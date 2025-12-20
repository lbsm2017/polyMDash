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
    - Multiple tracked users betting same direction = higher weight
    - Large position sizes = higher conviction
    - Extreme prices (>0.85 or <0.15) = strong directional bet
    - Recent activity = more relevant
    """
    
    # Configurable weights
    CONSENSUS_WEIGHT = 3.0      # Multiplier for each additional user agreeing
    VOLUME_WEIGHT = 1.0         # Base weight for volume
    EXTREME_PRICE_BONUS = 2.0   # Bonus for bets at extreme prices
    RECENCY_DECAY_HOURS = 6     # Half-life for recency decay
    
    def __init__(self, tracked_wallets: List[str]):
        """
        Initialize scorer with tracked wallet addresses.
        
        Args:
            tracked_wallets: List of wallet addresses to track
        """
        self.tracked_wallets = set(w.lower() for w in tracked_wallets)
        
    def _is_tracked_user(self, wallet: str) -> bool:
        """Check if wallet belongs to a tracked user."""
        return wallet.lower() in self.tracked_wallets
    
    def _compute_trade_conviction(self, trade: Dict) -> float:
        """
        Compute conviction score for a single trade.
        
        Factors:
        - Volume (price × size)
        - Price extremity (closer to 0 or 1 = higher conviction)
        - Recency (exponential decay)
        """
        price = float(trade.get('price', 0.5))
        size = float(trade.get('size', 0))
        volume = price * size
        timestamp = trade.get('timestamp', 0)
        
        # Base conviction from volume
        conviction = math.log1p(volume) * self.VOLUME_WEIGHT
        
        # Bonus for extreme prices (betting when confident)
        price_extremity = abs(price - 0.5) * 2  # 0-1 scale, 1 = extreme
        if price_extremity > 0.7:  # Price > 0.85 or < 0.15
            conviction *= (1 + self.EXTREME_PRICE_BONUS * price_extremity)
        
        # Recency decay
        if timestamp:
            try:
                trade_dt = datetime.fromtimestamp(timestamp)
                hours_ago = (datetime.now() - trade_dt).total_seconds() / 3600
                recency_factor = math.exp(-hours_ago / self.RECENCY_DECAY_HOURS)
                conviction *= recency_factor
            except:
                pass
        
        return conviction
    
    def score_markets(self, trades: List[Dict]) -> List[Dict]:
        """
        Score and rank markets by tracked user conviction.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            List of market summaries sorted by conviction score
        """
        # Group trades by market
        markets = defaultdict(lambda: {
            'trades': [],
            'users_bullish': set(),    # Users betting YES
            'users_bearish': set(),    # Users betting NO
            'bullish_volume': 0,
            'bearish_volume': 0,
            'bullish_conviction': 0,
            'bearish_conviction': 0,
            'last_activity': 0,
            'slug': '',
            'market_id': '',
        })
        
        for trade in trades:
            wallet = trade.get('proxyWallet', '').lower()
            
            # Only count tracked users for consensus
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
            
            # Track user positions
            if is_bullish:
                market['users_bullish'].add(wallet)
                market['bullish_volume'] += volume
                market['bullish_conviction'] += self._compute_trade_conviction(trade)
            elif is_bearish:
                market['users_bearish'].add(wallet)
                market['bearish_volume'] += volume
                market['bearish_conviction'] += self._compute_trade_conviction(trade)
            
            # Track most recent activity
            if timestamp > market['last_activity']:
                market['last_activity'] = timestamp
        
        # Compute final scores with consensus weighting
        scored_markets = []
        for slug, market in markets.items():
            num_bullish = len(market['users_bullish'])
            num_bearish = len(market['users_bearish'])
            
            # Consensus bonus: more users = exponentially higher score
            bullish_consensus = 1 + (num_bullish - 1) * self.CONSENSUS_WEIGHT if num_bullish > 0 else 0
            bearish_consensus = 1 + (num_bearish - 1) * self.CONSENSUS_WEIGHT if num_bearish > 0 else 0
            
            final_bullish_score = market['bullish_conviction'] * bullish_consensus
            final_bearish_score = market['bearish_conviction'] * bearish_consensus
            
            # Dominant direction
            if final_bullish_score > final_bearish_score:
                direction = 'BULLISH'
                dominant_score = final_bullish_score
                consensus_count = num_bullish
                consensus_users = list(market['users_bullish'])
            else:
                direction = 'BEARISH'
                dominant_score = final_bearish_score
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
    
    def get_conviction_level(self, score: float) -> Tuple[str, str]:
        """
        Convert score to human-readable conviction level.
        
        Returns:
            Tuple of (level_name, emoji)
        """
        if score > 50:
            return ("🔥 EXTREME", "🔥")
        elif score > 20:
            return ("💎 HIGH", "💎")
        elif score > 10:
            return ("📈 MODERATE", "📈")
        elif score > 5:
            return ("👀 LOW", "👀")
        else:
            return ("💤 MINIMAL", "💤")
