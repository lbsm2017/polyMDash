"""
Tests for API clients (unit tests with basic validation).
"""

import pytest
from clients.gamma_client import GammaClient
from clients.trades_client import TradesClient


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
