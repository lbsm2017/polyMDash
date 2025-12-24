"""
Tests for utility helper functions.
"""

import pytest
from datetime import datetime, timedelta
from utils.helpers import (
    format_address,
    format_currency,
    format_percentage,
    format_timestamp,
    time_ago,
    truncate_text,
    calculate_price_change,
    parse_outcome_prices,
    calculate_implied_probability,
    get_color_for_change,
    validate_market_data,
    get_market_status_emoji,
    format_large_number
)


class TestHelpers:
    """Test suite for helper functions."""
    
    def test_format_address(self):
        """Test wallet address formatting."""
        addr = "0x1234567890abcdef1234567890abcdef12345678"
        formatted = format_address(addr, length=6)
        assert formatted == "0x1234...345678"
        
        # Short address
        short_addr = "0x123"
        assert format_address(short_addr, length=6) == "0x123"
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(1234.567, decimals=3) == "$1,234.567"
        assert format_currency(0) == "$0.00"
    
    def test_format_percentage(self):
        """Test percentage formatting."""
        assert format_percentage(0.75) == "75.0%"
        assert format_percentage(75) == "75.0%"
        assert format_percentage(0.123, decimals=2) == "12.30%"
    
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        dt = datetime(2025, 12, 20, 15, 30, 45)
        formatted = format_timestamp(dt)
        assert "2025-12-20" in formatted
        assert "15:30:45" in formatted
        
        # Test with ISO string
        iso_str = "2025-12-20T15:30:45Z"
        formatted = format_timestamp(iso_str)
        assert "2025-12-20" in formatted
    
    def test_time_ago(self):
        """Test time ago formatting."""
        now = datetime.now()
        
        # Minutes ago
        dt = now - timedelta(minutes=5)
        assert "5 minute" in time_ago(dt)
        
        # Hours ago
        dt = now - timedelta(hours=2)
        assert "2 hour" in time_ago(dt)
        
        # Days ago
        dt = now - timedelta(days=3)
        assert "3 day" in time_ago(dt)
        
        # Just now
        assert time_ago(now) == "just now"
    
    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a long text that needs to be truncated"
        truncated = truncate_text(text, max_length=20)
        assert len(truncated) <= 20
        assert truncated.endswith("...")
        
        # Short text
        short_text = "Short"
        assert truncate_text(short_text, max_length=20) == "Short"
    
    def test_calculate_price_change(self):
        """Test price change calculation."""
        result = calculate_price_change(100, 110)
        assert result['change'] == 10
        assert result['change_percent'] == 10
        assert result['direction'] == 'up'
        
        result = calculate_price_change(100, 90)
        assert result['change'] == -10
        assert result['change_percent'] == -10
        assert result['direction'] == 'down'
        
        result = calculate_price_change(100, 100)
        assert result['direction'] == 'neutral'
        
        # Zero old price
        result = calculate_price_change(0, 50)
        assert result['change'] == 0
        assert result['change_percent'] == 0
    
    def test_parse_outcome_prices(self):
        """Test parsing outcome prices."""
        # From dict
        prices = {"YES": 0.6, "NO": 0.4}
        parsed = parse_outcome_prices(prices)
        assert parsed["YES"] == 0.6
        assert parsed["NO"] == 0.4
        
        # From JSON string
        import json
        json_str = json.dumps(prices)
        parsed = parse_outcome_prices(json_str)
        assert parsed["YES"] == 0.6
    
    def test_calculate_implied_probability(self):
        """Test implied probability calculation."""
        assert calculate_implied_probability(0.6) == 60
        assert calculate_implied_probability(0.5) == 50
        assert calculate_implied_probability(1.0) == 100
    
    def test_get_color_for_change(self):
        """Test color assignment for price changes."""
        assert get_color_for_change(10) == "green"
        assert get_color_for_change(-10) == "red"
        assert get_color_for_change(0) == "gray"
    
    def test_validate_market_data(self):
        """Test market data validation."""
        valid_market = {"id": "123", "question": "Test question?"}
        assert validate_market_data(valid_market) is True
        
        invalid_market = {"id": "123"}
        assert validate_market_data(invalid_market) is False
        
        invalid_market = {"question": "Test?"}
        assert validate_market_data(invalid_market) is False
    
    def test_get_market_status_emoji(self):
        """Test market status emoji."""
        closed_market = {"closed": True}
        assert get_market_status_emoji(closed_market) == "[CLOSED]"
        
        active_market = {"active": True, "closed": False}
        assert get_market_status_emoji(active_market) == "[ACTIVE]"
        
        inactive_market = {"active": False, "closed": False}
        assert get_market_status_emoji(inactive_market) == "[INACTIVE]"
    
    def test_format_large_number(self):
        """Test large number formatting."""
        assert format_large_number(1_500_000_000) == "$1.5B"
        assert format_large_number(2_500_000) == "$2.5M"
        assert format_large_number(3_500) == "$3.5K"
        assert format_large_number(500) == "$500.00"
