"""
Conviction Scoring Algorithm for Polymarket Dashboard.
Weights similar bets from tracked users to surface high-conviction signals.
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import math


class ConvictionScorer:
    """
    Scores market activity based on tracked user consensus and conviction.
    
    Key Signals:
    - Number of users agreeing on direction
    - Total bet size vs baseline
    - Bet size vs user's historical average
    - Momentum (time clustering of trades)
    - Recency decay
    """
    
    # Configurable weights
    USER_COUNT_WEIGHT = 2.0         # Weight per user agreeing
    VOLUME_BASELINE = 1000          # Baseline volume for normalization
    SIZE_VS_AVG_WEIGHT = 1.5        # Weight for bet size vs user average
    MOMENTUM_WEIGHT = 2.0           # Weight for time clustering
    RECENCY_DECAY_HOURS = 6         # Half-life for recency decay
    MOMENTUM_WINDOW_HOURS = 1       # Time window for momentum clustering
    
    def __init__(self, tracked_wallets: List[str]):
        """
        Initialize scorer with tracked wallet addresses.
        
        Args:
            tracked_wallets: List of wallet addresses to track
        """
        self.tracked_wallets = set(w.lower() for w in tracked_wallets)
        self.user_volume_history = defaultdict(list)  # Track per-user volumes
        
    def _is_tracked_user(self, wallet: str) -> bool:
        """Check if wallet belongs to a tracked user."""
        return wallet.lower() in self.tracked_wallets
    
    def _update_user_history(self, wallet: str, volume: float):
        """Update historical volume tracking for user."""
        self.user_volume_history[wallet].append(volume)
    
    def _get_user_avg_volume(self, wallet: str) -> float:
        """Get user's average volume. Returns baseline if no history."""
        volumes = self.user_volume_history.get(wallet, [])
        if not volumes:
            return self.VOLUME_BASELINE
        return sum(volumes) / len(volumes)
    
    def _calculate_momentum_score(self, trades: List[Dict]) -> float:
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
    
    def _calculate_recency_factor(self, timestamp: int) -> float:
        """Calculate exponential decay based on time."""
        if not timestamp:
            return 0.5  # Default if no timestamp
        
        try:
            trade_dt = datetime.fromtimestamp(timestamp)
            hours_ago = (datetime.now() - trade_dt).total_seconds() / 3600
            return math.exp(-hours_ago / self.RECENCY_DECAY_HOURS)
        except:
            return 0.5
    
    def score_markets(self, trades: List[Dict]) -> List[Dict]:
        """
        Score and rank markets by tracked user conviction.
        
        New scoring formula:
        Score = (User Count × 2.0) 
              + (Total Volume / $1000) 
              + (Bet Size vs Avg Ratio × 1.5) 
              + (Momentum Score × 2.0)
              × Recency Decay
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            List of market summaries sorted by conviction score
        """
        # First pass: collect all user volumes for history
        for trade in trades:
            wallet = trade.get('proxyWallet', '').lower()
            if self._is_tracked_user(wallet):
                price = float(trade.get('price', 0))
                size = float(trade.get('size', 0))
                volume = price * size
                self._update_user_history(wallet, volume)
        
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
            })
        
        # Sort by conviction score (highest first), then by recency
        scored_markets.sort(key=lambda x: (x['conviction_score'], x['last_activity']), reverse=True)
        
        return scored_markets
    
    def _calculate_direction_score(
        self, 
        trades: List[Dict], 
        users: set, 
        total_volume: float,
        last_activity: int
    ) -> float:
        """
        Calculate conviction score for one direction (bullish or bearish).
        
        Formula:
        Score = (User Count × 2.0) 
              + (Total Volume / $1000) 
              + (Bet Size vs Avg Ratio × 1.5) 
              + (Momentum Score × 2.0)
              × Recency Decay
        """
        if not trades or not users:
            return 0.0
        
        # Component 1: User count
        user_count_score = len(users) * self.USER_COUNT_WEIGHT
        
        # Component 2: Total volume ratio
        volume_score = total_volume / self.VOLUME_BASELINE
        
        # Component 3: Bet size vs user average
        size_vs_avg_ratios = []
        for trade in trades:
            wallet = trade.get('proxyWallet', '').lower()
            price = float(trade.get('price', 0))
            size = float(trade.get('size', 0))
            volume = price * size
            
            user_avg = self._get_user_avg_volume(wallet)
            if user_avg > 0:
                ratio = volume / user_avg
                size_vs_avg_ratios.append(ratio)
        
        avg_ratio = sum(size_vs_avg_ratios) / len(size_vs_avg_ratios) if size_vs_avg_ratios else 1.0
        size_score = avg_ratio * self.SIZE_VS_AVG_WEIGHT
        
        # Component 4: Momentum (time clustering)
        momentum = self._calculate_momentum_score(trades)
        momentum_score = momentum * self.MOMENTUM_WEIGHT
        
        # Combine all components
        base_score = user_count_score + volume_score + size_score + momentum_score
        
        # Apply recency decay
        recency_factor = self._calculate_recency_factor(last_activity)
        final_score = base_score * recency_factor
        
        return final_score
    
    def get_conviction_level(self, score: float) -> Tuple[str, str]:
        """
        Convert score to human-readable conviction level.
        
        Returns:
            Tuple of (level_name, emoji)
        """
        if score > 15:
            return ("🔥 EXTREME", "🔥")
        elif score > 10:
            return ("💎 HIGH", "💎")
        elif score > 5:
            return ("📈 MODERATE", "📈")
        elif score > 2:
            return ("👀 LOW", "👀")
        else:
            return ("💤 MINIMAL", "💤")
