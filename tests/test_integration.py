"""
Integration tests for the dashboard components.
"""

import pytest
from datetime import datetime, timedelta


class TestActivityFeed:
    """Test activity feed functionality."""
    
    def test_format_time_ago(self):
        """Test time ago formatting."""
        from app import format_time_ago
        
        now = int(datetime.now().timestamp())
        
        # Minutes ago
        ts = int((datetime.now() - timedelta(minutes=5)).timestamp())
        result = format_time_ago(ts)
        assert "5m ago" == result or "4m ago" == result  # Allow 1 minute tolerance
        
        # Hours ago
        ts = int((datetime.now() - timedelta(hours=2)).timestamp())
        result = format_time_ago(ts)
        assert "2h ago" == result or "1h ago" == result  # Allow tolerance
        
        # Days ago
        ts = int((datetime.now() - timedelta(days=3)).timestamp())
        result = format_time_ago(ts)
        assert "3d ago" == result
        
        # Just now
        result = format_time_ago(now)
        assert "just now" == result
    
    def test_parse_time_window(self):
        """Test time window parsing."""
        from app import parse_time_window
        
        assert parse_time_window("Last 1 hour") == 60
        assert parse_time_window("Last 6 hours") == 360
        assert parse_time_window("Last 24 hours") == 1440
        assert parse_time_window("Last 3 days") == 4320
        assert parse_time_window("Unknown") == 360  # Default


class TestPriceCalculations:
    """Test price calculation functions."""
    
    def test_calculate_entry_prices_bullish(self):
        """Test weighted average and last price calculation for bullish direction."""
        from app import calculate_entry_prices
        
        market = {
            'direction': 'BULLISH',
            'trades': [
                {'side': 'BUY', 'outcome': 'YES', 'price': 0.6, 'size': 100, 'timestamp': 1000},
                {'side': 'BUY', 'outcome': 'YES', 'price': 0.65, 'size': 200, 'timestamp': 2000},
                {'side': 'SELL', 'outcome': 'NO', 'price': 0.3, 'size': 50, 'timestamp': 3000},
            ]
        }
        
        avg_entry, last_price = calculate_entry_prices(market)
        
        # Weighted average: (0.6*60 + 0.65*130 + 0.3*15) / (60 + 130 + 15)
        expected_avg = (0.6 * 60 + 0.65 * 130 + 0.3 * 15) / (60 + 130 + 15)
        assert abs(avg_entry - expected_avg) < 0.001
        
        # Last price should be most recent (timestamp 3000)
        assert last_price == 0.3
    
    def test_calculate_entry_prices_bearish(self):
        """Test weighted average and last price calculation for bearish direction."""
        from app import calculate_entry_prices
        
        market = {
            'direction': 'BEARISH',
            'trades': [
                {'side': 'BUY', 'outcome': 'NO', 'price': 0.4, 'size': 100, 'timestamp': 1000},
                {'side': 'SELL', 'outcome': 'YES', 'price': 0.7, 'size': 50, 'timestamp': 2000},
            ]
        }
        
        avg_entry, last_price = calculate_entry_prices(market)
        
        # Weighted average: (0.4*40 + 0.7*35) / (40 + 35)
        expected_avg = (0.4 * 40 + 0.7 * 35) / (40 + 35)
        assert abs(avg_entry - expected_avg) < 0.001
        
        # Last price should be most recent (timestamp 2000)
        assert last_price == 0.7
    
    def test_calculate_entry_prices_no_trades(self):
        """Test price calculation with no trades."""
        from app import calculate_entry_prices
        
        market = {
            'direction': 'BULLISH',
            'trades': []
        }
        
        avg_entry, last_price = calculate_entry_prices(market)
        assert avg_entry == 0.0
        assert last_price == 0.0


class TestDataFiltering:
    """Test data filtering logic."""
    
    def test_activity_filtering(self):
        """Test filtering of activities by side and outcome."""
        # Sample activity data
        activities = [
            {"side": "BUY", "outcome": "YES", "price": 0.6, "size": 100},
            {"side": "SELL", "outcome": "NO", "price": 0.4, "size": 50},
            {"side": "BUY", "outcome": "NO", "price": 0.3, "size": 75},
            {"side": "SELL", "outcome": "YES", "price": 0.7, "size": 25},
        ]
        
        # Filter BUYs only
        buys = [a for a in activities if a["side"] == "BUY"]
        assert len(buys) == 2
        
        # Filter SELLs only
        sells = [a for a in activities if a["side"] == "SELL"]
        assert len(sells) == 2
        
        # Filter YES outcomes
        yes_trades = [a for a in activities if a["outcome"] == "YES"]
        assert len(yes_trades) == 2
        
        # Filter NO outcomes
        no_trades = [a for a in activities if a["outcome"] == "NO"]
        assert len(no_trades) == 2


class TestMetricsCalculation:
    """Test metrics calculation."""
    
    def test_volume_calculation(self):
        """Test volume calculation from trades."""
        trades = [
            {"price": 0.6, "size": 100},
            {"price": 0.4, "size": 50},
            {"price": 0.5, "size": 200},
        ]
        
        total_volume = sum(float(t["price"]) * float(t["size"]) for t in trades)
        assert total_volume == (0.6 * 100 + 0.4 * 50 + 0.5 * 200)
        assert total_volume == 180.0
    
    def test_percentage_calculation(self):
        """Test percentage calculations."""
        total_trades = 100
        yes_trades = 60
        no_trades = 40
        
        yes_pct = (yes_trades / total_trades) * 100
        no_pct = (no_trades / total_trades) * 100
        
        assert yes_pct == 60.0
        assert no_pct == 40.0
        assert yes_pct + no_pct == 100.0
