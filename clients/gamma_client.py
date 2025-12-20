"""
Gamma API Client for Polymarket market data.
Handles market discovery, filtering, and metadata retrieval.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GammaClient:
    """Client for Polymarket Gamma API - Core Market Data."""
    
    BASE_URL = "https://gamma-api.polymarket.com"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the Gamma API client.
        
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
        Make an async GET request to the Gamma API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response data
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise
            
    async def get_markets(
        self,
        limit: int = 50,
        offset: int = 0,
        active: Optional[bool] = None,
        closed: Optional[bool] = None,
        category: Optional[str] = None,
        order_by: str = "volume24hr"
    ) -> List[Dict]:
        """
        Fetch markets with optional filters.
        
        Args:
            limit: Number of markets to return (default 50)
            offset: Pagination offset (default 0)
            active: Filter by active status
            closed: Filter by closed status
            category: Filter by category/tag
            order_by: Sort field (volume24hr, liquidity, etc.)
            
        Returns:
            List of market dictionaries
        """
        params = {
            "limit": limit,
            "offset": offset,
            "order": order_by
        }
        
        if active is not None:
            params["active"] = str(active).lower()
        if closed is not None:
            params["closed"] = str(closed).lower()
        if category:
            params["tag"] = category
            
        logger.info(f"Fetching markets with params: {params}")
        return await self._request("/markets", params)
        
    async def get_market_by_id(self, market_id: str) -> Dict:
        """
        Get a single market by its ID.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Market data dictionary
        """
        logger.info(f"Fetching market ID: {market_id}")
        return await self._request(f"/markets/{market_id}")
        
    async def get_market_by_slug(self, slug: str) -> Dict:
        """
        Get a single market by its slug.
        
        Args:
            slug: Market slug identifier
            
        Returns:
            Market data dictionary
        """
        logger.info(f"Fetching market slug: {slug}")
        return await self._request(f"/markets/slug/{slug}")
        
    async def get_events(
        self,
        limit: int = 50,
        offset: int = 0,
        archived: Optional[bool] = None
    ) -> List[Dict]:
        """
        Fetch events (collections of related markets).
        
        Args:
            limit: Number of events to return
            offset: Pagination offset
            archived: Filter by archived status
            
        Returns:
            List of event dictionaries
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if archived is not None:
            params["archived"] = str(archived).lower()
            
        logger.info(f"Fetching events with params: {params}")
        return await self._request("/events", params)
        
    async def get_tags(self) -> List[Dict]:
        """
        Get all available market tags/categories.
        
        Returns:
            List of tag dictionaries
        """
        logger.info("Fetching all tags")
        return await self._request("/tags")
        
    async def get_hot_markets(self, limit: int = 20) -> List[Dict]:
        """
        Get currently hot/trending markets by volume.
        
        Args:
            limit: Number of markets to return
            
        Returns:
            List of market dictionaries sorted by 24h volume
        """
        return await self.get_markets(
            limit=limit,
            active=True,
            order_by="volume24hr"
        )
        
    async def search_markets(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search markets by question text.
        
        Args:
            query: Search query string
            limit: Maximum results to return
            
        Returns:
            List of matching market dictionaries
        """
        # Note: Adjust based on actual API search capabilities
        markets = await self.get_markets(limit=100, active=True)
        
        # Simple client-side filtering (improve with server-side search if available)
        query_lower = query.lower()
        filtered = [
            m for m in markets 
            if query_lower in m.get("question", "").lower()
        ]
        
        return filtered[:limit]


# Synchronous wrapper for ease of use
class GammaClientSync:
    """Synchronous wrapper for GammaClient."""
    
    def __init__(self):
        self.client = GammaClient()
        
    def get_markets(self, **kwargs) -> List[Dict]:
        """Sync wrapper for get_markets."""
        return asyncio.run(self._async_get_markets(**kwargs))
        
    async def _async_get_markets(self, **kwargs) -> List[Dict]:
        async with self.client as client:
            return await client.get_markets(**kwargs)
            
    def get_market_by_id(self, market_id: str) -> Dict:
        """Sync wrapper for get_market_by_id."""
        return asyncio.run(self._async_get_market_by_id(market_id))
        
    async def _async_get_market_by_id(self, market_id: str) -> Dict:
        async with self.client as client:
            return await client.get_market_by_id(market_id)
            
    def get_hot_markets(self, limit: int = 20) -> List[Dict]:
        """Sync wrapper for get_hot_markets."""
        return asyncio.run(self._async_get_hot_markets(limit))
        
    async def _async_get_hot_markets(self, limit: int) -> List[Dict]:
        async with self.client as client:
            return await client.get_hot_markets(limit)


if __name__ == "__main__":
    # Test the client
    async def test():
        async with GammaClient() as client:
            # Fetch hot markets
            markets = await client.get_hot_markets(limit=5)
            print(f"\nFetched {len(markets)} hot markets:")
            for i, market in enumerate(markets, 1):
                print(f"{i}. {market.get('question', 'N/A')}")
                print(f"   Volume 24h: ${market.get('volume24hr', 0):,.2f}")
                print(f"   Liquidity: ${market.get('liquidity', 0):,.2f}")
                
    asyncio.run(test())
