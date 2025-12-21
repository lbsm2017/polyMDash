"""
Comprehensive tests for the new priority-based conviction scoring algorithm.

Tests cover:
1. Directionality (+++): Mixed positions killing conviction
2. Expiration urgency (++): Near expiration boosting scores
3. Volume vs average (++): Above-average bets = conviction
4. Momentum (++): Recent clustering and volatility
5. Integration scenarios combining multiple factors
"""

import pytest
from datetime import datetime, timedelta, timezone
from algorithms.conviction_scorer import ConvictionScorer


class TestDirectionalityMultiplier:
    """Test directionality multiplier - the most critical factor."""
    
    def test_pure_bullish_direction(self):
        """100% bullish should give 1.0x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        mult = scorer._calculate_directionality_multiplier(
            bullish_volume=10000,
            bearish_volume=0,
            bullish_users=5,
            bearish_users=0
        )
        assert mult == 1.0
    
    def test_pure_bearish_direction(self):
        """100% bearish should give 1.0x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        mult = scorer._calculate_directionality_multiplier(
            bullish_volume=0,
            bearish_volume=10000,
            bullish_users=0,
            bearish_users=5
        )
        assert mult == 1.0
    
    def test_90_percent_agreement(self):
        """90% agreement should give ~0.8x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        mult = scorer._calculate_directionality_multiplier(
            bullish_volume=9000,
            bearish_volume=1000,
            bullish_users=9,
            bearish_users=1
        )
        # 90% → (90% + 90%) / 2 = 90% → 2*(0.9-0.5) = 0.8
        assert mult == pytest.approx(0.8, abs=0.01)
    
    def test_75_percent_agreement(self):
        """75% agreement should give 0.5x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        mult = scorer._calculate_directionality_multiplier(
            bullish_volume=7500,
            bearish_volume=2500,
            bullish_users=3,
            bearish_users=1
        )
        # 75% → 2*(0.75-0.5) = 0.5
        assert mult == pytest.approx(0.5, abs=0.01)
    
    def test_50_50_split_kills_conviction(self):
        """50/50 split should give 0.0x multiplier (KILLS conviction)."""
        scorer = ConvictionScorer(['0x1'])
        mult = scorer._calculate_directionality_multiplier(
            bullish_volume=5000,
            bearish_volume=5000,
            bullish_users=3,
            bearish_users=3
        )
        # 50% → 2*(0.5-0.5) = 0.0
        assert mult == 0.0
    
    def test_60_40_split_low_conviction(self):
        """60/40 split should give low multiplier (0.2x)."""
        scorer = ConvictionScorer(['0x1'])
        mult = scorer._calculate_directionality_multiplier(
            bullish_volume=6000,
            bearish_volume=4000,
            bullish_users=3,
            bearish_users=2
        )
        # 60% → 2*(0.6-0.5) = 0.2
        assert mult == pytest.approx(0.2, abs=0.05)
    
    def test_volume_and_user_mismatch(self):
        """When volume and user ratios differ, use average."""
        scorer = ConvictionScorer(['0x1'])
        # 90% volume, but only 60% users
        mult = scorer._calculate_directionality_multiplier(
            bullish_volume=9000,
            bearish_volume=1000,
            bullish_users=3,
            bearish_users=2
        )
        # Volume: 90%, Users: 60% → avg = 75% → 2*(0.75-0.5) = 0.5
        assert mult == pytest.approx(0.5, abs=0.01)
    
    def test_empty_market_zero_conviction(self):
        """Empty market should have zero conviction."""
        scorer = ConvictionScorer(['0x1'])
        mult = scorer._calculate_directionality_multiplier(
            bullish_volume=0,
            bearish_volume=0,
            bullish_users=0,
            bearish_users=0
        )
        assert mult == 0.0


