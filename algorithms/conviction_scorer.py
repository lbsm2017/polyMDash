"""
Conviction Scoring Algorithm for Polymarket Dashboard.
Prioritizes: Directionality > Expiration > Volume vs Average > Momentum > Trader Count

Priority ranking:
1. Directionality (+++): Mixed positions = LOW conviction by definition
2. Expiration urgency (++): Markets near expiration get highest weight
3. Volume vs average (++): Bets larger than trader's average = HIGH conviction
4. Recent momentum (++): New bets or price changes = HIGH conviction  
5. Number of traders (+): More agreement = better signal
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import math


class ConvictionScorer:
    """
    Conviction scoring with proper priority weighting.
    
    Components (in priority order):
    1. Directionality: Mixed bets kill conviction
    2. Expiration Urgency: Near expiration = HIGH weight (inverse theta)
    3. Volume vs Average: Bigger than usual = conviction signal
    4. Momentum: Recent clustering + volatility
    5. Trader Count: More traders = stronger signal
    """
    
    # Priority weights (percentages of influence)
    DIRECTIONALITY_WEIGHT = 0.50      # 50% - CRITICAL: mixed = kills score
    EXPIRATION_WEIGHT = 0.30          # 30% - Near expiration = urgent
    VOLUME_RATIO_WEIGHT = 0.30        # 30% - Above average = conviction
    MOMENTUM_WEIGHT = 0.30            # 30% - Recent activity = conviction
    TRADER_COUNT_WEIGHT = 0.20        # 20% - More traders = better
    
    # Multiplier ranges
    MAX_EXPIRATION_MULTIPLIER = 3.0   # 3x for markets expiring soon
    MAX_VOLUME_RATIO_MULTIPLIER = 2.0 # 2x for volume 2x above average
    MAX_MOMENTUM_MULTIPLIER = 1.5     # 1.5x for strong recent momentum
    
    # Time constants
    EXPIRATION_URGENCY_DAYS = 30.0    # Decay constant for expiration urgency
    MOMENTUM_WINDOW_HOURS = 1.0       # Time window for momentum clustering
    
    # Base scoring
    BASE_TRADER_SCORE = 10.0          # Points per trader
    BASE_VOLUME_SCORE = 15.0          # Weight for volume component
    
    def __init__(self, tracked_wallets: List[str]):
        """
        Initialize scorer with tracked wallet addresses.
        
        Args:
            tracked_wallets: List of wallet addresses to track
        """
        self.tracked_wallets = set(w.lower() for w in tracked_wallets)
        self.user_profiles = {}  # Track average volume per user
        
    def _is_tracked_user(self, wallet: str) -> bool:
        """Check if wallet belongs to a tracked user."""
        return wallet.lower() in self.tracked_wallets
    
    def _build_user_profiles(self, all_trades: List[Dict]) -> None:
        """
        Build user profiles to track average bet sizes.
        
        Args:
            all_trades: All trades from all markets
        """
        user_volumes = defaultdict(list)
        
        for trade in all_trades:
            wallet = trade.get('proxyWallet', '').lower()
            if not self._is_tracked_user(wallet):
                continue
                
            price = float(trade.get('price', 0))
            size = float(trade.get('size', 0))
            volume = price * size
            
            user_volumes[wallet].append(volume)
        
        # Calculate average volume per user
        for wallet, volumes in user_volumes.items():
            self.user_profiles[wallet] = {
                'avg_volume': sum(volumes) / len(volumes) if volumes else 1000,
                'total_trades': len(volumes)
            }
    
    def _calculate_directionality_multiplier(
        self,
        bullish_volume: float,
        bearish_volume: float,
        bullish_users: int,
        bearish_users: int
    ) -> float:
        """
        Calculate directionality multiplier - KILLS conviction if mixed.
        
        Pure direction (all YES or all NO) = 1.0x
        Mixed positions = 0.0x (ZERO conviction by definition)
        
        Args:
            bullish_volume: Total bullish volume
            bearish_volume: Total bearish volume
            bullish_users: Number of bullish users
            bearish_users: Number of bearish users
            
        Returns:
            Multiplier 0.0 - 1.0
        """
        total_volume = bullish_volume + bearish_volume
        total_users = bullish_users + bearish_users
        
        if total_volume == 0 or total_users == 0:
            return 0.0
        
        # Use BOTH volume and user count for directionality
        volume_ratio = max(bullish_volume, bearish_volume) / total_volume
        user_ratio = max(bullish_users, bearish_users) / total_users
        
        # Average the two ratios (balanced approach)
        combined_ratio = (volume_ratio + user_ratio) / 2.0
        
        # Convert to multiplier:
        # 1.0 (100% agreement) → 1.0x multiplier
        # 0.9 (90% agreement) → 0.8x multiplier  
        # 0.75 (75% agreement) → 0.5x multiplier
        # 0.5 (50/50 split) → 0.0x multiplier (KILLS conviction)
        
        multiplier = max(0.0, 2.0 * (combined_ratio - 0.5))
        
        return multiplier
    
    def _calculate_expiration_urgency(self, end_date_iso: Optional[str]) -> float:
        """
        Calculate expiration urgency multiplier (inverse theta).
        
        Markets closer to expiration = HIGHER multiplier.
        This is the INVERSE of options theta decay.
        
        Args:
            end_date_iso: ISO format end date string
            
        Returns:
            Multiplier 1.0 - 3.0 (higher = more urgent)
        """
        if not end_date_iso:
            return 1.0  # No expiration data = no bonus
        
        try:
            # Parse the end date
            end_dt = datetime.fromisoformat(end_date_iso.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            
            # Calculate days until expiration
            delta = end_dt - now
            days_remaining = delta.total_seconds() / 86400
            
            if days_remaining < 0:
                # Market already expired - very high urgency
                return self.MAX_EXPIRATION_MULTIPLIER
            
            # Exponential urgency: e^(-days/30)
            # < 1 day → ~3.0x
            # 1 week → ~2.0x  
            # 1 month → ~1.7x
            # 6 months → ~1.0x
            
            urgency_factor = math.exp(-days_remaining / self.EXPIRATION_URGENCY_DAYS)
            multiplier = 1.0 + ((self.MAX_EXPIRATION_MULTIPLIER - 1.0) * urgency_factor)
            
            return multiplier
            
        except Exception:
            return 1.0  # Parsing error = no bonus
    
    def _calculate_volume_ratio_multiplier(
        self,
        trades: List[Dict],
        users: set
    ) -> float:
        """
        Calculate volume-vs-average multiplier.
        
        If traders are betting MORE than their usual amount = HIGH conviction.
        
        Args:
            trades: List of trades in this direction
            users: Set of user wallets
            
        Returns:
            Multiplier 1.0 - 2.0 (higher = above average volume)
        """
        if not trades or not self.user_profiles:
            return 1.0
        
        # Calculate average ratio of (actual volume / user average)
        ratios = []
        
        for trade in trades:
            wallet = trade.get('proxyWallet', '').lower()
            if wallet not in self.user_profiles:
                continue
                
            price = float(trade.get('price', 0))
            size = float(trade.get('size', 0))
            volume = price * size
            
            user_avg = self.user_profiles[wallet]['avg_volume']
            if user_avg > 0:
                ratio = volume / user_avg
                ratios.append(ratio)
        
        if not ratios:
            return 1.0
        
        # Average ratio across all trades
        avg_ratio = sum(ratios) / len(ratios)
        
        # Convert to multiplier:
        # 3x average → 2.0x multiplier (max)
        # 2x average → 1.5x multiplier
        # 1x average → 1.0x multiplier
        # 0.5x average → 0.75x multiplier
        
        multiplier = min(self.MAX_VOLUME_RATIO_MULTIPLIER, 0.5 + (avg_ratio * 0.5))
        
        return multiplier
    
    def _calculate_momentum_multiplier(
        self,
        trades: List[Dict],
        prices: List[float]
    ) -> float:
        """
        Calculate momentum from time clustering + price volatility.
        
        Recent trades clustered together = HIGH conviction.
        Recent price movement = HIGH conviction.
        
        Args:
            trades: List of trades
            prices: List of trade prices
            
        Returns:
            Multiplier 1.0 - 1.5
        """
        if len(trades) < 2:
            return 1.0
        
        # Component 1: Time clustering
        timestamps = sorted([t.get('timestamp', 0) for t in trades if t.get('timestamp')])
        
        if timestamps:
            window_seconds = self.MOMENTUM_WINDOW_HOURS * 3600
            recent_trades = 0
            total_intervals = 0
            
            for i in range(len(timestamps) - 1):
                total_intervals += 1
                if timestamps[i + 1] - timestamps[i] <= window_seconds:
                    recent_trades += 1
            
            cluster_ratio = recent_trades / total_intervals if total_intervals > 0 else 0
        else:
            cluster_ratio = 0
        
        # Component 2: Price volatility (recent movement)
        volatility_bonus = 0.0
        if len(prices) >= 3:
            recent_prices = prices[-3:]  # Last 3 trades
            price_range = max(recent_prices) - min(recent_prices)
            # Higher volatility in recent trades = more conviction (up to 0.2 bonus)
            volatility_bonus = min(0.2, price_range * 0.5)
        
        # Combine components
        # High clustering (>50%) = up to 0.5 bonus
        # Volatility = up to 0.2 bonus
        # Total max = 1.5x multiplier
        
        clustering_bonus = cluster_ratio * 0.5 if cluster_ratio > 0.5 else 0
        total_bonus = clustering_bonus + volatility_bonus
        
        multiplier = 1.0 + min(total_bonus, 0.5)
        
        return multiplier
    
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
    
    def score_markets(
        self,
        trades: List[Dict],
        market_data_dict: Optional[Dict[str, Dict]] = None
    ) -> List[Dict]:
        """
        Score and rank markets using priority-weighted conviction model.
        
        Priority ranking:
        1. Directionality (mixed = kills conviction)
        2. Expiration urgency (near expiration = high weight)
        3. Volume vs average (larger than usual = conviction)
        4. Momentum (recent clustering + volatility)
        5. Trader count (more = better)
        
        Args:
            trades: List of trade dictionaries
            market_data_dict: Optional dict mapping slug -> market data (for expiration)
            
        Returns:
            List of market summaries sorted by conviction score
        """
        # Build user profiles first (to know average volumes)
        self._build_user_profiles(trades)
        
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
            'prices': [],
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
            market['prices'].append(price)
            
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
        
        # Compute final scores with NEW priority-based algorithm
        scored_markets = []
        
        for slug, market in markets.items():
            num_bullish = len(market['users_bullish'])
            num_bearish = len(market['users_bearish'])
            total_users = num_bullish + num_bearish
            
            if total_users == 0:
                continue
            
            # Determine dominant direction
            if market['bullish_volume'] >= market['bearish_volume']:
                direction = 'BULLISH'
                dominant_trades = market['bullish_trades']
                dominant_users = market['users_bullish']
                dominant_volume = market['bullish_volume']
            else:
                direction = 'BEARISH'
                dominant_trades = market['bearish_trades']
                dominant_users = market['users_bearish']
                dominant_volume = market['bearish_volume']
            
            # BASE SCORE: Trader count + Volume
            base_score = (
                (total_users * self.BASE_TRADER_SCORE) +
                (math.log1p(dominant_volume / 1000) * self.BASE_VOLUME_SCORE)
            )
            
            # MULTIPLIER 1: Directionality (+++, CRITICAL)
            # Mixed positions = KILLS conviction
            directionality = self._calculate_directionality_multiplier(
                market['bullish_volume'],
                market['bearish_volume'],
                num_bullish,
                num_bearish
            )
            
            # MULTIPLIER 2: Expiration Urgency (++)
            # Near expiration = HIGH weight
            end_date_iso = None
            if market_data_dict and slug in market_data_dict:
                end_date_iso = market_data_dict[slug].get('end_date_iso')
            expiration_urgency = self._calculate_expiration_urgency(end_date_iso)
            
            # MULTIPLIER 3: Volume vs Average (++)
            # Larger than usual = conviction signal
            volume_ratio = self._calculate_volume_ratio_multiplier(
                dominant_trades,
                dominant_users
            )
            
            # MULTIPLIER 4: Momentum (++)
            # Recent clustering + volatility
            momentum = self._calculate_momentum_multiplier(
                dominant_trades,
                market['prices']
            )
            
            # FINAL SCORE = Base × All Multipliers
            # Note: Directionality can reduce to ZERO (mixed positions)
            final_score = (
                base_score *
                directionality *      # Can be 0.0 - kills conviction if mixed
                expiration_urgency *  # 1.0 - 3.0x
                volume_ratio *        # 1.0 - 2.0x
                momentum              # 1.0 - 1.5x
            )
            
            # Calculate weighted average timestamp for recency sorting
            weighted_avg_time = (
                market['weighted_timestamp_sum'] / market['total_volume'] 
                if market['total_volume'] > 0 
                else market['last_activity']
            )
            
            scored_markets.append({
                'slug': slug,
                'market_id': market['market_id'],
                'direction': direction,
                'conviction_score': final_score,
                'consensus_count': len(dominant_users),
                'consensus_users': list(dominant_users),
                'bullish_users': list(market['users_bullish']),
                'bearish_users': list(market['users_bearish']),
                'bullish_volume': market['bullish_volume'],
                'bearish_volume': market['bearish_volume'],
                'total_trades': len(market['trades']),
                'trades': market['trades'],
                'last_activity': market['last_activity'],
                'weighted_avg_time': weighted_avg_time,
                # Debug info
                'directionality_mult': directionality,
                'expiration_mult': expiration_urgency,
                'volume_ratio_mult': volume_ratio,
                'momentum_mult': momentum,
            })
        
        # Sort by conviction score (highest first)
        scored_markets.sort(key=lambda x: x['conviction_score'], reverse=True)
        
        return scored_markets
    
    def get_conviction_level(self, score: float) -> Tuple[str, str]:
        """
        Convert score to human-readable conviction level.
        
        New scale based on priority weighting:
        - High directionality + near expiration + above-average volume = EXTREME
        - Mixed positions or far expiration = LOW
        
        Returns:
            Tuple of (level_name, emoji)
        """
        if score >= 100:
            return ("🔥 EXTREME", "🔥")
        elif score >= 60:
            return ("💎 HIGH", "💎")
        elif score >= 30:
            return ("📈 MODERATE", "📈")
        elif score >= 10:
            return ("👀 LOW", "👀")
        else:
            return ("💤 MINIMAL", "💤")
