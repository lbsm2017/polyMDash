"""
Conviction Scoring Algorithm for Polymarket Dashboard.
Black-Scholes inspired model with time decay, volatility, and Kelly criterion.
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import math


class ConvictionScorer:
    """
    Advanced conviction scoring inspired by Black-Scholes options pricing model.
    
    Components:
    - Time Decay (Theta): Exponential decay for recency
    - Volatility: Historical price movement dampening
    - Direction Strength: Kelly criterion at price extremes
    - Size Score: Log-scaled position sizing
    - Consensus: Exponential bonus for multiple users
    - Momentum: Time clustering detection
    """
    
    # Black-Scholes inspired parameters
    TIME_DECAY_HOURS = 6.0          # Theta: half-life for time decay
    VOLATILITY_WINDOW = 10          # Number of trades for volatility calc
    MOMENTUM_WINDOW_HOURS = 1.0     # Time clustering window
    
    # Scoring weights
    SIZE_WEIGHT = 15.0              # Weight for position size (log-scaled)
    CONSENSUS_BASE = 1.5            # Exponential base for consensus (1.5^n)
    DIRECTION_WEIGHT = 10.0         # Weight for price extremity
    MOMENTUM_BONUS = 1.3            # Multiplier when momentum detected
    
    # Normalization constants
    VOLUME_SCALE = 10000            # Scale factor for volume normalization
    MAX_SCORE = 100.0               # Maximum possible score
    
    def __init__(self, tracked_wallets: List[str]):
        """
        Initialize scorer with tracked wallet addresses.
        
        Args:
            tracked_wallets: List of wallet addresses to track
        """
        self.tracked_wallets = set(w.lower() for w in tracked_wallets)
        self.trade_history = defaultdict(list)  # Track price history per market
        
    def _is_tracked_user(self, wallet: str) -> bool:
        """Check if wallet belongs to a tracked user."""
        return wallet.lower() in self.tracked_wallets
    
    def _calculate_time_decay(self, timestamp: int) -> float:
        """
        Calculate time decay (Theta) using exponential decay.
        More recent trades have higher weight.
        
        Args:
            timestamp: Unix timestamp of trade
            
        Returns:
            Decay factor between 0 and 1
        """
        if not timestamp:
            return 0.5
        
        try:
            trade_dt = datetime.fromtimestamp(timestamp)
            hours_ago = (datetime.now() - trade_dt).total_seconds() / 3600
            # Exponential decay: e^(-t/τ) where τ is half-life
            return math.exp(-hours_ago / self.TIME_DECAY_HOURS)
        except:
            return 0.5
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """
        Calculate historical volatility from price movements.
        Higher volatility = more noise = lower conviction.
        
        Args:
            prices: List of trade prices
            
        Returns:
            Volatility factor (higher = more volatile)
        """
        if len(prices) < 2:
            return 0.1  # Default low volatility
        
        # Calculate price changes
        changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        
        # Standard deviation of price changes
        mean_change = sum(changes) / len(changes)
        variance = sum((c - mean_change) ** 2 for c in changes) / len(changes)
        volatility = math.sqrt(variance)
        
        # Normalize to 0-1 range (typical prediction market volatility is 0-0.3)
        return min(volatility / 0.3, 1.0)
    
    def _calculate_direction_strength(self, price: float) -> float:
        """
        Calculate conviction from price extremity (Kelly criterion inspired).
        Maximum conviction near 0.05 or 0.95 (strong directional bets).
        
        Args:
            price: Trade price (0-1)
            
        Returns:
            Direction strength score
        """
        # Distance from 0.5 (neutral)
        distance_from_neutral = abs(price - 0.5)
        
        # Kelly-like: conviction increases at extremes
        # Peak at 0.05 and 0.95
        return distance_from_neutral * 2.0  # Scale to 0-1
    
    def _calculate_size_score(self, volume: float) -> float:
        """
        Calculate score from position size using logarithmic scaling.
        Prevents huge bets from dominating.
        
        Args:
            volume: Dollar volume of position
            
        Returns:
            Size score
        """
        # Log scaling to prevent outliers from dominating
        normalized_volume = volume / self.VOLUME_SCALE
        return math.log1p(normalized_volume) * self.SIZE_WEIGHT
    
    def _calculate_consensus_score(self, num_users: int) -> float:
        """
        Calculate exponential consensus bonus.
        Multiple users agreeing = strong signal.
        
        Args:
            num_users: Number of tracked users in same direction
            
        Returns:
            Consensus multiplier
        """
        if num_users <= 0:
            return 0.0
        
        # Exponential growth: 1.5^(n-1)
        # 1 user = 1.0, 2 users = 1.5, 3 users = 2.25, etc.
        return self.CONSENSUS_BASE ** (num_users - 1)
        """
        Calculate momentum score based on time clustering.
        Higher score when trades happen close together in time.
        """
        if len(trades) < 2:
            return 0.0
        
        timestamps = sorted([t.get('timestamp', 0) for t in trades if t.get('timestamp')])
        if not timestamps:
            return 0.0
        
        # Count trades within momentum window
        clustered_trades = 0
        window_seconds = self.MOMENTUM_WINDOW_HOURS * 3600
        
        for i in range(len(timestamps) - 1):
            if timestamps[i + 1] - timestamps[i] <= window_seconds:
                clustered_trades += 1
        
        # Momentum score: ratio of clustered trades
        momentum = clustered_trades / (len(timestamps) - 1) if len(timestamps) > 1 else 0
        return momentum
    
    def _calculate_momentum_bonus(self, trades: List[Dict]) -> float:
        """
        Calculate momentum bonus from time clustering.
        Trades happening close together = coordinated conviction.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Momentum multiplier (1.0 = no bonus, 1.3 = high momentum)
        """
        if len(trades) < 2:
            return 1.0
        
        timestamps = sorted([t.get('timestamp', 0) for t in trades if t.get('timestamp')])
        if not timestamps:
            return 1.0
        
        # Count trades within momentum window
        clustered_trades = 0
        window_seconds = self.MOMENTUM_WINDOW_HOURS * 3600
        
        for i in range(len(timestamps) - 1):
            if timestamps[i + 1] - timestamps[i] <= window_seconds:
                clustered_trades += 1
        
        # Momentum ratio
        momentum_ratio = clustered_trades / (len(timestamps) - 1) if len(timestamps) > 1 else 0
        
        # Apply bonus if significant clustering
        if momentum_ratio > 0.5:  # More than half trades are clustered
            return self.MOMENTUM_BONUS
        
        return 1.0
    
    def _calculate_direction_score(
        self,
        trades: List[Dict],
        users: set,
        total_volume: float,
        last_activity: int
    ) -> float:
        """
        Calculate conviction score for one direction using Black-Scholes inspired model.
        
        Formula:
        Score = (Size Score + Consensus Score + Direction Score) 
                × Time Decay × Volatility Damping × Momentum Bonus
        
        Args:
            trades: Trades in this direction
            users: Set of user wallets in this direction
            total_volume: Total dollar volume
            last_activity: Most recent trade timestamp
            
        Returns:
            Conviction score (0-100)
        """
        if not trades or not users:
            return 0.0
        
        # Extract prices for volatility and direction calculation
        prices = [float(t.get('price', 0.5)) for t in trades]
        avg_price = sum(prices) / len(prices) if prices else 0.5
        
        # 1. Size Score (log-scaled to prevent outliers)
        size_score = self._calculate_size_score(total_volume)
        
        # 2. Consensus Score (exponential bonus for multiple users)
        consensus_score = self._calculate_consensus_score(len(users)) * 10  # Scale up
        
        # 3. Direction Strength (Kelly criterion - conviction at price extremes)
        direction_score = self._calculate_direction_strength(avg_price) * self.DIRECTION_WEIGHT
        
        # 4. Time Decay (Theta - exponential decay for recency)
        time_decay = self._calculate_time_decay(last_activity)
        
        # 5. Volatility Dampening (high volatility = more noise)
        volatility = self._calculate_volatility(prices)
        volatility_factor = 1.0 - (volatility * 0.5)  # Reduce score by up to 50% for high volatility
        
        # 6. Momentum Bonus (time clustering)
        momentum_bonus = self._calculate_momentum_bonus(trades)
        
        # Combine all factors
        base_score = size_score + consensus_score + direction_score
        final_score = base_score * time_decay * volatility_factor * momentum_bonus
        
        # Normalize to 0-100 scale
        return min(final_score, self.MAX_SCORE)
    
    def score_markets(self, trades: List[Dict]) -> List[Dict]:
        """
        Score and rank markets using Black-Scholes inspired conviction model.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            List of market summaries sorted by weighted average time
        """
        # Group trades by market and direction
        markets = defaultdict(lambda: {
            'trades': [],
            'users_bullish': set(),
            'users_bearish': set(),
            'bullish_volume': 0,
            'bearish_volume': 0,
            'bullish_trades': [],
            'bearish_trades': [],
            'last_activity': 0,
            'weighted_timestamp_sum': 0,
            'total_volume': 0,
            'slug': '',
            'market_id': '',
        })
        
        for trade in trades:
            wallet = trade.get('proxyWallet', '').lower()
            
            # Only count tracked users
            if not self._is_tracked_user(wallet):
                continue
                
            slug = trade.get('slug', 'Unknown')
            side = trade.get('side', '').upper()
            outcome = trade.get('outcome', '').upper()
            price = float(trade.get('price', 0))
            size = float(trade.get('size', 0))
            volume = price * size
            timestamp = trade.get('timestamp', 0)
            
            # Determine if bullish or bearish
            is_bullish = (side == 'BUY' and 'YES' in outcome) or (side == 'SELL' and 'NO' in outcome)
            is_bearish = (side == 'BUY' and 'NO' in outcome) or (side == 'SELL' and 'YES' in outcome)
            
            market = markets[slug]
            market['slug'] = slug
            market['market_id'] = trade.get('market', '')
            market['trades'].append(trade)
            
            # Track weighted timestamp for recency sorting
            market['weighted_timestamp_sum'] += timestamp * volume
            market['total_volume'] += volume
            
            # Track user positions and direction-specific trades
            if is_bullish:
                market['users_bullish'].add(wallet)
                market['bullish_volume'] += volume
                market['bullish_trades'].append(trade)
            elif is_bearish:
                market['users_bearish'].add(wallet)
                market['bearish_volume'] += volume
                market['bearish_trades'].append(trade)
            
            # Track most recent activity
            if timestamp > market['last_activity']:
                market['last_activity'] = timestamp
        
        # Compute final scores with new algorithm
        scored_markets = []
        for slug, market in markets.items():
            num_bullish = len(market['users_bullish'])
            num_bearish = len(market['users_bearish'])
            
            # Calculate scores for both directions
            bullish_score = self._calculate_direction_score(
                market['bullish_trades'],
                market['users_bullish'],
                market['bullish_volume'],
                market['last_activity']
            )
            
            bearish_score = self._calculate_direction_score(
                market['bearish_trades'],
                market['users_bearish'],
                market['bearish_volume'],
                market['last_activity']
            )
            
            # Dominant direction
            if bullish_score > bearish_score:
                direction = 'BULLISH'
                dominant_score = bullish_score
                consensus_count = num_bullish
                consensus_users = list(market['users_bullish'])
            else:
                direction = 'BEARISH'
                dominant_score = bearish_score
                consensus_count = num_bearish
                consensus_users = list(market['users_bearish'])
            
            # Calculate weighted average timestamp for sorting
            weighted_avg_time = (market['weighted_timestamp_sum'] / market['total_volume'] 
                                if market['total_volume'] > 0 else market['last_activity'])
            
            scored_markets.append({
                'slug': slug,
                'market_id': market['market_id'],
                'direction': direction,
                'conviction_score': dominant_score,
                'consensus_count': consensus_count,
                'consensus_users': consensus_users,
                'bullish_users': list(market['users_bullish']),
                'bearish_users': list(market['users_bearish']),
                'bullish_volume': market['bullish_volume'],
                'bearish_volume': market['bearish_volume'],
                'total_trades': len(market['trades']),
                'trades': market['trades'],
                'last_activity': market['last_activity'],
                'weighted_avg_time': weighted_avg_time,
            })
        
        # Sort by weighted average time (most recent first)
        scored_markets.sort(key=lambda x: x['weighted_avg_time'], reverse=True)
        
        return scored_markets
    
    def get_conviction_level(self, score: float) -> Tuple[str, str]:
        """
        Convert score to human-readable conviction level.
        Updated for 0-100 scale.
        
        Returns:
            Tuple of (level_name, emoji)
        """
        if score >= 60:
            return ("🔥 EXTREME", "🔥")
        elif score >= 40:
            return ("💎 HIGH", "💎")
        elif score >= 20:
            return ("📈 MODERATE", "📈")
        elif score >= 10:
            return ("👀 LOW", "👀")
        else:
            return ("💤 MINIMAL", "💤")