class TestExpirationUrgency:
    """Test expiration urgency multiplier - inverse theta."""
    
    def test_expires_in_hours(self):
        """Market expiring in < 1 day should get ~3.0x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        
        # 12 hours from now
        future = datetime.now(timezone.utc) + timedelta(hours=12)
        end_date_iso = future.isoformat()
        
        mult = scorer._calculate_expiration_urgency(end_date_iso)
        assert mult >= 2.5  # Very high urgency
        assert mult <= 3.0  # Max urgency
    
    def test_expires_in_one_week(self):
        """Market expiring in 1 week should get ~2.6x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        
        future = datetime.now(timezone.utc) + timedelta(days=7)
        end_date_iso = future.isoformat()
        
        mult = scorer._calculate_expiration_urgency(end_date_iso)
        assert mult >= 2.3
        assert mult <= 2.8
    
    def test_expires_in_one_month(self):
        """Market expiring in 1 month should get ~1.7x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        
        future = datetime.now(timezone.utc) + timedelta(days=30)
        end_date_iso = future.isoformat()
        
        mult = scorer._calculate_expiration_urgency(end_date_iso)
        assert mult >= 1.5
        assert mult <= 1.9
    
    def test_expires_in_six_months(self):
        """Market expiring in 6 months should get ~1.0x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        
        future = datetime.now(timezone.utc) + timedelta(days=180)
        end_date_iso = future.isoformat()
        
        mult = scorer._calculate_expiration_urgency(end_date_iso)
        assert mult >= 1.0
        assert mult <= 1.2
    
    def test_already_expired(self):
        """Already expired market should get max urgency (3.0x)."""
        scorer = ConvictionScorer(['0x1'])
        
        past = datetime.now(timezone.utc) - timedelta(days=1)
        end_date_iso = past.isoformat()
        
        mult = scorer._calculate_expiration_urgency(end_date_iso)
        assert mult == 3.0
    
    def test_no_expiration_data(self):
        """No expiration data should give 1.0x (no bonus)."""
        scorer = ConvictionScorer(['0x1'])
        
        mult = scorer._calculate_expiration_urgency(None)
        assert mult == 1.0
        
        mult = scorer._calculate_expiration_urgency('')
        assert mult == 1.0
    
    def test_invalid_date_format(self):
        """Invalid date should fallback to 1.0x."""
        scorer = ConvictionScorer(['0x1'])
        
        mult = scorer._calculate_expiration_urgency('invalid-date')
        assert mult == 1.0


class TestVolumeRatioMultiplier:
    """Test volume vs average multiplier."""
    
    def test_trading_3x_average(self):
        """Trading 3x average should give 2.0x multiplier (max)."""
        scorer = ConvictionScorer(['0x1'])
        
        # Build profile with average of 1000
        scorer.user_profiles = {
            '0x1': {'avg_volume': 1000, 'total_trades': 10}
        }
        
        trades = [
            {'proxyWallet': '0x1', 'price': 0.5, 'size': 6000}  # Volume = 3000
        ]
        
        mult = scorer._calculate_volume_ratio_multiplier(trades, {'0x1'})
        # Ratio = 3000/1000 = 3.0 → min(2.0, 0.5 + 3*0.5) = min(2.0, 2.0) = 2.0
        assert mult == 2.0
    
    def test_trading_2x_average(self):
        """Trading 2x average should give 1.5x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        
        scorer.user_profiles = {
            '0x1': {'avg_volume': 1000, 'total_trades': 10}
        }
        
        trades = [
            {'proxyWallet': '0x1', 'price': 0.5, 'size': 4000}  # Volume = 2000
        ]
        
        mult = scorer._calculate_volume_ratio_multiplier(trades, {'0x1'})
        # Ratio = 2.0 → 0.5 + 2*0.5 = 1.5
        assert mult == 1.5
    
    def test_trading_at_average(self):
        """Trading at average should give 1.0x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        
        scorer.user_profiles = {
            '0x1': {'avg_volume': 1000, 'total_trades': 10}
        }
        
        trades = [
            {'proxyWallet': '0x1', 'price': 0.5, 'size': 2000}  # Volume = 1000
        ]
        
        mult = scorer._calculate_volume_ratio_multiplier(trades, {'0x1'})
        # Ratio = 1.0 → 0.5 + 1*0.5 = 1.0
        assert mult == 1.0
    
    def test_trading_below_average(self):
        """Trading below average should give <1.0x multiplier."""
        scorer = ConvictionScorer(['0x1'])
        
        scorer.user_profiles = {
            '0x1': {'avg_volume': 2000, 'total_trades': 10}
        }
        
        trades = [
            {'proxyWallet': '0x1', 'price': 0.5, 'size': 2000}  # Volume = 1000
        ]
        
        mult = scorer._calculate_volume_ratio_multiplier(trades, {'0x1'})
        # Ratio = 0.5 → 0.5 + 0.5*0.5 = 0.75
        assert mult == 0.75
    
    def test_multiple_traders_average_ratio(self):
        """Multiple traders should average their ratios."""
        scorer = ConvictionScorer(['0x1', '0x2'])
        
        scorer.user_profiles = {
            '0x1': {'avg_volume': 1000, 'total_trades': 10},
            '0x2': {'avg_volume': 2000, 'total_trades': 5}
        }
        
        trades = [
            {'proxyWallet': '0x1', 'price': 0.5, 'size': 4000},  # Ratio = 2.0
            {'proxyWallet': '0x2', 'price': 0.6, 'size': 5000}   # Ratio = 1.5
        ]
        
        mult = scorer._calculate_volume_ratio_multiplier(trades, {'0x1', '0x2'})
        # Avg ratio = (2.0 + 1.5) / 2 = 1.75 → 0.5 + 1.75*0.5 = 1.375
        assert mult == pytest.approx(1.375, abs=0.01)
    
    def test_no_user_profiles(self):
        """No user profiles should give 1.0x (no bonus/penalty)."""
        scorer = ConvictionScorer(['0x1'])
        scorer.user_profiles = {}
        
        trades = [{'proxyWallet': '0x1', 'price': 0.5, 'size': 2000}]
        
        mult = scorer._calculate_volume_ratio_multiplier(trades, {'0x1'})
        assert mult == 1.0


