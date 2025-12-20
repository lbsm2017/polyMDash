"""
Integration tests for the dashboard components.
"""

import pytest
from datetime import datetime, timedelta


class TestActivityFeed:
    """Test activity feed functionality."""
    
    def test_categorize_outcome(self):
        """Test outcome categorization logic."""
        from app import categorize_outcome
        
        assert categorize_outcome("YES") == "YES"
        assert categorize_outcome("yes") == "YES"
        assert categorize_outcome("NO") == "NO"
        assert categorize_outcome("no") == "NO"
        assert categorize_outcome("Maybe") == "Other"
        assert categorize_outcome("Trump") == "Other"
    
    def test_format_time_ago(self):
        """Test time ago formatting."""
        from app import format_time_ago
        
        now = datetime.now()
        
        # Minutes ago
        dt = now - timedelta(minutes=5)
        result = format_time_ago(dt)
        assert "5m ago" == result
        
        # Hours ago
        dt = now - timedelta(hours=2)
        result = format_time_ago(dt)
        assert "2h ago" == result
        
        # Days ago
        dt = now - timedelta(days=3)
        result = format_time_ago(dt)
        assert "3d ago" == result
        
        # Just now
        result = format_time_ago(now)
        assert "just now" == result
    
    def test_parse_time_window(self):
        """Test time window parsing."""
        from app import parse_time_window
        
        assert parse_time_window("Last 5 minutes") == 5
        assert parse_time_window("Last 15 minutes") == 15
        assert parse_time_window("Last hour") == 60
        assert parse_time_window("Last 24 hours") == 1440
        assert parse_time_window("Unknown") == 15  # Default


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
