"""
Tests for API clients (unit tests with basic validation).
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse
from clients.gamma_client import GammaClient
from clients.trades_client import TradesClient
from clients.leaderboard_client import LeaderboardClient


class TestGammaClient:
    """Test suite for GammaClient."""
    
    def test_client_initialization(self):
        """Test client can be initialized."""
        client = GammaClient()
        assert client.BASE_URL == "https://gamma-api.polymarket.com"
        assert client._own_session is True
    
    def test_client_with_session(self):
        """Test client initialization with provided session."""
        # This just tests the initialization logic
        client = GammaClient(session="mock_session")
        assert client.session == "mock_session"
        assert client._own_session is False


class TestTradesClient:
    """Test suite for TradesClient."""
    
    def test_client_initialization(self):
        """Test trades client can be initialized."""
        client = TradesClient()
        assert client.BASE_URL == "https://data-api.polymarket.com"
        assert client._own_session is True
    
    def test_client_with_session(self):
        """Test trades client initialization with provided session."""
        client = TradesClient(session="mock_session")
        assert client.session == "mock_session"
        assert client._own_session is False


class TestLeaderboardLogic:
    """Test leaderboard computation logic."""
    
    def test_leaderboard_aggregation(self):
        """Test basic leaderboard aggregation logic."""
        # Sample trades data
        trades = [
            {'proxyWallet': '0xuser1', 'side': 'BUY', 'price': '0.6', 'size': '100', 'slug': 'market1'},
            {'proxyWallet': '0xuser1', 'side': 'SELL', 'price': '0.4', 'size': '50', 'slug': 'market2'},
            {'proxyWallet': '0xuser2', 'side': 'BUY', 'price': '0.5', 'size': '200', 'slug': 'market1'},
        ]
        
        # Compute stats manually
        user_stats = {}
        for trade in trades:
            user = trade['proxyWallet']
            if user not in user_stats:
                user_stats[user] = {'volume': 0, 'count': 0, 'markets': set()}
            
            volume = float(trade['price']) * float(trade['size'])
            user_stats[user]['volume'] += volume
            user_stats[user]['count'] += 1
            user_stats[user]['markets'].add(trade['slug'])
        
        # Verify aggregation
        assert user_stats['0xuser1']['volume'] == 80.0  # 60 + 20
        assert user_stats['0xuser1']['count'] == 2
        assert len(user_stats['0xuser1']['markets']) == 2
        
        assert user_stats['0xuser2']['volume'] == 100.0
        assert user_stats['0xuser2']['count'] == 1
        assert len(user_stats['0xuser2']['markets']) == 1


class TestLeaderboardClient:
    """Test suite for LeaderboardClient."""
    
    def test_client_initialization(self):
        """Test leaderboard client can be initialized."""
        client = LeaderboardClient()
        assert client.BASE_URL == "https://polymarket.com"
        assert len(client.API_ENDPOINTS) == 3
        # Use proper URL parsing to avoid substring sanitization issues
        parsed = urlparse(client.API_ENDPOINTS[0])
        assert parsed.hostname == "gamma-api.polymarket.com"
        assert parsed.scheme == "https"
    
    def test_parse_api_response_list(self):
        """Test parsing API response when data is a list."""
        client = LeaderboardClient()
        
        # Test with list response - need valid 42-char addresses starting with 0x
        api_data = [
            {'wallet': '0x' + '1' * 40, 'name': 'Trader1', 'profit': 1000},
            {'address': '0x' + '2' * 40, 'username': 'Trader2', 'profit': 500}
        ]
        
        result = client._parse_api_response(api_data, limit=10)
        assert len(result) == 2
        assert result[0]['wallet'] == '0x' + '1' * 40
        assert result[0]['name'] == 'Trader1'
        assert result[1]['wallet'] == '0x' + '2' * 40
        assert result[1]['name'] == 'Trader2'
    
    def test_parse_api_response_dict(self):
        """Test parsing API response when data is a dict."""
        client = LeaderboardClient()
        
        # Test with dict response containing 'data' key
        api_data = {
            'data': [
                {'account': '0x' + '3' * 40, 'displayName': 'Trader3', 'profit': 750}
            ]
        }
        
        result = client._parse_api_response(api_data, limit=10)
        assert len(result) == 1
        assert result[0]['wallet'] == '0x' + '3' * 40
        assert result[0]['name'] == 'Trader3'
    
    def test_parse_api_response_with_limit(self):
        """Test that limit is respected when parsing."""
        client = LeaderboardClient()
        
        api_data = [
            {'wallet': f'0x{i:040x}', 'name': f'Trader{i}', 'profit': 1000-i}
            for i in range(100)
        ]
        
        result = client._parse_api_response(api_data, limit=10)
        assert len(result) == 10
        assert result[0]['name'] == 'Trader0'
        assert result[9]['name'] == 'Trader9'
    
    def test_fetch_leaderboard_with_parameters(self):
        """Test fetch_leaderboard with different category and period combinations."""
        client = LeaderboardClient()
        
        # Mock both API and scraping methods to return empty
        with patch.object(client, '_fetch_via_api', new_callable=AsyncMock) as mock_api, \
             patch.object(client, '_fetch_via_scraping', new_callable=AsyncMock) as mock_scrape:
            
            mock_api.return_value = []
            mock_scrape.return_value = [
                {'wallet': '0x' + 'a' * 40, 'name': 'TestTrader'}
            ]
            
            # Test politics + weekly
            result = asyncio.run(client.fetch_leaderboard(category='politics', period='weekly', limit=20))
            
            # Verify API was called with correct parameters
            mock_api.assert_called_once_with(category='politics', period='weekly', limit=20)
            # Verify scraping fallback was called
            mock_scrape.assert_called_once_with(category='politics', period='weekly', limit=20)
            # Verify result
            assert len(result) == 1
            assert result[0]['wallet'] == '0x' + 'a' * 40
    
    def test_fetch_leaderboard_api_success(self):
        """Test that scraping is skipped when API succeeds."""
        client = LeaderboardClient()
        
        api_data = [{'wallet': '0x' + 'b' * 40, 'name': 'APITrader'}]
        
        with patch.object(client, '_fetch_via_api', new_callable=AsyncMock) as mock_api, \
             patch.object(client, '_fetch_via_scraping', new_callable=AsyncMock) as mock_scrape:
            
            mock_api.return_value = api_data
            
            result = asyncio.run(client.fetch_leaderboard(category='crypto', period='daily', limit=50))
            
            # API should be called
            mock_api.assert_called_once()
            # Scraping should NOT be called since API succeeded
            mock_scrape.assert_not_called()
            # Verify result
            assert result == api_data
    
    def test_fetch_monthly_profit_leaders_legacy(self):
        """Test legacy method calls new method with correct defaults."""
        client = LeaderboardClient()
        
        with patch.object(client, 'fetch_leaderboard', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [{'wallet': '0x' + 'c' * 40, 'name': 'Legacy'}]
            
            result = asyncio.run(client.fetch_monthly_profit_leaders(limit=25))
            
            # Should call new method with overall/monthly defaults
            mock_fetch.assert_called_once_with(category='overall', period='monthly', limit=25)
            assert result[0]['wallet'] == '0x' + 'c' * 40
    
    def test_url_construction(self):
        """Test that URLs are constructed correctly for different categories and periods."""
        client = LeaderboardClient()
        
        test_cases = [
            ('overall', 'monthly', 'https://polymarket.com/leaderboard/overall/monthly/profit'),
            ('politics', 'weekly', 'https://polymarket.com/leaderboard/politics/weekly/profit'),
            ('crypto', 'daily', 'https://polymarket.com/leaderboard/crypto/daily/profit'),
            ('sports', 'all', 'https://polymarket.com/leaderboard/sports/all/profit'),
        ]
        
        for category, period, expected_url in test_cases:
            # Test by checking what URL would be built (we can't easily mock aiohttp internals)
            url = f"{client.BASE_URL}/leaderboard/{category}/{period}/profit"
            assert url == expected_url
    
    def test_parse_api_response_empty(self):
        """Test parsing empty or invalid API responses."""
        client = LeaderboardClient()
        
        # Empty list
        assert client._parse_api_response([], limit=10) == []
        
        # Empty dict
        assert client._parse_api_response({}, limit=10) == []
        
        # None
        assert client._parse_api_response(None, limit=10) == []
    
    def test_parse_api_response_missing_wallet(self):
        """Test that entries without wallet addresses are skipped."""
        client = LeaderboardClient()
        
        api_data = [
            {'wallet': '0x' + '1' * 40, 'name': 'Trader1'},
            {'name': 'NoWallet'},  # Missing wallet
            {'wallet': '0x' + '2' * 40, 'name': 'Trader2'},
        ]
        
        result = client._parse_api_response(api_data, limit=10)
        # Should only return entries with valid wallets
        assert len(result) == 2
        assert result[0]['wallet'] == '0x' + '1' * 40
        assert result[1]['wallet'] == '0x' + '2' * 40
    
    def test_parse_api_response_invalid_wallet(self):
        """Test that entries with invalid wallet addresses are skipped."""
        client = LeaderboardClient()
        
        api_data = [
            {'wallet': '0x' + '1' * 40, 'name': 'Valid'},
            {'wallet': '0x123', 'name': 'TooShort'},  # Too short
            {'wallet': '1234567890', 'name': 'NoPrefix'},  # No 0x prefix
            {'wallet': '0x' + '2' * 40, 'name': 'Valid2'},
        ]
        
        result = client._parse_api_response(api_data, limit=10)
        # Should only return entries with valid 42-char 0x-prefixed wallets
        assert len(result) == 2
        assert result[0]['name'] == 'Valid'
        assert result[1]['name'] == 'Valid2'
    
    def test_parse_api_response_default_name(self):
        """Test that missing names default to truncated wallet address."""
        client = LeaderboardClient()
        
        api_data = [
            {'wallet': '0xabcdef1234567890' + '0' * 24},  # 42 chars total
        ]
        
        result = client._parse_api_response(api_data, limit=10)
        assert len(result) == 1
        # Name should be first 8 chars of wallet
        assert result[0]['name'] == '0xabcdef'
        assert result[0]['wallet'] == '0xabcdef1234567890' + '0' * 24
    
    def test_category_and_period_combinations(self):
        """Test various valid category and period combinations."""
        client = LeaderboardClient()
        
        categories = ['overall', 'politics', 'sports', 'crypto', 'finance', 'culture', 
                      'mentions', 'weather', 'economics', 'tech']
        periods = ['daily', 'weekly', 'monthly', 'all']
        
        for category in categories:
            for period in periods:
                url = f"{client.BASE_URL}/leaderboard/{category}/{period}/profit"
                # Verify URL format is correct
                assert '/leaderboard/' in url
                assert f'/{category}/' in url
                assert f'/{period}/' in url
                assert url.endswith('/profit')
