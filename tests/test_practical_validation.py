"""
Test practical scenarios for conviction scoring algorithm.
Validates that scores make sense in real-world trading situations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from algorithms.conviction_scorer import ConvictionScorer


class TestPracticalValidation:
    """Test that conviction scores make practical sense in real-world scenarios."""
    
    def test_whale_bet_near_expiration_beats_small_bet_far_out(self):
        """
        PRACTICAL: A whale betting big near expiration should score 
        higher than a small bet months away.
        """
        scorer = ConvictionScorer(['0x1', '0x2'])
        
        base_time = int(datetime.now().timestamp())
        soon = datetime.now(timezone.utc) + timedelta(hours=12)
        far = datetime.now(timezone.utc) + timedelta(days=180)
        
        trades = [
            # Market 1: Whale bet, expires soon
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.8, 
             'size': 50000, 'timestamp': base_time, 'slug': 'whale-soon', 'market': 'm1'},
            
            # Market 2: Small bet, far away
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6, 
             'size': 1000, 'timestamp': base_time, 'slug': 'small-far', 'market': 'm2'},
        ]
        
        market_data = {
            'whale-soon': {'end_date_iso': soon.isoformat()},
            'small-far': {'end_date_iso': far.isoformat()},
        }
        
        scored = scorer.score_markets(trades, market_data_dict=market_data)
        
        whale_market = next(m for m in scored if m['slug'] == 'whale-soon')
        small_market = next(m for m in scored if m['slug'] == 'small-far')
        
        assert whale_market['conviction_score'] > small_market['conviction_score']
        assert whale_market['conviction_score'] > small_market['conviction_score'] * 2
    
    def test_unanimous_beats_split_decision(self):
        """
        PRACTICAL: 5 traders all agreeing should score much higher 
        than 5 traders split 3-2.
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3', '0x4', '0x5'])
        
        base_time = int(datetime.now().timestamp())
        
        trades = [
            # Market 1: Unanimous YES
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7,
             'size': 5000, 'timestamp': base_time, 'slug': 'unanimous', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.71,
             'size': 5000, 'timestamp': base_time, 'slug': 'unanimous', 'market': 'm1'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.72,
             'size': 5000, 'timestamp': base_time, 'slug': 'unanimous', 'market': 'm1'},
            {'proxyWallet': '0x4', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.73,
             'size': 5000, 'timestamp': base_time, 'slug': 'unanimous', 'market': 'm1'},
            {'proxyWallet': '0x5', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.74,
             'size': 5000, 'timestamp': base_time, 'slug': 'unanimous', 'market': 'm1'},
            
            # Market 2: Split 3-2
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 5000, 'timestamp': base_time, 'slug': 'split', 'market': 'm2'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.61,
             'size': 5000, 'timestamp': base_time, 'slug': 'split', 'market': 'm2'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.62,
             'size': 5000, 'timestamp': base_time, 'slug': 'split', 'market': 'm2'},
            {'proxyWallet': '0x4', 'side': 'BUY', 'outcome': 'No', 'price': 0.4,
             'size': 5000, 'timestamp': base_time, 'slug': 'split', 'market': 'm2'},
            {'proxyWallet': '0x5', 'side': 'BUY', 'outcome': 'No', 'price': 0.41,
             'size': 5000, 'timestamp': base_time, 'slug': 'split', 'market': 'm2'},
        ]
        
        scored = scorer.score_markets(trades)
        
        unanimous = next(m for m in scored if m['slug'] == 'unanimous')
        split = next(m for m in scored if m['slug'] == 'split')
        
        # Unanimous should score much higher (3x or more)
        assert unanimous['conviction_score'] > split['conviction_score'] * 3
        
        # Check directionality multipliers specifically
        assert unanimous['directionality_mult'] > 0.9  # Near perfect
        assert split['directionality_mult'] < 0.4  # Weak due to split

    def test_coordinated_buying_beats_scattered_bets(self):
        """
        PRACTICAL: 3 trades clustered in 1 hour should show more momentum
        than 3 trades scattered over a week.
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3'])
        
        base_time = int(datetime.now().timestamp())
        
        trades = [
            # Market 1: Coordinated (within 1 hour)
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 5000, 'timestamp': base_time, 'slug': 'coordinated', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.65,
             'size': 5000, 'timestamp': base_time + 1800, 'slug': 'coordinated', 'market': 'm1'},  # 30 min
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7,
             'size': 5000, 'timestamp': base_time + 3600, 'slug': 'coordinated', 'market': 'm1'},  # 1 hour
            
            # Market 2: Scattered (over a week)
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 5000, 'timestamp': base_time, 'slug': 'scattered', 'market': 'm2'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.61,
             'size': 5000, 'timestamp': base_time + 259200, 'slug': 'scattered', 'market': 'm2'},  # 3 days
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.62,
             'size': 5000, 'timestamp': base_time + 604800, 'slug': 'scattered', 'market': 'm2'},  # 7 days
        ]
        
        scored = scorer.score_markets(trades)
        
        coordinated = next(m for m in scored if m['slug'] == 'coordinated')
        scattered = next(m for m in scored if m['slug'] == 'scattered')
        
        # Coordinated should have higher momentum multiplier
        assert coordinated['momentum_mult'] > scattered['momentum_mult']
        
        # Overall score should be higher too
        assert coordinated['conviction_score'] > scattered['conviction_score']
    
    def test_score_ranges_are_meaningful(self):
        """
        PRACTICAL: High conviction should be 50-500 range, not absurdly high.
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3'])
        
        base_time = int(datetime.now().timestamp())
        soon = datetime.now(timezone.utc) + timedelta(hours=6)
        
        trades = [
            # High conviction scenario: big bets, soon to expire, unanimous
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.8,
             'size': 20000, 'timestamp': base_time, 'slug': 'high-conviction', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.82,
             'size': 20000, 'timestamp': base_time + 600, 'slug': 'high-conviction', 'market': 'm1'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.84,
             'size': 20000, 'timestamp': base_time + 1200, 'slug': 'high-conviction', 'market': 'm1'},
        ]
        
        market_data = {
            'high-conviction': {'end_date_iso': soon.isoformat()},
        }
        
        scored = scorer.score_markets(trades, market_data_dict=market_data)
        market = scored[0]
        
        # Score should be in meaningful range
        assert 50 < market['conviction_score'] < 500
        
        # Should be HIGH or EXTREME conviction
        level_name = scorer.get_conviction_level(market['conviction_score'])[0]
        assert "HIGH" in level_name or "EXTREME" in level_name
    
    def test_bigger_than_usual_bet_gets_bonus(self):
        """
        PRACTICAL: When a trader bets 3x their usual amount, 
        volume ratio multiplier should be > 1.5x.
        """
        scorer = ConvictionScorer(['0x1'])
        
        base_time = int(datetime.now().timestamp())
        
        # First establish average bet size with historical trades
        historical_trades = [
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.5,
             'size': 2000, 'timestamp': base_time - 86400, 'slug': 'old1', 'market': 'old1'},
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'No', 'price': 0.4,
             'size': 2000, 'timestamp': base_time - 172800, 'slug': 'old2', 'market': 'old2'},
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 2000, 'timestamp': base_time - 259200, 'slug': 'old3', 'market': 'old3'},
        ]
        
        # Big bet - 3x usual amount
        current_trades = [
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7,
             'size': 6000, 'timestamp': base_time, 'slug': 'big-bet', 'market': 'm1'},  # 3x average
        ]
        
        # Score with historical context
        all_trades = historical_trades + current_trades
        scored = scorer.score_markets(all_trades)
        
        big_bet = next(m for m in scored if m['slug'] == 'big-bet')
        
        # Should get volume ratio bonus (> 1.5x)
        assert big_bet['volume_ratio_mult'] > 1.5
    
    def test_expiring_today_beats_expiring_next_year(self):
        """
        PRACTICAL: Same bet size and trader, expiring today should score
        much higher than expiring next year.
        """
        scorer = ConvictionScorer(['0x1'])
        
        base_time = int(datetime.now().timestamp())
        today = datetime.now(timezone.utc) + timedelta(hours=6)
        next_year = datetime.now(timezone.utc) + timedelta(days=365)
        
        trades = [
            # Market 1: Expires today
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7,
             'size': 10000, 'timestamp': base_time, 'slug': 'expires-today', 'market': 'm1'},
            
            # Market 2: Expires next year
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7,
             'size': 10000, 'timestamp': base_time, 'slug': 'expires-next-year', 'market': 'm2'},
        ]
        
        market_data = {
            'expires-today': {'end_date_iso': today.isoformat()},
            'expires-next-year': {'end_date_iso': next_year.isoformat()},
        }
        
        scored = scorer.score_markets(trades, market_data_dict=market_data)
        
        today_market = next(m for m in scored if m['slug'] == 'expires-today')
        next_year_market = next(m for m in scored if m['slug'] == 'expires-next-year')
        
        # Today should score much higher (at least 2x)
        assert today_market['conviction_score'] > next_year_market['conviction_score'] * 2
        
        # Check expiration multipliers specifically
        assert today_market['expiration_mult'] > 2.5  # Near max urgency
        assert next_year_market['expiration_mult'] < 1.1  # Minimal urgency

    def test_price_movement_indicates_momentum(self):
        """
        PRACTICAL: When traders keep buying at higher prices,
        it shows strong conviction (price momentum).
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3'])

        base_time = int(datetime.now().timestamp())

        trades = [
            # Market 1: Rising prices (strong momentum) - 3 trades, bigger price change
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.5,
             'size': 5000, 'timestamp': base_time, 'slug': 'rising', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.65,
             'size': 5000, 'timestamp': base_time + 500, 'slug': 'rising', 'market': 'm1'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.8,
             'size': 5000, 'timestamp': base_time + 1000, 'slug': 'rising', 'market': 'm1'},

            # Market 2: Stable prices (weak momentum) - spread out trades, small price change
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 5000, 'timestamp': base_time, 'slug': 'stable', 'market': 'm2'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.61,
             'size': 5000, 'timestamp': base_time + 86400, 'slug': 'stable', 'market': 'm2'},  # 1 day later
        ]

        scored = scorer.score_markets(trades)

        rising = next(m for m in scored if m['slug'] == 'rising')
        stable = next(m for m in scored if m['slug'] == 'stable')

        # Rising prices with clustering should have higher momentum
        # Rising has 3 trades in 1000 seconds with 0.3 price change
        # Stable has 2 trades over 1 day with 0.01 price change
        assert rising['momentum_mult'] > stable['momentum_mult']

    def test_zero_conviction_for_completely_mixed_signals(self):
        """
        PRACTICAL: Perfect 50/50 split should result in near-zero conviction.
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3', '0x4'])
        
        base_time = int(datetime.now().timestamp())
        
        trades = [
            # Perfect 50/50 split
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 10000, 'timestamp': base_time, 'slug': 'mixed', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.61,
             'size': 10000, 'timestamp': base_time, 'slug': 'mixed', 'market': 'm1'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'No', 'price': 0.4,
             'size': 10000, 'timestamp': base_time, 'slug': 'mixed', 'market': 'm1'},
            {'proxyWallet': '0x4', 'side': 'BUY', 'outcome': 'No', 'price': 0.39,
             'size': 10000, 'timestamp': base_time, 'slug': 'mixed', 'market': 'm1'},
        ]
        
        scored = scorer.score_markets(trades)
        market = scored[0]
        
        # Directionality multiplier should be very low (kills conviction)
        assert market['directionality_mult'] < 0.15
        
        # Overall score should be very low
        assert market['conviction_score'] < 20
        
        # Should be MINIMAL or LOW conviction
        level_name = scorer.get_conviction_level(market['conviction_score'])[0]
        assert "MINIMAL" in level_name or "LOW" in level_name

    def test_single_whale_beats_multiple_small_traders(self):
        """
        PRACTICAL: One whale with large bets and strong conviction indicators
        should score higher than multiple small traders with mixed signals.
        Volume quality matters more than trader count alone.
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3', '0x4', '0x5', '0x6'])

        base_time = int(datetime.now().timestamp())
        soon = datetime.now(timezone.utc) + timedelta(hours=6)
        far = datetime.now(timezone.utc) + timedelta(days=180)

        trades = [
            # Market 1: One whale, expiring soon, unanimous
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7,
             'size': 71428, 'timestamp': base_time, 'slug': 'whale', 'market': 'm1'},  # 50k USD
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.75,
             'size': 66666, 'timestamp': base_time + 500, 'slug': 'whale', 'market': 'm1'},  # Another 50k USD

            # Market 2: Five small traders, far away, somewhat mixed
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 1666, 'timestamp': base_time, 'slug': 'small-traders', 'market': 'm2'},  # 1k USD
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.61,
             'size': 1639, 'timestamp': base_time, 'slug': 'small-traders', 'market': 'm2'},  # 1k USD
            {'proxyWallet': '0x4', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.62,
             'size': 1612, 'timestamp': base_time, 'slug': 'small-traders', 'market': 'm2'},  # 1k USD
            {'proxyWallet': '0x5', 'side': 'BUY', 'outcome': 'No', 'price': 0.38,  # Mixed signal
             'size': 1587, 'timestamp': base_time, 'slug': 'small-traders', 'market': 'm2'},  # 1k USD
            {'proxyWallet': '0x6', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.64,
             'size': 1562, 'timestamp': base_time, 'slug': 'small-traders', 'market': 'm2'},  # 1k USD
        ]

        market_data = {
            'whale': {'end_date_iso': soon.isoformat()},
            'small-traders': {'end_date_iso': far.isoformat()},
        }

        scored = scorer.score_markets(trades, market_data_dict=market_data)

        whale = next(m for m in scored if m['slug'] == 'whale')
        small_traders = next(m for m in scored if m['slug'] == 'small-traders')

        # Whale should score higher:
        # - Massive volume (100k vs 5k total)
        # - Perfect directionality (100% Yes)
        # - Expiring soon (6 hours vs 6 months)
        # - Clustered trades (500 seconds apart)
        # Even though fewer unique traders, quality beats quantity
        assert whale['conviction_score'] > small_traders['conviction_score']

    def test_realistic_conviction_progression(self):
        """
        PRACTICAL: Test that conviction scores progress logically
        from MINIMAL to LOW to MODERATE to HIGH to EXTREME.
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3'])

        base_time = int(datetime.now().timestamp())
        soon = datetime.now(timezone.utc) + timedelta(hours=12)
        medium = datetime.now(timezone.utc) + timedelta(days=30)
        far = datetime.now(timezone.utc) + timedelta(days=180)

        trades = [
            # MINIMAL: Small bet, far away, completely mixed (50/50)
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.5,
             'size': 500, 'timestamp': base_time, 'slug': 'minimal', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'No', 'price': 0.5,
             'size': 500, 'timestamp': base_time, 'slug': 'minimal', 'market': 'm1'},

            # LOW: Small bet, far away, but aligned
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 1000, 'timestamp': base_time, 'slug': 'low', 'market': 'm2'},

            # MODERATE: Decent bet, medium time, multiple aligned traders
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.65,
             'size': 3000, 'timestamp': base_time, 'slug': 'moderate', 'market': 'm3'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.66,
             'size': 3000, 'timestamp': base_time, 'slug': 'moderate', 'market': 'm3'},

            # HIGH: Large bets, expiring soon, perfect alignment
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.75,
             'size': 10000, 'timestamp': base_time, 'slug': 'high', 'market': 'm4'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.76,
             'size': 10000, 'timestamp': base_time + 1000, 'slug': 'high', 'market': 'm4'},

            # EXTREME: Massive bets, expiring very soon, perfect alignment, clustered
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.85,
             'size': 25000, 'timestamp': base_time, 'slug': 'extreme', 'market': 'm5'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.87,
             'size': 25000, 'timestamp': base_time + 300, 'slug': 'extreme', 'market': 'm5'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.90,
             'size': 25000, 'timestamp': base_time + 600, 'slug': 'extreme', 'market': 'm5'},
        ]

        market_data = {
            'minimal': {'end_date_iso': far.isoformat()},
            'low': {'end_date_iso': far.isoformat()},
            'moderate': {'end_date_iso': medium.isoformat()},
            'high': {'end_date_iso': soon.isoformat()},
            'extreme': {'end_date_iso': soon.isoformat()},
        }

        scored = scorer.score_markets(trades, market_data_dict=market_data)

        # Get scores for each level
        scores = {m['slug']: m['conviction_score'] for m in scored}

        # Verify logical progression - each level should be higher
        assert scores['minimal'] < scores['low'], f"minimal ({scores['minimal']}) should be < low ({scores['low']})"
        assert scores['low'] < scores['moderate'], f"low ({scores['low']}) should be < moderate ({scores['moderate']})"
        assert scores['moderate'] < scores['high'], f"moderate ({scores['moderate']}) should be < high ({scores['high']})"
        assert scores['high'] < scores['extreme'], f"high ({scores['high']}) should be < extreme ({scores['extreme']})"

        # Verify the progression makes sense (at least 20% increase between levels)
        assert scores['low'] > scores['minimal'] * 1.2
        assert scores['moderate'] > scores['low'] * 1.2
        assert scores['high'] > scores['moderate'] * 1.5
        assert scores['extreme'] > scores['high'] * 1.2

    def test_scorer_handles_none_market_data(self):
        """
        Test that scorer gracefully handles None market_data_dict.
        This was causing AttributeError in Streamlit when market data failed to fetch.
        """
        scorer = ConvictionScorer(['0x1', '0x2'])

        base_time = int(datetime.now().timestamp())

        trades = [
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7,
             'size': 5000, 'timestamp': base_time, 'slug': 'market1', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.72,
             'size': 5000, 'timestamp': base_time, 'slug': 'market1', 'market': 'm1'},
        ]

        # Should not raise AttributeError or KeyError
        scored = scorer.score_markets(trades, market_data_dict=None)

        # Should return valid scores
        assert len(scored) == 1
        assert scored[0]['conviction_score'] > 0
        assert 'market1' == scored[0]['slug']

    def test_scorer_handles_partial_market_data(self):
        """
        Test that scorer handles case where some markets have data, some don't.
        """
        scorer = ConvictionScorer(['0x1', '0x2', '0x3'])

        base_time = int(datetime.now().timestamp())
        future = datetime.now(timezone.utc) + timedelta(hours=6)

        trades = [
            # Market 1: Has data
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.7,
             'size': 5000, 'timestamp': base_time, 'slug': 'with-data', 'market': 'm1'},
            {'proxyWallet': '0x2', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.72,
             'size': 5000, 'timestamp': base_time, 'slug': 'with-data', 'market': 'm1'},

            # Market 2: No data (will be None in dict or missing)
            {'proxyWallet': '0x1', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.6,
             'size': 4000, 'timestamp': base_time, 'slug': 'no-data', 'market': 'm2'},
            {'proxyWallet': '0x3', 'side': 'BUY', 'outcome': 'Yes', 'price': 0.62,
             'size': 4000, 'timestamp': base_time, 'slug': 'no-data', 'market': 'm2'},
        ]

        market_data = {
            'with-data': {'end_date_iso': future.isoformat()},
            'no-data': None,  # Simulates failed API fetch
        }

        # Should not crash
        scored = scorer.score_markets(trades, market_data_dict=market_data)

        # Should return scores for both markets
        assert len(scored) == 2
        
        # Market with data should have higher expiration multiplier
        with_data = next(m for m in scored if m['slug'] == 'with-data')
        no_data = next(m for m in scored if m['slug'] == 'no-data')
        
        # With data: expiration_mult > 1.0, without: expiration_mult == 1.0
        assert with_data['expiration_mult'] > no_data['expiration_mult']