class TestMomentumMultiplier:
    """Test momentum from clustering and volatility."""
    
    def test_all_trades_clustered(self):
        """All trades within 1 hour should give high momentum."""
        scorer = ConvictionScorer(['0x1'])
        
        base_time = 1000000
        trades = [
            {'timestamp': base_time, 'price': 0.5},
            {'timestamp': base_time + 1800, 'price': 0.52},  # 30 min later
            {'timestamp': base_time + 3000, 'price': 0.55}   # 50 min from start
        ]
        prices = [0.5, 0.52, 0.55]
        
        mult = scorer._calculate_momentum_multiplier(trades, prices)
        # All within 1 hour = 100% clustering = 0.5 bonus
        # Price range = 0.05, volatility bonus = min(0.2, 0.05*0.5) = 0.025
        # Total = 1.0 + 0.5 + 0.025 = 1.525, capped at 1.5
        assert mult >= 1.4
        assert mult <= 1.5
    
    def test_trades_spread_out(self):
        """Trades spread over days should give low momentum."""
        scorer = ConvictionScorer(['0x1'])
        
        base_time = 1000000
        trades = [
            {'timestamp': base_time, 'price': 0.5},
            {'timestamp': base_time + 86400, 'price': 0.51},  # 1 day later
            {'timestamp': base_time + 172800, 'price': 0.52}  # 2 days later
        ]
        prices = [0.5, 0.51, 0.52]
        
        mult = scorer._calculate_momentum_multiplier(trades, prices)
        # No clustering (>1hr apart) = 0% clustering = no bonus
        # Low volatility = minimal bonus
        assert mult >= 1.0
        assert mult <= 1.1
    
    def test_high_price_volatility(self):
        """High price volatility should add momentum bonus."""
        scorer = ConvictionScorer(['0x1'])
        
        base_time = 1000000
        trades = [
            {'timestamp': base_time, 'price': 0.3},
            {'timestamp': base_time + 100, 'price': 0.8},  # Big jump, within 1hr
        ]
        prices = [0.3, 0.8]
        
        mult = scorer._calculate_momentum_multiplier(trades, prices)
        # 2 trades within 1 hour = 100% clustering = 0.5 bonus
        # Price range = 0.5, volatility = min(0.2, 0.5*0.5) = 0.2 bonus
        # Total = 1.0 + 0.5 = 1.5 (capped)
        assert mult >= 1.45
        assert mult <= 1.5
    
    def test_single_trade_no_momentum(self):
        """Single trade should give 1.0x (no momentum)."""
        scorer = ConvictionScorer(['0x1'])
        
        trades = [{'timestamp': 1000000, 'price': 0.5}]
        prices = [0.5]
        
        mult = scorer._calculate_momentum_multiplier(trades, prices)
        assert mult == 1.0


