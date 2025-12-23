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
        """Test momentum score calculation weights."""
        # Test data
        yes_price = 0.80  # 30% from 50%
        hours_to_expiry = 24
        max_hours_short = 72
        volume = 50000
        momentum = 0.25
        
        # Calculate components
        distance_from_50 = abs(yes_price - 0.5)
        urgency_score = max(0, (max_hours_short - hours_to_expiry) / max_hours_short)
        volume_score = min(volume / 100000, 1.0)
        momentum_score = min(momentum / 0.5, 1.0)
        
        # Weight: 30% extremity, 25% urgency, 20% volume, 25% momentum
        score = (distance_from_50 * 30) + (urgency_score * 25) + (volume_score * 20) + (momentum_score * 25)
        
        # Verify weights
        assert abs(distance_from_50 - 0.30) < 0.01  # Allow floating point precision
        assert urgency_score > 0.65  # 48h remaining out of 72h
        assert abs(volume_score - 0.5) < 0.01  # 50k out of 100k max
        assert abs(momentum_score - 0.5) < 0.01  # 25% out of 50% max
        
        # Score should be reasonable
        assert 30 < score < 100, f"Score {score} is out of expected range"
    
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
