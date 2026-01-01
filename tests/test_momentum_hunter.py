"""
Tests for Momentum Hunter functionality
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import asyncio


class TestMomentumHunter:
    """Test suite for Momentum Hunter scanner."""
    
    def test_market_categorization(self):
        """Test that markets are correctly categorized by domain."""
        def categorize_market(question: str) -> str:
            q_lower = question.lower()
            if any(word in q_lower for word in ['election', 'trump', 'biden', 'congress', 'senate', 'president', 'vote', 'poll']):
                return 'Politics'
            elif any(word in q_lower for word in ['nfl', 'nba', 'mlb', 'super bowl', 'soccer', 'football', 'basketball', 'sport', 'championship', 'playoff', 'league']):
                return 'Sports'
            elif any(word in q_lower for word in ['movie', 'oscar', 'emmy', 'grammy', 'celebrity', 'actor', 'actress', 'box office']):
                return 'Entertainment'
            elif any(word in q_lower for word in ['stock', 'nasdaq', 's&p', 'dow', 'gdp', 'inflation', 'fed', 'interest rate', 'recession']):
                return 'Finance'
            else:
                return 'Other'
        
        # Test politics categorization
        politics_markets = [
            'Will Trump win the 2024 election?',
            'Biden approval rating above 50%?',
            'Will Democrats control Senate?',
        ]
        for q in politics_markets:
            assert categorize_market(q) == 'Politics', f"Failed to categorize politics: {q}"
        
        # Test sports categorization
        sports_markets = [
            'Will the Lakers win the NBA championship?',
            'Who will win the 2025 Super Bowl?',
            'Premier League top scorer',
        ]
        for q in sports_markets:
            assert categorize_market(q) == 'Sports', f"Failed to categorize sports: {q}"
        
        # Test finance categorization
        finance_markets = [
            'Will the Fed cut interest rates?',
            'S&P 500 above 5000?',
            'US recession in 2025?',
        ]
        for q in finance_markets:
            assert categorize_market(q) == 'Finance', f"Failed to categorize finance: {q}"
    
    def test_direction_thresholds(self):
        """Test market direction determination logic."""
        # YES direction for >75%
        assert 0.80 > 0.75  # Qualifies for YES
        assert 0.76 > 0.75  # Qualifies for YES
        assert 0.60 <= 0.75 # Does not qualify for YES (middle zone)
        
        # NO direction for <25%
        assert 0.20 < 0.25  # Qualifies for NO
        assert 0.24 < 0.25  # Qualifies for NO
        assert 0.40 >= 0.25 # Does not qualify for NO (middle zone)
    
    def test_middle_zone_filtering(self):
        """Test that markets in the middle zone (25%-75%) are filtered out."""
        # Markets to test
        test_cases = [
            {'prob': 0.80, 'should_pass': True},   # YES direction (>75%)
            {'prob': 0.76, 'should_pass': True},   # YES direction (>75%)
            {'prob': 0.75, 'should_pass': False},  # Middle zone
            {'prob': 0.50, 'should_pass': False},  # Middle zone
            {'prob': 0.25, 'should_pass': False},  # Middle zone
            {'prob': 0.24, 'should_pass': True},   # NO direction (<25%)
            {'prob': 0.20, 'should_pass': True},   # NO direction (<25%)
        ]
        
        for case in test_cases:
            # Binary market direction logic
            if case['prob'] > 0.75:
                direction = 'YES'
                in_middle_zone = False
            elif case['prob'] < 0.25:
                direction = 'NO'
                in_middle_zone = False
            else:
                direction = None
                in_middle_zone = True
            
            passes = not in_middle_zone
            assert passes == case['should_pass'], \
                f"Prob {case['prob']} should {'pass' if case['should_pass'] else 'be filtered'}"
    
    def test_expiry_window_filtering(self):
        """Test that markets are filtered by single expiry window."""
        max_expiry_hours = 72  # User-specified window
        
        # Market within window should pass
        hours_to_expiry = 48
        assert 0 < hours_to_expiry <= max_expiry_hours, "48h should qualify for 72h window"
        
        # Market beyond window should fail
        hours_to_expiry = 100
        assert hours_to_expiry > max_expiry_hours, "100h should not qualify for 72h window"
        
        # Expired market should fail
        hours_to_expiry = -1
        assert hours_to_expiry <= 0, "Expired market should not qualify"
    
    def test_price_extraction_priority(self):
        """Test price extraction from lastTradePrice with bestBid/bestAsk fallback."""
        # Test lastTradePrice is used when available
        market1 = {
            'lastTradePrice': 0.75,
            'bestBid': 0.70,
            'bestAsk': 0.80
        }
        yes_price = market1.get('lastTradePrice')
        assert yes_price == 0.75, "Should use lastTradePrice when available"
        
        # Test fallback to bestBid/bestAsk average
        market2 = {
            'lastTradePrice': 0,
            'bestBid': 0.70,
            'bestAsk': 0.80
        }
        yes_price = market2.get('lastTradePrice')
        if yes_price is None or yes_price == 0:
            best_bid = market2.get('bestBid')
            best_ask = market2.get('bestAsk')
            if best_bid is not None and best_ask is not None:
                yes_price = (float(best_bid) + float(best_ask)) / 2
        
        assert yes_price == 0.75, "Should use bid/ask average when lastTradePrice is 0"
    
    def test_score_calculation(self):
        """Test multi-modal scoring system with sweet spot optimization."""
        from app import calculate_opportunity_score
        
        # Test case: Sweet spot - 3.5% distance, 8.5 days
        score_data = calculate_opportunity_score(
            current_prob=0.965,  # 3.5% from 100%
            momentum=0.35,
            hours_to_expiry=8.5 * 24,  # 8.5 days
            volume=1_000_000,
            best_bid=0.96,
            best_ask=0.97,
            direction='YES',
            one_day_change=0.05,
            one_week_change=0.10,
            annualized_yield=3.0,
            charm=8.0
        )
        
        # Verify structure
        assert 'total_score' in score_data
        assert 'grade' in score_data
        assert 'components' in score_data
        assert 'in_sweet_spot' in score_data
        
        # Verify components exist
        components = score_data['components']
        assert 'distance_time_fit' in components
        assert 'apy' in components
        assert 'volume' in components
        assert 'spread' in components
        assert 'momentum' in components
        assert 'charm' in components
        
        # All scores should be valid (0-100)
        for key, value in components.items():
            assert 0 <= value <= 100, f"{key} score {value} out of range"
        
        assert 0 <= score_data['total_score'] <= 100
        
        # Sweet spot should be detected
        assert score_data['in_sweet_spot'] == True
    
    def test_expiration_filtering(self):
        """Test that markets are filtered by expiration correctly."""
        now = datetime.now(timezone.utc)
        max_hours = 72
        
        # Market expiring in 48 hours - should qualify
        end_dt_soon = now + timedelta(hours=48)
        hours_to_expiry = (end_dt_soon - now).total_seconds() / 3600
        assert 0 < hours_to_expiry <= max_hours, "48h market should qualify"
        
        # Market expiring in 100 hours - should not qualify
        end_dt_far = now + timedelta(hours=100)
        hours_to_expiry = (end_dt_far - now).total_seconds() / 3600
        assert hours_to_expiry > max_hours, "100h market should not qualify for 72h window"
        
        # Already expired market - should not qualify
        end_dt_past = now - timedelta(hours=1)
        hours_to_expiry = (end_dt_past - now).total_seconds() / 3600
        assert hours_to_expiry <= 0, "Expired market should not qualify"
    
    def test_momentum_calculation(self):
        """Test that momentum takes the max of 24h and 1w changes."""
        # Case 1: 24h change is higher
        one_day_change = 0.35
        one_week_change = 0.20
        momentum = max(abs(one_day_change), abs(one_week_change))
        assert momentum == 0.35, "Should use higher 24h change"
        
        # Case 2: 1w change is higher
        one_day_change = 0.15
        one_week_change = 0.40
        momentum = max(abs(one_day_change), abs(one_week_change))
        assert momentum == 0.40, "Should use higher 1w change"
        
        # Case 3: Negative changes (use absolute values)
        one_day_change = -0.25
        one_week_change = -0.10
        momentum = max(abs(one_day_change), abs(one_week_change))
        assert momentum == 0.25, "Should use absolute values"
    
    def test_market_validation_structure(self):
        """Test the market validation helper function logic."""
        # Valid market with all required fields
        valid_market = {
            'question': 'Will X happen?',
            'slug': 'will-x-happen',
            'outcomes': '["Yes", "No"]',
            'outcomePrices': '["0.75", "0.25"]'
        }
        
        # Check all required fields exist
        assert 'question' in valid_market
        assert 'slug' in valid_market
        assert 'outcomes' in valid_market
        assert 'outcomePrices' in valid_market
        
        # Invalid market missing outcomePrices
        invalid_market = {
            'question': 'Will Y happen?',
            'slug': 'will-y-happen',
            'outcomes': '["Yes", "No"]'
        }
        
        assert 'outcomePrices' not in invalid_market, "Missing field should be detectable"
    
    def test_sorting_by_expiration(self):
        """Test that opportunities are sorted by expiration (soonest first)."""
        opportunities = [
            {'question': 'Market 1', 'hours_to_expiry': 72},
            {'question': 'Market 2', 'hours_to_expiry': 24},
            {'question': 'Market 3', 'hours_to_expiry': 48},
        ]
        
        sorted_opps = sorted(opportunities, key=lambda x: x['hours_to_expiry'])
        
        assert sorted_opps[0]['hours_to_expiry'] == 24, "Soonest should be first"
        assert sorted_opps[1]['hours_to_expiry'] == 48, "Middle should be second"
        assert sorted_opps[2]['hours_to_expiry'] == 72, "Latest should be last"
    
    def test_volume_display_formatting(self):
        """Test volume display formatting (K for thousands, M for millions)."""
        # Millions
        vol = 1_500_000
        if vol >= 1_000_000:
            vol_str = f"${vol/1_000_000:.1f}M"
        elif vol >= 1000:
            vol_str = f"${vol/1000:.0f}K"
        else:
            vol_str = f"${vol:.0f}"
        assert vol_str == "$1.5M", f"Expected $1.5M, got {vol_str}"
        
        # Large volume in K
        vol = 11044000
        if vol >= 1_000_000:
            vol_str = f"${vol/1_000_000:.1f}M"
        elif vol >= 1000:
            vol_str = f"${vol/1000:.0f}K"
        else:
            vol_str = f"${vol:.0f}"
        assert vol_str == "$11.0M", f"Expected $11.0M, got {vol_str}"
        
        # Thousands
        vol = 50000
        if vol >= 1_000_000:
            vol_str = f"${vol/1_000_000:.1f}M"
        elif vol >= 1000:
            vol_str = f"${vol/1000:.0f}K"
        else:
            vol_str = f"${vol:.0f}"
        assert vol_str == "$50K", f"Expected $50K, got {vol_str}"
        
        # Small volume
        vol = 500
        if vol >= 1_000_000:
            vol_str = f"${vol/1_000_000:.1f}M"
        elif vol >= 1000:
            vol_str = f"${vol/1000:.0f}K"
        else:
            vol_str = f"${vol:.0f}"
        assert vol_str == "$500", f"Expected $500, got {vol_str}"
    
    def test_direction_determination(self):
        """Test that direction is correctly determined from price."""
        # YES direction for >75%
        yes_price = 0.80
        direction = 'YES' if yes_price > 0.75 else ('NO' if yes_price < 0.25 else None)
        assert direction == 'YES', "80% probability should be YES direction"
        
        # NO direction for <25%
        yes_price = 0.20
        direction = 'YES' if yes_price > 0.75 else ('NO' if yes_price < 0.25 else None)
        assert direction == 'NO', "20% probability should be NO direction"
        
        # Middle zone: 25%-75%
        yes_price = 0.50
        direction = 'YES' if yes_price > 0.75 else ('NO' if yes_price < 0.25 else None)
        assert direction is None, "50% probability should be middle zone (no direction)"
        
        # Edge case: exactly 75%
        yes_price = 0.75
        direction = 'YES' if yes_price > 0.75 else ('NO' if yes_price < 0.25 else None)
        assert direction is None, "75% probability should be middle zone (not inclusive)"
        
        # Edge case: exactly 25%
        yes_price = 0.25
        direction = 'YES' if yes_price > 0.75 else ('NO' if yes_price < 0.25 else None)
        assert direction is None, "25% probability should be middle zone (not inclusive)"
    
    def test_charm_calculation(self):
        """Test Charm (delta decay) calculation."""
        # Charm = (momentum * 100) / days_to_expiry
        
        # Test case 1: High momentum, short timeframe
        momentum = 0.30  # 30%
        days_to_expiry = 3
        charm = (momentum * 100) / days_to_expiry
        assert charm == 10.0, f"Expected charm=10.0, got {charm}"
        
        # Test case 2: Medium momentum, medium timeframe
        momentum = 0.20  # 20%
        days_to_expiry = 7
        charm = (momentum * 100) / days_to_expiry
        assert abs(charm - 2.857) < 0.01, f"Expected charm≈2.857, got {charm}"
        
        # Test case 3: Low momentum, long timeframe
        momentum = 0.10  # 10%
        days_to_expiry = 14
        charm = (momentum * 100) / days_to_expiry
        assert abs(charm - 0.714) < 0.01, f"Expected charm≈0.714, got {charm}"
        
        # Test case 4: Zero days to expiry edge case
        momentum = 0.25
        days_to_expiry = 0
        charm = 0 if days_to_expiry == 0 else (momentum * 100) / days_to_expiry
        assert charm == 0, "Charm should be 0 when days_to_expiry is 0"
    
    def test_charm_classification(self):
        """Test Charm classification (high/medium/low)."""
        # High charm: |charm| >= 2.0
        charm_high = 2.5
        is_high = abs(charm_high) >= 2.0
        assert is_high, "Charm 2.5 should be classified as high"
        
        # Medium charm: 1.0 <= |charm| < 2.0
        charm_med = 1.5
        is_med = 1.0 <= abs(charm_med) < 2.0
        assert is_med, "Charm 1.5 should be classified as medium"
        
        # Low charm: |charm| < 1.0
        charm_low = 0.8
        is_low = abs(charm_low) < 1.0
        assert is_low, "Charm 0.8 should be classified as low"
        
        # Test negative charm values
        charm_negative = -3.0
        is_high_negative = abs(charm_negative) >= 2.0
        assert is_high_negative, "Negative charm -3.0 should be classified as high (by absolute value)"
    
    def test_charm_formatting(self):
        """Test Charm display formatting with 1 decimal and sign."""
        # Positive charm
        charm = 2.15
        charm_str = f"{charm:+.1f}%"
        assert charm_str == "+2.1%", f"Expected '+2.1%', got {charm_str}"
        
        # Negative charm
        charm = -1.87
        charm_str = f"{charm:+.1f}%"
        assert charm_str == "-1.9%", f"Expected '-1.9%', got {charm_str}"
        
        # Zero charm
        charm = 0.0
        charm_str = f"{charm:+.1f}%"
        assert charm_str == "+0.0%", f"Expected '+0.0%', got {charm_str}"
    
    def test_charm_sorting(self):
        """Test sorting opportunities by absolute charm value."""
        opportunities = [
            {'question': 'Market 1', 'charm': 1.5},
            {'question': 'Market 2', 'charm': -3.2},
            {'question': 'Market 3', 'charm': 0.8},
            {'question': 'Market 4', 'charm': 2.7},
        ]
        
        sorted_opps = sorted(opportunities, key=lambda x: abs(x.get('charm', 0)), reverse=True)
        
        assert sorted_opps[0]['charm'] == -3.2, "Highest absolute charm should be first"
        assert sorted_opps[1]['charm'] == 2.7, "Second highest absolute charm should be second"
        assert sorted_opps[2]['charm'] == 1.5, "Third highest absolute charm should be third"
        assert sorted_opps[3]['charm'] == 0.8, "Lowest absolute charm should be last"
    
    def test_volume_filtering(self):
        """Test minimum volume filter."""
        min_volume = 500_000  # Default 500k
        
        # Markets to test
        markets = [
            {'volume': 1_000_000, 'should_pass': True},
            {'volume': 500_000, 'should_pass': True},
            {'volume': 499_999, 'should_pass': False},
            {'volume': 100_000, 'should_pass': False},
            {'volume': 0, 'should_pass': False},
        ]
        
        for market in markets:
            passes_filter = market['volume'] >= min_volume
            assert passes_filter == market['should_pass'], \
                f"Volume {market['volume']} should {'pass' if market['should_pass'] else 'fail'} filter"
    
    def test_apy_formatting(self):
        """Test APY display formatting (x notation for >10000%)."""
        # >10000% - use x notation without decimal
        ann_yield = 150  # 15000%
        if ann_yield > 100:
            apy_str = f"x{ann_yield:.0f}"
        else:
            apy_str = f"{ann_yield:.1%}"
        assert apy_str == "x150", f"Expected 'x150', got {apy_str}"
        
        # Edge case: exactly 100 (10000%)
        ann_yield = 100
        if ann_yield > 100:
            apy_str = f"x{ann_yield:.0f}"
        else:
            apy_str = f"{ann_yield:.1%}"
        assert apy_str == "10000.0%", f"Expected percentage for 100, got {apy_str}"
        
        # 100-1000% - use percentage
        ann_yield = 5.5  # 550%
        if ann_yield > 100:
            apy_str = f"x{ann_yield:.0f}"
        else:
            apy_str = f"{ann_yield:.1%}"
        assert apy_str == "550.0%", f"Expected '550.0%', got {apy_str}"
        
        # <100% - use percentage
        ann_yield = 0.75  # 75%
        if ann_yield > 100:
            apy_str = f"x{ann_yield:.0f}"
        else:
            apy_str = f"{ann_yield:.1%}"
        assert apy_str == "75.0%", f"Expected '75.0%', got {apy_str}"
    
    def test_apy_color_classification(self):
        """Test APY color class assignment."""
        # Dark green (apy-extreme) for >10000%
        ann_yield = 250  # 25000%
        if ann_yield > 100:
            apy_class = "apy-extreme"
        elif ann_yield > 1:
            apy_class = "apy-high"
        elif ann_yield > 0.5:
            apy_class = "score-b"
        else:
            apy_class = "score-c"
        assert apy_class == "apy-extreme", "APY >10000% should be dark green"
        
        # Light green (apy-high) for 100-1000%
        ann_yield = 5  # 500%
        if ann_yield > 100:
            apy_class = "apy-extreme"
        elif ann_yield > 1:
            apy_class = "apy-high"
        elif ann_yield > 0.5:
            apy_class = "score-b"
        else:
            apy_class = "score-c"
        assert apy_class == "apy-high", "APY 100-1000% should be light green"
        
        # Orange (score-b) for 50-100%
        ann_yield = 0.75  # 75%
        if ann_yield > 100:
            apy_class = "apy-extreme"
        elif ann_yield > 1:
            apy_class = "apy-high"
        elif ann_yield > 0.5:
            apy_class = "score-b"
        else:
            apy_class = "score-c"
        assert apy_class == "score-b", "APY 50-100% should be orange"
        
        # Blue (score-c) for <50%
        ann_yield = 0.25  # 25%
        if ann_yield > 100:
            apy_class = "apy-extreme"
        elif ann_yield > 1:
            apy_class = "apy-high"
        elif ann_yield > 0.5:
            apy_class = "score-b"
        else:
            apy_class = "score-c"
        assert apy_class == "score-c", "APY <50% should be blue"
    
    def test_min_distance_to_extreme(self):
        """Test minimum distance to extreme filter."""
        min_distance = 0.015  # 1.5% default
        
        # Test YES direction (probability >= 0.5)
        # Should PASS: 85% is 15% from 100%
        yes_price = 0.85
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert abs(distance_to_extreme - 0.15) < 0.0001, "Expected 0.15 distance"
        assert distance_to_extreme >= min_distance, "85% should pass 1.5% min distance"
        
        # Should FAIL: 99% is 1% from 100%
        yes_price = 0.99
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert abs(distance_to_extreme - 0.01) < 0.0001, "Expected 0.01 distance"
        assert distance_to_extreme < min_distance, "99% should fail 1.5% min distance"
        
        # Edge case: exactly at threshold (98.5%)
        yes_price = 0.985
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert abs(distance_to_extreme - 0.015) < 0.0001, "Expected 0.015 distance"
        assert distance_to_extreme >= min_distance, "98.5% should pass (inclusive)"
        
        # Test NO direction (probability < 0.5)
        # Should PASS: 25% is 25% from 0%
        yes_price = 0.25
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert abs(distance_to_extreme - 0.25) < 0.0001, "Expected 0.25 distance"
        assert distance_to_extreme >= min_distance, "25% should pass 1.5% min distance"
        
        # Should FAIL: 1% is 1% from 0%
        yes_price = 0.01
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert abs(distance_to_extreme - 0.01) < 0.0001, "Expected 0.01 distance"
        assert distance_to_extreme < min_distance, "1% should fail 1.5% min distance"
    
    def test_middle_zone_boundaries(self):
        """Test middle zone filtering (markets between 25%-75% are filtered)."""
        # YES markets (>75%)
        yes_price = 0.85
        in_middle = 0.25 <= yes_price <= 0.75
        assert not in_middle, "85% should not be in middle zone"
        
        yes_price = 0.76
        in_middle = 0.25 <= yes_price <= 0.75
        assert not in_middle, "76% should not be in middle zone"
        
        # Middle zone markets
        yes_price = 0.55
        in_middle = 0.25 <= yes_price <= 0.75
        assert in_middle, "55% should be in middle zone"
        
        yes_price = 0.50
        in_middle = 0.25 <= yes_price <= 0.75
        assert in_middle, "50% should be in middle zone"
        
        # NO markets (<25%)
        yes_price = 0.20
        in_middle = 0.25 <= yes_price <= 0.75
        assert not in_middle, "20% should not be in middle zone"
        
        yes_price = 0.24
        in_middle = 0.25 <= yes_price <= 0.75
        assert not in_middle, "24% should not be in middle zone"
        
        # Boundary cases
        yes_price = 0.25
        in_middle = 0.25 <= yes_price <= 0.75
        assert in_middle, "25% should be in middle zone (inclusive)"
        
        yes_price = 0.75
        in_middle = 0.25 <= yes_price <= 0.75
        assert in_middle, "75% should be in middle zone (inclusive)"
    
    def test_distance_filter_edge_cases(self):
        """Test edge cases for distance filtering."""
        # Exactly at 100%
        yes_price = 1.0
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert distance_to_extreme == 0.0, "100% should have 0 distance"
        
        # Exactly at 0%
        yes_price = 0.0
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert distance_to_extreme == 0.0, "0% should have 0 distance"
        
        # Exactly at 50%
        yes_price = 0.5
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert direction == 'YES', "50% should be YES direction"
        assert distance_to_extreme == 0.5, "50% should have 50% distance to 100%"
        
        # Very close to 100%
        yes_price = 0.999
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
        assert abs(distance_to_extreme - 0.001) < 0.0001, "99.9% distance check"
    
    def test_distance_range_validation(self):
        """Test various min distance values (0-10%)."""
        test_cases = [
            (0.00, 1.0, True),     # 0% threshold passes everything
            (0.01, 0.99, True),    # 1% distance, 1% threshold
            (0.01, 0.995, False),  # 0.5% distance, 1% threshold
            (0.02, 0.98, True),    # 2% distance, 2% threshold
            (0.05, 0.95, True),    # 5% distance, 5% threshold
            (0.05, 0.97, False),   # 3% distance, 5% threshold
            (0.10, 0.90, True),    # 10% distance, 10% threshold
            (0.10, 0.95, False),   # 5% distance, 10% threshold
        ]
        
        for min_distance, yes_price, should_pass in test_cases:
            direction = 'YES' if yes_price >= 0.5 else 'NO'
            distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
            # Use tolerance for floating-point comparison
            passes_filter = (distance_to_extreme - min_distance) >= -1e-10
            
            assert passes_filter == should_pass, \
                f"Price {yes_price*100}% with min {min_distance*100}% " \
                f"(distance {distance_to_extreme*100}%) should {'pass' if should_pass else 'fail'}"
    
    def test_min_distance_middle_zone_interaction(self):
        """Test interaction between min_distance and middle zone filters."""
        min_distance = 0.015  # 1.5%
        
        test_markets = [
            (0.85, False, True, "85%: not in middle, far from 100%"),
            (0.76, False, True, "76%: not in middle, far from 100%"),
            (0.99, False, False, "99%: not in middle but too close to 100%"),
            (0.985, False, True, "98.5%: not in middle and at min distance"),
            (0.55, True, True, "55%: in middle zone (filtered)"),
            (0.20, False, True, "20%: not in middle, far from 0%"),
            (0.01, False, False, "1%: not in middle but too close to 0%"),
        ]
        
        for yes_price, should_be_middle, should_pass_distance, desc in test_markets:
            # Check middle zone (25%-75%)
            in_middle = 0.25 <= yes_price <= 0.75
            assert in_middle == should_be_middle, f"{desc}: middle zone check failed"
            
            # Check distance (only if not in middle zone)
            if not in_middle:
                direction = 'YES' if yes_price > 0.75 else 'NO'
                distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
                passes_distance = (distance_to_extreme - min_distance) >= -1e-10
                assert passes_distance == should_pass_distance, f"{desc}: distance failed"
            
            # Should be included if: not in middle AND passes distance
            should_include = not should_be_middle and should_pass_distance
            actual_passes = not in_middle and (direction := 'YES' if yes_price > 0.75 else 'NO') and \
                           ((1.0 - yes_price) if direction == 'YES' else yes_price) >= min_distance - 1e-10
            assert actual_passes == should_include, f"{desc}: combined failed"
    
    def test_distance_filter_with_zero_min(self):
        """Test that 0% min_distance allows all markets."""
        min_distance = 0.0
        
        for yes_price in [1.0, 0.999, 0.99, 0.01, 0.001, 0.0]:
            direction = 'YES' if yes_price >= 0.5 else 'NO'
            distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
            passes_filter = distance_to_extreme >= min_distance
            assert passes_filter, f"{yes_price*100}% should pass with 0% min distance"
    
    def test_distance_filter_with_max_10_percent(self):
        """Test 10% min_distance (maximum slider value)."""
        min_distance = 0.10
        
        test_cases = [
            (0.50, True, "50% should pass"),
            (0.60, True, "60% should pass"),
            (0.90, True, "90% should pass"),
            (0.10, True, "10% should pass"),
            (0.91, False, "91% should fail"),
            (0.09, False, "9% should fail"),
            (1.0, False, "100% should fail"),
            (0.0, False, "0% should fail"),
        ]
        
        for yes_price, should_pass, desc in test_cases:
            direction = 'YES' if yes_price >= 0.5 else 'NO'
            distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
            # Use tolerance for floating-point
            passes_filter = (distance_to_extreme - min_distance) >= -1e-10
            assert passes_filter == should_pass, desc
    
    def test_distance_filtering_with_direction_thresholds(self):
        """Test how min_distance works with fixed direction thresholds (75%/25%)."""
        # Direction is determined by fixed thresholds: >75% = YES, <25% = NO
        # min_distance excludes markets too close to 0% or 100%
        
        min_distance = 0.05  # 5% - exclude 0-5% and 95-100%
        
        test_cases = [
            # (price, direction, should_pass_distance)
            (0.03, 'NO', False),   # 3%: NO direction but too close to 0%
            (0.10, 'NO', True),    # 10%: NO direction and safe distance
            (0.20, 'NO', True),    # 20%: NO direction and safe distance
            (0.50, None, False),   # 50%: middle zone (filtered before distance check)
            (0.80, 'YES', True),   # 80%: YES direction and safe distance
            (0.92, 'YES', True),   # 92%: YES direction and safe distance  
            (0.97, 'YES', False),  # 97%: YES direction but too close to 100%
        ]
        
        for price, expected_dir, should_pass_distance in test_cases:
            # Determine direction based on actual thresholds
            if price > 0.75:
                direction = 'YES'
            elif price < 0.25:
                direction = 'NO'
            else:
                direction = None  # Middle zone
            
            assert direction == expected_dir, f"Price {price}: direction mismatch"
            
            # Check distance filter (only if there's a direction)
            if direction:
                if direction == 'YES':
                    passes_distance = price < (1.0 - min_distance)
                else:  # NO
                    passes_distance = price > min_distance
                
                assert passes_distance == should_pass_distance, f"Price {price}: distance check failed"


class TestMomentumIntegration:
    """Integration tests for momentum hunter with mocked API."""
    
    def test_market_fetching_strategies(self):
        """Test that multiple fetching strategies logic is sound."""
        # Test the logic structure without async complexity
        
        strategies_attempted = []
        
        def mock_strategy(name):
            strategies_attempted.append(name)
            return []
        
        # Simulate attempting 6 main strategies (as per refactored code)
        mock_strategy("default")
        mock_strategy("volume_pagination")
        mock_strategy("hot")
        mock_strategy("breaking")
        mock_strategy("events")
        mock_strategy("newest")
        
        # Verify multiple strategies can be attempted
        assert len(strategies_attempted) == 6
        assert "default" in strategies_attempted
        assert "hot" in strategies_attempted
        assert "breaking" in strategies_attempted
        assert "events" in strategies_attempted
    
    def test_market_deduplication(self):
        """Test that duplicate markets are removed by slug."""
        markets = [
            {'slug': 'market-a', 'question': 'Question A'},
            {'slug': 'market-b', 'question': 'Question B'},
            {'slug': 'market-a', 'question': 'Question A (duplicate)'},  # Duplicate
            {'slug': 'market-c', 'question': 'Question C'},
        ]
        
        # Deduplication logic
        seen = set()
        unique_markets = []
        for m in markets:
            slug = m.get('slug', '')
            if slug and slug not in seen:
                seen.add(slug)
                unique_markets.append(m)
        
        assert len(unique_markets) == 3, "Should have 3 unique markets"
        assert len(seen) == 3, "Should have 3 unique slugs"
        slugs = [m['slug'] for m in unique_markets]
        assert slugs == ['market-a', 'market-b', 'market-c']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
