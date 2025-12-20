"""
Data API Client for Polymarket trade history and user activity.
Handles trade data retrieval for leaderboards and activity tracking.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradesClient:
    """Client for Polymarket Data API - Trade History and User Activity."""
    
    BASE_URL = "https://data-api.polymarket.com"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the Trades API client.
        
        Args:
            session: Optional aiohttp session for connection pooling
        """
        self.session = session
        self._own_session = session is None
        
    async def __aenter__(self):
        """Async context manager entry."""
        if self._own_session:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._own_session and self.session:
            await self.session.close()
            
    async def _request(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """
        Make an async GET request to the Data API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response data or None on error
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in API request: {e}")
            return None
            
    async def get_trades(
        self,
        limit: int = 100,
        offset: int = 0,
        user: Optional[str] = None,
        market: Optional[str] = None,
        event_id: Optional[str] = None,
        taker_only: Optional[bool] = None
    ) -> List[Dict]:
        """
        Fetch recent trades with optional filters.
        
        Args:
            limit: Number of trades to return (default 100)
            offset: Pagination offset
            user: Filter by user address
            market: Filter by market ID
            event_id: Filter by event ID
            taker_only: Filter by taker side only
            
        Returns:
            List of trade dictionaries or empty list on error
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if user:
            params["user"] = user
        if market:
            params["market"] = market
        if event_id:
            params["eventId"] = event_id
        if taker_only is not None:
            params["takerOnly"] = str(taker_only).lower()
            
        logger.info(f"Fetching trades with params: {params}")
        result = await self._request("/trades", params)
        
        # Ensure we always return a list
        if result is None:
            return []
        if not isinstance(result, list):
            logger.warning(f"Expected list from API but got {type(result)}")
            return []
        
        return result
        
    async def get_user_trades(
        self,
        user_address: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get all trades for a specific user.
        
        Args:
            user_address: User's proxy wallet address
            limit: Maximum number of trades to return
            
        Returns:
            List of user's trade dictionaries
        """
        logger.info(f"Fetching trades for user: {user_address}")
        return await self.get_trades(user=user_address, limit=limit)
        
    async def get_market_trades(
        self,
        market_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get all trades for a specific market.
        
        Args:
            market_id: Market identifier
            limit: Maximum number of trades to return
            
        Returns:
            List of market's trade dictionaries
        """
        logger.info(f"Fetching trades for market: {market_id}")
        return await self.get_trades(market=market_id, limit=limit)
        
    async def get_recent_activity(
        self,
        minutes: int = 15,
        limit: int = 500
    ) -> List[Dict]:
        """
        Get recent trading activity within a time window.
        
        Args:
            minutes: Time window in minutes (default 15)
            limit: Maximum number of trades to fetch
            
        Returns:
            List of recent trade dictionaries
        """
        logger.info(f"Fetching activity from last {minutes} minutes")
        trades = await self.get_trades(limit=limit)
        
        # Filter by timestamp
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_trades = []
        
        for trade in trades:
            # Parse timestamp (adjust format based on actual API response)
            trade_time = datetime.fromisoformat(
                trade.get('timestamp', '').replace('Z', '+00:00')
            )
            if trade_time >= cutoff_time:
                recent_trades.append(trade)
            else:
                break  # Trades are ordered by timestamp desc
                
        return recent_trades
        
    async def compute_leaderboard(
        self,
        time_window_minutes: int = 1440,  # 24 hours
        min_trades: int = 5,
        limit: int = 100
    ) -> List[Dict]:
        """
        Compute trader leaderboard based on volume and activity.
        
        Args:
            time_window_minutes: Time window for leaderboard (default 24h)
            min_trades: Minimum trades required to qualify
            limit: Number of top traders to return
            
        Returns:
            List of trader statistics sorted by volume
        """
        logger.info(f"Computing leaderboard for {time_window_minutes} minute window")
        
        # Fetch recent trades
        trades = await self.get_recent_activity(
            minutes=time_window_minutes,
            limit=2000
        )
        
        # Aggregate by user
        user_stats = defaultdict(lambda: {
            'total_volume': 0,
            'trade_count': 0,
            'buy_count': 0,
            'sell_count': 0,
            'markets_traded': set(),
            'avg_trade_size': 0,
            'last_trade_time': None
        })
        
        for trade in trades:
            user = trade.get('proxyWallet', 'unknown')
            side = trade.get('side', 'UNKNOWN')
            price = float(trade.get('price', 0))
            size = float(trade.get('size', 0))
            volume = price * size
            
            stats = user_stats[user]
            stats['total_volume'] += volume
            stats['trade_count'] += 1
            
            if side == 'BUY':
                stats['buy_count'] += 1
            elif side == 'SELL':
                stats['sell_count'] += 1
                
            stats['markets_traded'].add(trade.get('slug', ''))
            
            # Track most recent trade
            trade_time = trade.get('timestamp')
            if not stats['last_trade_time'] or trade_time > stats['last_trade_time']:
                stats['last_trade_time'] = trade_time
                
        # Convert to list and calculate averages
        leaderboard = []
        for user, stats in user_stats.items():
            if stats['trade_count'] < min_trades:
                continue
                
            stats['avg_trade_size'] = (
                stats['total_volume'] / stats['trade_count']
                if stats['trade_count'] > 0 else 0
            )
            stats['markets_traded'] = len(stats['markets_traded'])
            stats['user_address'] = user
            
            leaderboard.append(stats)
            
        # Sort by total volume descending
        leaderboard.sort(key=lambda x: x['total_volume'], reverse=True)
        
        return leaderboard[:limit]
        
    async def get_user_stats(self, user_address: str) -> Dict:
        """
        Get comprehensive statistics for a specific user.
        
        Args:
            user_address: User's proxy wallet address
            
        Returns:
            Dictionary of user statistics
        """
        logger.info(f"Computing stats for user: {user_address}")
        
        trades = await self.get_user_trades(user_address, limit=500)
        
        if not trades:
            return {
                'user_address': user_address,
                'total_volume': 0,
                'trade_count': 0,
                'markets_traded': 0,
                'recent_activity': []
            }
            
        total_volume = sum(
            float(t.get('price', 0)) * float(t.get('size', 0))
            for t in trades
        )
        
        markets = set(t.get('slug') for t in trades)
        
        return {
            'user_address': user_address,
            'total_volume': total_volume,
            'trade_count': len(trades),
            'markets_traded': len(markets),
            'recent_activity': trades[:10]  # Last 10 trades
        }


# Synchronous wrapper
class TradesClientSync:
    """Synchronous wrapper for TradesClient."""
    
    def __init__(self):
        self.client = TradesClient()
        
    def get_trades(self, **kwargs) -> List[Dict]:
        """Sync wrapper for get_trades."""
        return asyncio.run(self._async_get_trades(**kwargs))
        
    async def _async_get_trades(self, **kwargs) -> List[Dict]:
        async with self.client as client:
            return await client.get_trades(**kwargs)
            
    def compute_leaderboard(self, **kwargs) -> List[Dict]:
        """Sync wrapper for compute_leaderboard."""
        return asyncio.run(self._async_compute_leaderboard(**kwargs))
        
    async def _async_compute_leaderboard(self, **kwargs) -> List[Dict]:
        async with self.client as client:
            return await client.compute_leaderboard(**kwargs)


if __name__ == "__main__":
    # Test the client
    async def test():
        async with TradesClient() as client:
            # Fetch recent trades
            trades = await client.get_trades(limit=10)
            print(f"\nFetched {len(trades)} recent trades:")
            for i, trade in enumerate(trades, 1):
                print(f"{i}. {trade.get('side')} - "
                      f"Market: {trade.get('slug', 'N/A')[:40]}")
                      
            # Compute leaderboard
            print("\nComputing 24h leaderboard...")
            leaderboard = await client.compute_leaderboard(limit=10)
            print(f"\nTop {len(leaderboard)} traders:")
            for i, trader in enumerate(leaderboard, 1):
                print(f"{i}. Volume: ${trader['total_volume']:,.2f} | "
                      f"Trades: {trader['trade_count']} | "
                      f"Markets: {trader['markets_traded']}")
                
    asyncio.run(test())
