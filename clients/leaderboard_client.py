"""
Client for fetching Polymarket leaderboard data.
"""

import logging
import aiohttp
import json
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LeaderboardClient:
    """Client for fetching Polymarket leaderboard via API or scraping."""
    
    BASE_URL = "https://polymarket.com"
    # Common API endpoint patterns
    API_ENDPOINTS = [
        "https://gamma-api.polymarket.com/leaderboard",
        "https://strapi-matic.poly.market/leaderboards",
        "https://data-api.polymarket.com/leaderboard",
    ]
    
    async def _fetch_via_api(self, category: str = "overall", period: str = "monthly", limit: int = 50) -> List[Dict[str, str]]:
        """
        Try to fetch leaderboard data via API endpoints.
        
        Args:
            category: Category filter (overall, politics, sports, etc.)
            period: Time period (daily, weekly, monthly, all)
            limit: Maximum number of traders to return
            
        Returns:
            List of dicts with 'name' and 'wallet' keys, or empty list if all APIs fail
        """
        async with aiohttp.ClientSession() as session:
            for api_url in self.API_ENDPOINTS:
                try:
                    # Try dynamic endpoint with category and period
                    url = f"{api_url}/{category}/{period}/profit"
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/json'
                    }
                    
                    async with session.get(url, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                traders = self._parse_api_response(data, limit)
                                if traders:
                                    logger.info(f"✓ Fetched {len(traders)} traders from API: {api_url}")
                                    return traders
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.debug(f"Failed to parse response from {api_url}: {e}")
                                continue
                        else:
                            logger.debug(f"API {api_url} returned status {response.status}")
                            
                except Exception as e:
                    logger.debug(f"API endpoint {api_url} failed: {e}")
                    continue
        
        return []
    
    def _parse_api_response(self, data: any, limit: int) -> List[Dict[str, str]]:
        """
        Parse API response into standardized trader format.
        
        Handles various possible API response structures.
        """
        traders = []
        
        # Try different possible response structures
        items = None
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common keys: data, results, leaderboard, users, traders
            for key in ['data', 'results', 'leaderboard', 'users', 'traders', 'items']:
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    break
        
        if not items:
            return []
        
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            
            # Extract wallet address (try various field names)
            wallet = None
            for wallet_key in ['wallet', 'address', 'account', 'user', 'userId', 'walletAddress']:
                if wallet_key in item:
                    wallet = item[wallet_key]
                    if isinstance(wallet, str) and len(wallet) == 42 and wallet.startswith('0x'):
                        break
            
            # Extract name (try various field names)
            name = None
            for name_key in ['name', 'username', 'displayName', 'nickname', 'handle']:
                if name_key in item:
                    name = item[name_key]
                    if isinstance(name, str) and name:
                        break
            
            if wallet and len(wallet) == 42 and wallet.startswith('0x'):
                traders.append({
                    'name': name if name else wallet[:8],
                    'wallet': wallet
                })
        
        return traders
    
    async def _fetch_via_scraping(self, category: str = "overall", period: str = "monthly", limit: int = 50) -> List[Dict[str, str]]:
        """
        Fallback method: scrape leaderboard HTML.
        
        Args:
            category: Category filter (overall, politics, sports, etc.)
            period: Time period (daily, weekly, monthly, all)
            limit: Maximum number of traders to return
            
        Returns:
            List of dicts with 'name' and 'wallet' keys
        """
        url = f"{self.BASE_URL}/leaderboard/{category}/{period}/profit"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=15) as response:
                    if response.status != 200:
                        logger.error(f"Leaderboard page fetch failed with status {response.status}")
                        return []
                    
                    html = await response.text()
                    
            # Parse HTML to extract trader data
            soup = BeautifulSoup(html, 'html.parser')
            traders = []
            
            # Try to find links to user profiles which contain wallet addresses
            user_links = soup.find_all('a', href=lambda x: x and '/profile/' in x)
            
            for link in user_links[:limit]:
                href = link.get('href', '')
                # Extract wallet from URL like /profile/0x123...
                if '/profile/' in href:
                    wallet = href.split('/profile/')[-1].split('?')[0]
                    
                    # Try to find username
                    name = link.get_text(strip=True) or wallet[:8]
                    
                    if wallet and len(wallet) == 42 and wallet.startswith('0x'):
                        traders.append({
                            'name': name,
                            'wallet': wallet
                        })
                        
                        if len(traders) >= limit:
                            break
            
            if not traders:
                logger.warning("No traders found via profile links, trying regex extraction")
                # Alternative: look for any 0x addresses in the page
                import re
                addresses = re.findall(r'0x[a-fA-F0-9]{40}', html)
                seen = set()
                for addr in addresses:
                    if addr not in seen and len(traders) < limit:
                        traders.append({
                            'name': addr[:8],
                            'wallet': addr
                        })
                        seen.add(addr)
            
            logger.info(f"✓ Scraped {len(traders)} traders from HTML")
            return traders
            
        except Exception as e:
            logger.error(f"Error scraping leaderboard: {e}")
            return []
    
    async def fetch_leaderboard(self, category: str = "overall", period: str = "monthly", limit: int = 50) -> List[Dict[str, str]]:
        """
        Fetch top traders from leaderboard with custom filters.
        
        Tries API first, falls back to HTML scraping if API fails.
        
        Args:
            category: Category filter (overall, politics, sports, crypto, etc.)
            period: Time period (daily, weekly, monthly, all)
            limit: Maximum number of traders to return
            
        Returns:
            List of dicts with 'name' and 'wallet' keys
        """
        # Try API first (faster and more reliable)
        traders = await self._fetch_via_api(category=category, period=period, limit=limit)
        
        if traders:
            return traders
        
        # Fallback to HTML scraping
        logger.info(f"API fetch failed, falling back to HTML scraping for {category}/{period}")
        traders = await self._fetch_via_scraping(category=category, period=period, limit=limit)
        
        if not traders:
            logger.error(f"Both API and scraping methods failed to fetch leaderboard for {category}/{period}")
        
        return traders
    
    async def fetch_monthly_profit_leaders(self, limit: int = 50) -> List[Dict[str, str]]:
        """
        Fetch top traders from monthly profit leaderboard (legacy method).
        
        Args:
            limit: Maximum number of traders to return
            
        Returns:
            List of dicts with 'name' and 'wallet' keys
        """
        return await self.fetch_leaderboard(category="overall", period="monthly", limit=limit)