class TestUserProfileBuilding:
    """Test user profile building for volume tracking."""
    
    def test_build_profiles_from_trades(self):
        """Should correctly calculate average volumes per user."""
        scorer = ConvictionScorer(['0x1', '0x2'])
        
        trades = [
            {'proxyWallet': '0x1', 'price': 0.5, 'size': 2000},  # Vol = 1000
            {'proxyWallet': '0x1', 'price': 0.6, 'size': 5000},  # Vol = 3000
            {'proxyWallet': '0x2', 'price': 0.4, 'size': 5000},  # Vol = 2000
        ]
        
        scorer._build_user_profiles(trades)
        
        # User 1: avg = (1000 + 3000) / 2 = 2000
        assert scorer.user_profiles['0x1']['avg_volume'] == 2000
        assert scorer.user_profiles['0x1']['total_trades'] == 2
        
        # User 2: avg = 2000 / 1 = 2000
        assert scorer.user_profiles['0x2']['avg_volume'] == 2000
        assert scorer.user_profiles['0x2']['total_trades'] == 1
    
    def test_ignore_untracked_users(self):
        """Should ignore trades from untracked users."""
        scorer = ConvictionScorer(['0x1'])
        
        trades = [
            {'proxyWallet': '0x1', 'price': 0.5, 'size': 2000},
            {'proxyWallet': '0x999', 'price': 0.6, 'size': 5000},  # Not tracked
        ]
        
        scorer._build_user_profiles(trades)
        
        assert '0x1' in scorer.user_profiles
        assert '0x999' not in scorer.user_profiles


