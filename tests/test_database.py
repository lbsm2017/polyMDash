"""
Tests for database functionality.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from data.database import Database


class TestDatabase:
    """Test suite for Database class."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        # Create a unique temporary file path for each test
        import uuid
        temp_path = tempfile.gettempdir() + f'/test_db_{uuid.uuid4().hex}.db'
        
        # Ensure file doesn't exist
        Path(temp_path).unlink(missing_ok=True)
        
        # Create fresh database
        db = Database(temp_path)
        
        yield db
        
        # Cleanup
        db.disconnect()
        Path(temp_path).unlink(missing_ok=True)
    
    def test_database_initialization(self, temp_db):
        """Test database schema initialization."""
        # Check that tables exist by trying to query them
        cursor = temp_db.conn.cursor()
        
        # Markets table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='markets'")
        assert cursor.fetchone() is not None
        
        # Trades table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        assert cursor.fetchone() is not None
        
        # Users table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None
        
        # Watchlist table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'")
        assert cursor.fetchone() is not None
    
    def test_upsert_market(self, temp_db):
        """Test inserting and updating markets."""
        market_data = {
            'id': 'test-market-1',
            'question': 'Will this test pass?',
            'slug': 'test-market-slug',
            'category': 'Testing',
            'active': True,
            'closed': False,
            'endDate': '2025-12-31',
            'outcomes': ['Yes', 'No'],
            'outcomePrices': {'Yes': 0.6, 'No': 0.4},
            'liquidity': 10000,
            'volume': 50000,
            'volume24hr': 5000
        }
        
        # Insert
        temp_db.upsert_market(market_data)
        
        # Retrieve
        market = temp_db.get_market('test-market-1')
        assert market is not None
        assert market['question'] == 'Will this test pass?'
        assert market['liquidity'] == 10000
        
        # Update
        market_data['liquidity'] = 20000
        temp_db.upsert_market(market_data)
        
        market = temp_db.get_market('test-market-1')
        assert market['liquidity'] == 20000
    
    def test_get_active_markets(self, temp_db):
        """Test retrieving active markets."""
        # Insert active market
        market1 = {
            'id': 'active-1',
            'question': 'Active market?',
            'slug': 'active-market',
            'active': True,
            'closed': False,
            'outcomes': ['Yes', 'No'],
            'outcomePrices': {},
            'volume24hr': 1000
        }
        temp_db.upsert_market(market1)
        
        # Insert inactive market
        market2 = {
            'id': 'inactive-1',
            'question': 'Inactive market?',
            'slug': 'inactive-market',
            'active': False,
            'closed': True,
            'outcomes': ['Yes', 'No'],
            'outcomePrices': {},
            'volume24hr': 500
        }
        temp_db.upsert_market(market2)
        
        active_markets = temp_db.get_active_markets(limit=10)
        assert len(active_markets) == 1
        assert active_markets[0]['id'] == 'active-1'
    
    def test_insert_trade(self, temp_db):
        """Test inserting trades."""
        trade_data = {
            'market': 'test-market-1',
            'proxyWallet': '0x1234567890abcdef',
            'side': 'BUY',
            'outcome': 'YES',
            'price': 0.6,
            'size': 100,
            'timestamp': datetime.now().isoformat(),
            'eventSlug': 'test-event'
        }
        
        temp_db.insert_trade(trade_data)
        
        trades = temp_db.get_recent_trades(limit=10)
        assert len(trades) == 1
        assert trades[0]['side'] == 'BUY'
        assert trades[0]['user_address'] == '0x1234567890abcdef'
    
    def test_get_user_trades(self, temp_db):
        """Test retrieving trades for specific user."""
        # Insert trades for different users
        trade1 = {
            'market': 'market-1',
            'proxyWallet': '0xuser1',
            'side': 'BUY',
            'outcome': 'YES',
            'price': 0.6,
            'size': 100,
            'timestamp': datetime.now().isoformat()
        }
        temp_db.insert_trade(trade1)
        
        trade2 = {
            'market': 'market-2',
            'proxyWallet': '0xuser2',
            'side': 'SELL',
            'outcome': 'NO',
            'price': 0.4,
            'size': 50,
            'timestamp': datetime.now().isoformat()
        }
        temp_db.insert_trade(trade2)
        
        user1_trades = temp_db.get_user_trades('0xuser1', limit=10)
        assert len(user1_trades) == 1
        assert user1_trades[0]['user_address'] == '0xuser1'
    
    def test_update_user_stats(self, temp_db):
        """Test updating user statistics."""
        stats = {
            'total_volume': 10000,
            'trade_count': 50,
            'markets_traded': 5,
            'last_trade_time': datetime.now().isoformat()
        }
        
        temp_db.update_user_stats('0xuser1', stats)
        
        leaderboard = temp_db.get_leaderboard(limit=10)
        assert len(leaderboard) == 1
        assert leaderboard[0]['address'] == '0xuser1'
        assert leaderboard[0]['total_volume'] == 10000
    
    def test_watchlist_operations(self, temp_db):
        """Test watchlist add/remove/get operations."""
        # Insert two test markets
        market1 = {
            'id': 'watch-market-1',
            'question': 'Watch this?',
            'slug': 'watch-market-1',
            'active': True,
            'closed': False,
            'outcomes': [],
            'outcomePrices': {},
            'liquidity': 1000,
            'volume': 5000,
            'volume24hr': 500
        }
        temp_db.upsert_market(market1)
        
        market2 = {
            'id': 'watch-market-2',
            'question': 'Watch this too?',
            'slug': 'watch-market-2',
            'active': True,
            'closed': False,
            'outcomes': [],
            'outcomePrices': {},
            'liquidity': 2000,
            'volume': 6000,
            'volume24hr': 600
        }
        temp_db.upsert_market(market2)
        
        # Initially watchlist should be empty
        watchlist = temp_db.get_watchlist()
        assert len(watchlist) == 0
        
        # Add first market to watchlist
        temp_db.add_to_watchlist('watch-market-1')
        watchlist = temp_db.get_watchlist()
        assert len(watchlist) == 1
        assert watchlist[0]['id'] == 'watch-market-1'
        
        # Add second market to watchlist
        temp_db.add_to_watchlist('watch-market-2')
        watchlist = temp_db.get_watchlist()
        assert len(watchlist) == 2
        
        # Add duplicate (should not create duplicate)
        temp_db.add_to_watchlist('watch-market-1')
        watchlist = temp_db.get_watchlist()
        assert len(watchlist) == 2
        
        # Remove first market from watchlist
        temp_db.remove_from_watchlist('watch-market-1')
        watchlist = temp_db.get_watchlist()
        assert len(watchlist) == 1
        assert watchlist[0]['id'] == 'watch-market-2'
        
        # Remove second market
        temp_db.remove_from_watchlist('watch-market-2')
        watchlist = temp_db.get_watchlist()
        assert len(watchlist) == 0
    
    def test_price_history(self, temp_db):
        """Test price history operations."""
        price_data = {
            'market_id': 'market-1',
            'outcome': 'YES',
            'price': 0.6,
            'volume': 1000,
            'liquidity': 5000,
            'timestamp': datetime.now()
        }
        
        temp_db.add_price_update(price_data)
        
        history = temp_db.get_price_history('market-1', hours=24)
        assert len(history) == 1
        assert history[0]['price'] == 0.6
    
    def test_cleanup_old_data(self, temp_db):
        """Test cleanup of old data."""
        from datetime import timedelta
        
        # Insert old trade
        old_trade = {
            'market': 'market-1',
            'proxyWallet': '0xuser1',
            'side': 'BUY',
            'outcome': 'YES',
            'price': 0.6,
            'size': 100,
            'timestamp': (datetime.now() - timedelta(days=60)).isoformat()
        }
        temp_db.insert_trade(old_trade)
        
        # Insert recent trade
        recent_trade = {
            'market': 'market-2',
            'proxyWallet': '0xuser2',
            'side': 'SELL',
            'outcome': 'NO',
            'price': 0.4,
            'size': 50,
            'timestamp': datetime.now().isoformat()
        }
        temp_db.insert_trade(recent_trade)
        
        # Cleanup data older than 30 days
        temp_db.cleanup_old_data(days=30)
        
        trades = temp_db.get_recent_trades(limit=100)
        assert len(trades) == 1
        assert trades[0]['user_address'] == '0xuser2'
