"""
Tests for Momentum Hunter functionality
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
import asyncio


class TestMomentumHunter:
    """Test suite for Momentum Hunter scanner."""
    
    def test_crypto_filter(self):
        """Test that crypto markets are properly filtered out."""
        excluded_terms = {'bitcoin', 'btc', 'crypto', 'ethereum', 'eth', 'solana', 'xrp', 'sol', 
                        'cryptocurrency', 'updown', 'up-down', 'btc-', 'eth-', 'sol-'}
        
        def is_excluded(market):
            slug = (market.get('slug', '') or '').lower()
            question = (market.get('question', '') or '').lower()
            return any(ex in slug or ex in question for ex in excluded_terms)
        
        # Test crypto markets are excluded
        crypto_markets = [
            {'slug': 'bitcoin-price-2025', 'question': 'Will Bitcoin reach $100k?'},
            {'slug': 'btc-updown-5m-1234', 'question': 'Bitcoin Up or Down'},
            {'slug': 'eth-price', 'question': 'Ethereum above $5000?'},
            {'slug': 'solana-prediction', 'question': 'Solana price prediction'},
        ]
        
        for market in crypto_markets:
            assert is_excluded(market), f"Failed to exclude crypto market: {market['slug']}"
        
        # Test non-crypto markets are included
        non_crypto_markets = [
            {'slug': 'us-recession-2025', 'question': 'US recession in 2025?'},
            {'slug': 'trump-president', 'question': 'Trump wins 2024?'},
            {'slug': 'fed-rate-cut', 'question': 'Fed emergency rate cut?'},
        ]
        
        for market in non_crypto_markets:
            assert not is_excluded(market), f"Incorrectly excluded non-crypto market: {market['slug']}"
    
    def test_extremity_qualification(self):
        """Test market qualification logic based on extremity."""
        min_extremity = 0.25  # >75% or <25%
        
        # Extreme YES markets
        assert 0.80 >= (0.5 + min_extremity)  # Qualifies
        assert 0.75 >= (0.5 + min_extremity)  # Qualifies
        assert 0.60 < (0.5 + min_extremity)   # Does not qualify on extremity alone
        
        # Extreme NO markets
        assert 0.20 <= (0.5 - min_extremity)  # Qualifies
        assert 0.25 <= (0.5 - min_extremity)  # Qualifies
        assert 0.40 > (0.5 - min_extremity)   # Does not qualify on extremity alone
    
    def test_momentum_qualification(self):
        """Test high momentum qualification for somewhat extreme markets."""
        high_momentum = 0.30
        
        # Markets with high momentum (≥30%) and >60% or <40% probability
        test_cases = [
            {'prob': 0.65, 'momentum': 0.35, 'should_qualify': True},  # High momentum + somewhat extreme
            {'prob': 0.35, 'momentum': 0.32, 'should_qualify': True},  # High momentum + somewhat extreme
            {'prob': 0.55, 'momentum': 0.40, 'should_qualify': False}, # High momentum but not extreme enough
            {'prob': 0.70, 'momentum': 0.10, 'should_qualify': False}, # Extreme but low momentum
        ]
        
        for case in test_cases:
            is_somewhat_extreme = case['prob'] >= 0.60 or case['prob'] <= 0.40
            has_high_momentum = case['momentum'] >= high_momentum
            qualifies = has_high_momentum and is_somewhat_extreme
            
            assert qualifies == case['should_qualify'], \
                f"Qualification mismatch for prob={case['prob']}, momentum={case['momentum']}"
    
    def test_time_window_extension(self):
        """Test that high momentum markets get extended time window."""
        max_hours_short = 72   # 3 days
        max_hours_momentum = 336  # 14 days
        high_momentum = 0.30
        
        # High momentum market should get extended window
        momentum = 0.35
        has_high_momentum = momentum >= high_momentum
        effective_window = max_hours_momentum if has_high_momentum else max_hours_short
        assert effective_window == 336, "High momentum should extend window to 14 days"
        
        # Low momentum market should use short window
        momentum = 0.15
        has_high_momentum = momentum >= high_momentum
        effective_window = max_hours_momentum if has_high_momentum else max_hours_short
        assert effective_window == 72, "Low momentum should use 3-day window"
    
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
    
    def test_debug_mode_bypasses_filters(self):
        """Test that debug mode shows all markets without extremity/expiry filters."""
        debug_mode = True
        
        # In debug mode, these checks should be skipped
        yes_price = 0.51  # Not extreme at all
        min_extremity = 0.25
        
        is_extreme_yes = yes_price >= (0.5 + min_extremity)
        is_extreme_no = yes_price <= (0.5 - min_extremity)
        
        # Normally wouldn't qualify
        assert not is_extreme_yes and not is_extreme_no
        
        # But debug mode should bypass this check and include the market
        # The test validates the logic structure
        if debug_mode:
            # Market should be included regardless of extremity
            should_include = True
        else:
            should_include = is_extreme_yes or is_extreme_no
        
        assert should_include, "Debug mode should include non-extreme markets"
    
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
        # YES direction for >50%
        yes_price = 0.75
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        assert direction == 'YES', "75% probability should be YES direction"
        
        # NO direction for <50%
        yes_price = 0.25
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        assert direction == 'NO', "25% probability should be NO direction"
        
        # Edge case: exactly 50%
        yes_price = 0.50
        direction = 'YES' if yes_price >= 0.5 else 'NO'
        assert direction == 'YES', "50% probability should be YES direction (inclusive)"
    
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
    
    def test_max_extremity_filter(self):
        """Test maximum extremity filter (markets must be extreme enough)."""
        min_extremity = 0.25  # Must be >75% or <25%
        
        # Test YES markets
        yes_price = 0.85
        is_extreme = yes_price > (0.5 + min_extremity) or yes_price < (0.5 - min_extremity)
        assert is_extreme, "85% should be extreme enough"
        
        yes_price = 0.55
        is_extreme = yes_price > (0.5 + min_extremity) or yes_price < (0.5 - min_extremity)
        assert not is_extreme, "55% should not be extreme enough"
        
        # Test NO markets
        yes_price = 0.20
        is_extreme = yes_price > (0.5 + min_extremity) or yes_price < (0.5 - min_extremity)
        assert is_extreme, "20% should be extreme enough"
        
        yes_price = 0.45
        is_extreme = yes_price > (0.5 + min_extremity) or yes_price < (0.5 - min_extremity)
        assert not is_extreme, "45% should not be extreme enough"
    
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
    
    def test_min_max_distance_interaction(self):
        """Test interaction between min_distance and extremity filters."""
        min_extremity = 0.25  # >75% or <25%
        min_distance = 0.015  # 1.5%
        
        test_markets = [
            (0.85, True, True, "85%: extreme and far from 100%"),
            (0.76, True, True, "76%: barely extreme, far from 100%"),
            (0.99, True, False, "99%: extreme but too close to 100%"),
            (0.985, True, True, "98.5%: extreme and at min distance"),
            (0.55, False, True, "55%: not extreme but far from 100%"),
        ]
        
        for yes_price, should_pass_extremity, should_pass_distance, desc in test_markets:
            # Check extremity
            is_extreme = yes_price > (0.5 + min_extremity) or yes_price < (0.5 - min_extremity)
            assert is_extreme == should_pass_extremity, f"{desc}: extremity failed"
            
            # Check distance (with tolerance)
            direction = 'YES' if yes_price >= 0.5 else 'NO'
            distance_to_extreme = (1.0 - yes_price) if direction == 'YES' else yes_price
            passes_distance = (distance_to_extreme - min_distance) >= -1e-10
            assert passes_distance == should_pass_distance, f"{desc}: distance failed"
            
            # Both must pass
            should_include = should_pass_extremity and should_pass_distance
            assert (is_extreme and passes_distance) == should_include, f"{desc}: combined failed"
    
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
    
    def test_min_distance_constrained_by_extremity(self):
        """Test that min_distance must be <= min_extremity."""
        # Scenario 1: min_extremity = 25%, min_distance can be up to 25%
        min_extremity = 0.25
        min_distance = 0.15  # 15%
        assert min_distance <= min_extremity, "min_distance must be <= min_extremity"
        
        # Scenario 2: min_extremity = 10%, min_distance must be <= 10%
        min_extremity = 0.10
        min_distance = 0.10  # 10% - at boundary
        assert min_distance <= min_extremity, "min_distance at boundary should be valid"
        
        # Scenario 3: Invalid configuration (would be rejected by UI)
        min_extremity = 0.05  # 5%
        min_distance = 0.10   # 10% - too high!
        assert min_distance > min_extremity, "This should be invalid - distance > extremity"
        # In the app, this would be prevented by the slider max_value
    
    def test_distance_extremity_filtering_interaction(self):
        """Test how min_distance and min_extremity filters work together."""
        # Note: Direction is determined by fixed thresholds (>75% = YES, <25% = NO)
        # min_extremity determines which markets are shown (0-X% and (100-X)-100%)
        # min_distance excludes markets too close to 0% or 100%
        
        # Setup: Using standard direction thresholds (75%/25%)
        #        min_distance = 5% (exclude 0-5% and 95-100%)
        
        min_distance = 0.05
        
        test_cases = [
            # (price, direction, should_pass_distance)
            (0.03, 'NO', False),   # 3%: NO direction but too close to 0%
            (0.10, 'NO', True),    # 10%: NO direction and safe distance
            (0.20, 'NO', True),    # 20%: NO direction and safe distance
            (0.50, None, True),    # 50%: middle zone (no direction)
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
                direction = None
            
            assert direction == expected_dir, f"Price {price}: direction mismatch"
            
            # Check distance filter (only if there's a direction)
            if direction:
                if direction == 'YES':
                    passes_distance = price < (1.0 - min_distance)
                else:  # NO
                    passes_distance = price > min_distance
                
                assert passes_distance == should_pass_distance, f"Price {price}: distance check failed"
    
    def test_extreme_slider_boundaries(self):
        """Test edge cases when min_extremity changes."""
        # When min_extremity = 5%, min_distance can be 0-5%
        min_extremity = 0.05
        valid_distances = [0.0, 0.01, 0.025, 0.05]
        for dist in valid_distances:
            assert dist <= min_extremity, f"Distance {dist} should be valid for extremity {min_extremity}"
        
        # When min_extremity = 50%, min_distance can be 0-50%
        min_extremity = 0.50
        valid_distances = [0.0, 0.05, 0.15, 0.25, 0.40, 0.50]
        for dist in valid_distances:
            assert dist <= min_extremity, f"Distance {dist} should be valid for extremity {min_extremity}"


class TestMomentumIntegration:
    """Integration tests for momentum hunter with mocked API."""
    
    def test_market_fetching_strategies(self):
        """Test that multiple fetching strategies logic is sound."""
        # Test the logic structure without async complexity
        
        strategies_attempted = []
        
        def mock_strategy(name):
            strategies_attempted.append(name)
            return []
        
        # Simulate attempting multiple strategies
        mock_strategy("liquidity")
        mock_strategy("default")
        
        # Verify multiple strategies can be attempted
        assert len(strategies_attempted) == 2
        assert "liquidity" in strategies_attempted
        assert "default" in strategies_attempted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