class TestIntegrationScenarios:
    """Test complete scoring with combined factors."""
    
    def test_extreme_conviction_scenario(self):
        """
        EXTREME conviction: Pure direction + expires soon + above avg + clustered
        Should get very high score (>100).
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3'])
        
        base_time = int(datetime.now().timestamp())
        future = datetime.now(timezone.utc) + timedelta(hours=6)
        
        trades = [
            # All bullish, recent, larger than usual
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.8, 
             'size': 10000, 'timestamp': base_time, 'slug': 'test-market', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.82, 
             'size': 8000, 'timestamp': base_time + 1800, 'slug': 'test-market', 'market': 'm1'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.85, 
             'size': 12000, 'timestamp': base_time + 3000, 'slug': 'test-market', 'market': 'm1'},
        ]
        
        market_data = {
            'test-market': {
                'end_date_iso': future.isoformat()
            }
        }
        
        scored = scorer.score_markets(trades, market_data_dict=market_data)
        
        assert len(scored) == 1
        market = scored[0]
        
        # Should have very high conviction
        assert market['conviction_score'] > 100
        assert market['direction'] == 'BULLISH'
        assert market['directionality_mult'] == 1.0  # Pure direction
        assert market['expiration_mult'] > 2.5  # Expires soon
    
    def test_low_conviction_mixed_positions(self):
        """
        LOW conviction: Mixed positions
        Should get very low score due to directionality killing it.
        """
        scorer = ConvictionScorer(['0x1', '0x2'])
        
        base_time = int(datetime.now().timestamp())
        
        trades = [
            # Split positions
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6, 
             'size': 5000, 'timestamp': base_time, 'slug': 'mixed-market', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'No', 'price': 0.4, 
             'size': 5000, 'timestamp': base_time, 'slug': 'mixed-market', 'market': 'm1'},
        ]
        
        scored = scorer.score_markets(trades)
        
        assert len(scored) == 1
        market = scored[0]
        
        # Should have very low conviction due to split
        # Volume: 60/40 (3000 YES vs 2000 NO), Users: 50/50 → avg = 55% → 2*(0.55-0.5) = 0.1
        assert market['conviction_score'] < 10  # Very low
        assert market['directionality_mult'] == pytest.approx(0.1, abs=0.01)  # Very low multiplier
    
    def test_moderate_conviction_distant_expiration(self):
        """
        MODERATE conviction: Good direction but far expiration
        Should get moderate score.
        """
        scorer = ConvictionScorer(['0x1', '0x2'])
        
        base_time = int(datetime.now().timestamp())
        future = datetime.now(timezone.utc) + timedelta(days=180)
        
        trades = [
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7, 
             'size': 5000, 'timestamp': base_time, 'slug': 'distant-market', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.72, 
             'size': 5000, 'timestamp': base_time, 'slug': 'distant-market', 'market': 'm1'},
        ]
        
        market_data = {
            'distant-market': {
                'end_date_iso': future.isoformat()
            }
        }
        
        scored = scorer.score_markets(trades, market_data_dict=market_data)
        
        assert len(scored) == 1
        market = scored[0]
        
        # Moderate conviction
        assert 20 < market['conviction_score'] < 80
        assert market['directionality_mult'] == 1.0  # Good direction
        assert market['expiration_mult'] < 1.2  # Far out = low urgency
    
    def test_multiple_markets_ranking(self):
        """
        Multiple markets should be ranked correctly by conviction.
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3'])
        
        base_time = int(datetime.now().timestamp())
        soon = datetime.now(timezone.utc) + timedelta(days=1)
        later = datetime.now(timezone.utc) + timedelta(days=90)
        
        trades = [
            # Market 1: High conviction (pure + soon)
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.8, 
             'size': 10000, 'timestamp': base_time, 'slug': 'high-conv', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.82, 
             'size': 10000, 'timestamp': base_time, 'slug': 'high-conv', 'market': 'm1'},
            
            # Market 2: Mixed (low conviction)
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6, 
             'size': 5000, 'timestamp': base_time, 'slug': 'mixed', 'market': 'm2'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'No', 'price': 0.4, 
             'size': 5000, 'timestamp': base_time, 'slug': 'mixed', 'market': 'm2'},
            
            # Market 3: Moderate (pure but far)
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'No', 'price': 0.3, 
             'size': 8000, 'timestamp': base_time, 'slug': 'moderate', 'market': 'm3'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'No', 'price': 0.28, 
             'size': 8000, 'timestamp': base_time, 'slug': 'moderate', 'market': 'm3'},
        ]
        
        market_data = {
            'high-conv': {'end_date_iso': soon.isoformat()},
            'mixed': {'end_date_iso': soon.isoformat()},
            'moderate': {'end_date_iso': later.isoformat()},
        }
        
        scored = scorer.score_markets(trades, market_data_dict=market_data)
        
        assert len(scored) == 3
        
        # Should be sorted by conviction (high to low)
        assert scored[0]['slug'] == 'high-conv'
        assert scored[2]['slug'] == 'mixed'  # Lowest due to 50/50 split
        
        # Verify scores
        assert scored[0]['conviction_score'] > scored[1]['conviction_score']
        assert scored[1]['conviction_score'] > scored[2]['conviction_score']


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_trades_list(self):
        """Empty trades should return empty results."""
        scorer = ConvictionScorer(['0x1'])
        scored = scorer.score_markets([])
        assert scored == []
    
    def test_no_tracked_users_in_trades(self):
        """Trades from untracked users should be ignored."""
        scorer = ConvictionScorer(['0x1'])
        
        trades = [
            {'proxyWallet': '0x999', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6, 
             'size': 5000, 'timestamp': 100000, 'slug': 'market', 'market': 'm1'},
        ]
        
        scored = scorer.score_markets(trades)
        assert scored == []
    
    def test_invalid_trade_data(self):
        """Should handle trades with missing fields gracefully."""
        scorer = ConvictionScorer(['0x1'])
        
        trades = [
            {'proxyWallet': '0x1'},  # Missing most fields
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes'},  # Missing price/size
        ]
        
        # Should not crash
        scored = scorer.score_markets(trades)
        # May have results with zero volume, or empty
        assert isinstance(scored, list)
    
    def test_case_insensitive_wallet_matching(self):
        """Wallet addresses should be matched case-insensitively."""
        scorer = ConvictionScorer(['0xABC123'])
        
        assert scorer._is_tracked_user('0xabc123')
        assert scorer._is_tracked_user('0xABC123')
        assert scorer._is_tracked_user('0xAbC123')
    
    def test_conviction_level_labels(self):
        """Test conviction level classification."""
        scorer = ConvictionScorer(['0x1'])
        
        level, emoji = scorer.get_conviction_level(150)
        assert "EXTREME" in level
        assert emoji == "🔥"
        
        level, emoji = scorer.get_conviction_level(70)
        assert "HIGH" in level
        assert emoji == "💎"
        
        level, emoji = scorer.get_conviction_level(40)
        assert "MODERATE" in level
        assert emoji == "📈"
        
        level, emoji = scorer.get_conviction_level(15)
        assert "LOW" in level
        assert emoji == "👀"
        
        level, emoji = scorer.get_conviction_level(5)
        assert "MINIMAL" in level
        assert emoji == "💤"