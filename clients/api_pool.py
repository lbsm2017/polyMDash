"""
High-performance API connection pool with persistent connections.
Provides best-in-class low latency for Polymarket API requests.
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


class APIPool:
    """
    Persistent connection pool with:
    - Shared TCP connections (keep-alive)
    - Semaphore-limited concurrency
    - Reusable event loop
    - Batch request optimization
    """
    
    # API endpoints
    GAMMA_API = "https://gamma-api.polymarket.com"
    DATA_API = "https://data-api.polymarket.com"
    
    # Connection pool settings
    MAX_CONNECTIONS = 100
    MAX_PER_HOST = 20
    KEEPALIVE_TIMEOUT = 30
    MAX_CONCURRENT_REQUESTS = 20
    REQUEST_TIMEOUT = 10
    
    _instance = None
    _session: Optional[aiohttp.ClientSession] = None
    _semaphore: Optional[asyncio.Semaphore] = None
    
    @classmethod
    def get_instance(cls) -> 'APIPool':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure the session exists and is valid."""
        # Check if event loop changed (happens with asyncio.run)
        try:
            current_loop = asyncio.get_running_loop()
            if self._session is not None and not self._session.closed:
                # Check if session's loop matches current loop
                if hasattr(self._session, '_loop') and self._session._loop != current_loop:
                    await self._session.close()
                    self._session = None
        except RuntimeError:
            pass
        
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.MAX_CONNECTIONS,
                limit_per_host=self.MAX_PER_HOST,
                keepalive_timeout=self.KEEPALIVE_TIMEOUT,
                enable_cleanup_closed=True,
            )
            timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        return self._session
    
    async def _fetch_with_semaphore(self, url: str) -> Optional[Dict]:
        """Fetch URL with semaphore limiting concurrency."""
        session = await self._ensure_session()
        async with self._semaphore:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Successfully fetched {url}: {len(data) if isinstance(data, list) else 'dict'}")
                        return data
                    else:
                        logger.warning(f"Request failed {url}: {response.status}")
                        return None
            except Exception as e:
                logger.warning(f"Request error {url}: {e}")
                return None
    
    async def fetch_user_trades(self, wallet: str, limit: int = 200) -> List[Dict]:
        """Fetch trades for a single user."""
        url = f"{self.DATA_API}/trades?user={wallet}&limit={limit}"
        result = await self._fetch_with_semaphore(url)
        if result and isinstance(result, list):
            return result
        return []
    
    async def fetch_market(self, slug: str) -> Optional[Dict]:
        """Fetch single market by slug."""
        url = f"{self.GAMMA_API}/markets/slug/{slug}"
        result = await self._fetch_with_semaphore(url)
        # This endpoint returns a single dict, not a list
        if result and isinstance(result, dict):
            logger.info(f"Market {slug}: closed={result.get('closed')}, active={result.get('active')}")
            return result
        else:
            logger.warning(f"Market {slug}: No data or wrong type: {type(result)}")
        return None
    
    async def fetch_all_parallel(
        self,
        wallets: List[str],
        market_slugs: List[str],
        cutoff_timestamp: int = 0
    ) -> Tuple[List[Dict], Dict[str, Optional[Dict]]]:
        """
        Fetch all user trades and market data in a single parallel batch.
        
        Returns:
            Tuple of (all_trades, market_data_dict)
        """
        await self._ensure_session()
        
        # Create all tasks
        trade_tasks = [self.fetch_user_trades(w) for w in wallets]
        market_tasks = [self.fetch_market(slug) for slug in market_slugs]
        
        # Run all in parallel
        all_results = await asyncio.gather(
            *trade_tasks, *market_tasks,
            return_exceptions=True
        )
        
        # Split results
        trade_results = all_results[:len(wallets)]
        market_results = all_results[len(wallets):]
        
        # Process trades
        all_trades = []
        for i, result in enumerate(trade_results):
            if isinstance(result, list):
                logger.info(f"Wallet {i+1}: Fetched {len(result)} trades")
                for trade in result:
                    if isinstance(trade, dict):
                        ts = trade.get('timestamp', 0)
                        if ts >= cutoff_timestamp:
                            all_trades.append(trade)
            elif isinstance(result, Exception):
                logger.warning(f"Trade fetch error for wallet {i+1}: {result}")
        
        logger.info(f"Total trades after filtering: {len(all_trades)}")
        
        # Process markets
        logger.info(f"Processing {len(market_slugs)} market slugs")
        market_data = {}
        for slug, result in zip(market_slugs, market_results):
            if isinstance(result, dict):
                is_closed = result.get('closed', False)
                is_active = result.get('active', True)
                
                if is_closed or not is_active:
                    logger.warning(f"Filtering out market {slug}: closed={is_closed}, active={is_active}")
                    market_data[slug] = None
                    continue
                
                prices = result.get('outcomePrices', [0.5, 0.5])
                if isinstance(prices, str):
                    prices = json.loads(prices)
                
                market_data[slug] = {
                    'yes_price': float(prices[0]) if prices else 0.5,
                    'no_price': float(prices[1]) if len(prices) > 1 else 0.5,
                    'volume': result.get('volume', 0),
                    'liquidity': result.get('liquidity', 0),
                    'active': is_active,
                    'closed': is_closed,
                }
                logger.info(f"Added market {slug} with prices YES={prices[0]}, NO={prices[1]}")
            else:
                logger.warning(f"Market {slug} returned non-dict: {type(result)}")
                market_data[slug] = None
        
        open_markets = [k for k, v in market_data.items() if v is not None]
        logger.info(f"Final market data: {len(open_markets)} open out of {len(market_data)} total")
        return all_trades, market_data
    
    async def close(self):
        """Close the session and cleanup."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        self._semaphore = None


def fetch_all_data(
    wallets: List[str],
    market_slugs: List[str],
    cutoff_minutes: int = 1440
) -> Tuple[List[Dict], Dict[str, Optional[Dict]]]:
    """
    Synchronous wrapper for parallel data fetching.
    Uses cached event loop for best performance.
    
    Args:
        wallets: List of wallet addresses
        market_slugs: List of market slugs to fetch
        cutoff_minutes: Only include trades newer than this
        
    Returns:
        Tuple of (trades_list, market_data_dict)
    """
    cutoff = int((datetime.now() - timedelta(minutes=cutoff_minutes)).timestamp())
    pool = APIPool.get_instance()
    
    async def _fetch_with_cleanup():
        try:
            return await pool.fetch_all_parallel(wallets, market_slugs, cutoff)
        finally:
            # Close session after each fetch to prevent event loop issues
            await pool.close()
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running (e.g., in Jupyter), create new one
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _fetch_with_cleanup())
                return future.result()
        else:
            return loop.run_until_complete(_fetch_with_cleanup())
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(_fetch_with_cleanup())
