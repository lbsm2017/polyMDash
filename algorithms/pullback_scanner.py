"""
Pullback Scanner Algorithm for Polymarket Dashboard.
Identifies high-momentum markets near expiration that have pulled back from extremes.

Strategy:
1. Find markets expiring soon (<72h)
2. Detect strong momentum toward 100% or 0% (asymptotic behavior)
3. Current probability must be extreme (>75% or <25%)
4. Identify recent pullback (retracement from peak)
5. Calculate annualized return based on time to expiry

Scoring Components:
- Expiration Urgency: Exponential weight for markets expiring sooner
- Momentum Strength: Size and speed of recent price moves
- Pullback Quality: Optimal pullback percentage (15-30% of move)
- Probability Extremity: Higher score for >85% or <15%
- Recency Weighting: Recent price action weighted more heavily
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import math


class PullbackScanner:
    """
    Scanner for identifying pullback opportunities in high-momentum markets.
    
    Scoring Philosophy:
    - Markets near expiration with strong directional moves get priority
    - Pullbacks create asymmetric entry opportunities
    - Time decay accelerates value in short-dated options
    - Recent momentum is more predictive than old momentum
    """
    
    # Scoring weights
    EXPIRATION_WEIGHT = 0.35          # 35% - Urgency of time decay
    MOMENTUM_WEIGHT = 0.30            # 30% - Strength of directional move
    PULLBACK_WEIGHT = 0.25            # 25% - Quality of pullback setup
    EXTREMITY_WEIGHT = 0.10           # 10% - How extreme current probability is
    
    # Thresholds
    MAX_EXPIRATION_HOURS = 72         # Only scan markets expiring within 72h
    MIN_PROBABILITY = 0.75            # Minimum for YES side (or max 0.25 for NO)
    OPTIMAL_PULLBACK_MIN = 0.10       # 10% pullback minimum
    OPTIMAL_PULLBACK_MAX = 0.35       # 35% pullback maximum
    OPTIMAL_PULLBACK_CENTER = 0.20    # 20% pullback is ideal
    
    # Momentum detection
    MOMENTUM_LOOKBACK_HOURS = 24      # Look back 24h for momentum
    STRONG_MOVE_THRESHOLD = 0.15      # 15% move is "strong"
    EXTREME_MOVE_THRESHOLD = 0.30     # 30% move is "extreme"
    
    # Recency decay (exponential)
    RECENCY_DECAY_HOURS = 6           # Half-life for recency weighting
    
    def __init__(self):
        """Initialize the pullback scanner."""
        pass
    
    def scan_markets(
        self,
        markets: List[Dict],
        price_history: Optional[Dict[str, List[Dict]]] = None
    ) -> List[Dict]:
        """
        Scan markets for pullback opportunities.
        
        Args:
            markets: List of market dictionaries from Gamma API
            price_history: Optional dict mapping market_id -> list of price points
                          Each price point: {'timestamp': datetime, 'price': float}
        
        Returns:
            List of opportunity dictionaries, sorted by score (highest first)
        """
        opportunities = []
        now = datetime.now(timezone.utc)
        
        for market in markets:
            # Extract market data
            market_id = market.get('id') or market.get('condition_id', '')
            question = market.get('question', 'Unknown Market')
            end_date_str = market.get('end_date_iso') or market.get('endDate')
            
            if not end_date_str:
                continue
                
            # Parse end date
            try:
                if isinstance(end_date_str, str):
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                else:
                    end_date = end_date_str
            except (ValueError, AttributeError):
                continue
            
            # Calculate hours to expiration
            hours_to_expiry = (end_date - now).total_seconds() / 3600
            
            # Filter: Must expire within MAX_EXPIRATION_HOURS
            if hours_to_expiry > self.MAX_EXPIRATION_HOURS or hours_to_expiry <= 0:
                continue
            
            # Get current probability
            current_prob = self._extract_probability(market)
            if current_prob is None:
                continue
            
            # Filter: Probability must be extreme (>75% or <25%)
            if not (current_prob >= self.MIN_PROBABILITY or current_prob <= (1 - self.MIN_PROBABILITY)):
                continue
            
            # Determine if we're tracking YES or NO side
            tracking_yes = current_prob >= 0.5
            tracked_prob = current_prob if tracking_yes else (1 - current_prob)
            
            # Get price history for this market
            history = price_history.get(market_id, []) if price_history else []
            
            # Analyze momentum and pullback
            momentum_data = self._analyze_momentum(
                current_prob=tracked_prob,
                price_history=history,
                now=now,
                tracking_yes=tracking_yes
            )
            
            if not momentum_data:
                continue
            
            # Check if there's a valid pullback
            if momentum_data['pullback_pct'] < self.OPTIMAL_PULLBACK_MIN:
                continue  # No pullback or too small
            
            # Calculate composite score
            score = self._calculate_score(
                hours_to_expiry=hours_to_expiry,
                momentum_data=momentum_data,
                current_prob=tracked_prob
            )
            
            # Calculate annualized return
            annualized_return = self._calculate_annualized_return(
                current_prob=tracked_prob,
                hours_to_expiry=hours_to_expiry
            )
            
            # Build opportunity object
            opportunity = {
                'market_id': market_id,
                'question': question,
                'current_prob': current_prob,
                'tracked_prob': tracked_prob,
                'tracking_yes': tracking_yes,
                'hours_to_expiry': hours_to_expiry,
                'end_date': end_date,
                'peak_prob': momentum_data['peak_prob'],
                'peak_time': momentum_data['peak_time'],
                'pullback_pct': momentum_data['pullback_pct'],
                'momentum_strength': momentum_data['momentum_strength'],
                'move_24h': momentum_data['move_24h'],
                'recent_volatility': momentum_data['recent_volatility'],
                'score': score,
                'annualized_return': annualized_return,
                'url': f"https://polymarket.com/event/{market.get('slug', market_id)}"
            }
            
            opportunities.append(opportunity)
        
        # Sort by score descending
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        return opportunities
    
    def _extract_probability(self, market: Dict) -> Optional[float]:
        """
        Extract current probability from market data.
        
        Args:
            market: Market dictionary
            
        Returns:
            Probability as float (0-1) or None if not available
        """
        # Try different field names
        prob = market.get('outcomePrices') or market.get('outcome_prices')
        
        if isinstance(prob, list) and len(prob) >= 2:
            # Usually [YES_price, NO_price]
            return float(prob[0])
        elif isinstance(prob, str):
            try:
                return float(prob)
            except ValueError:
                pass
        elif isinstance(prob, (int, float)):
            return float(prob)
        
        # Try other fields
        if 'price' in market:
            return float(market['price'])
        
        return None
    
    def _analyze_momentum(
        self,
        current_prob: float,
        price_history: List[Dict],
        now: datetime,
        tracking_yes: bool
    ) -> Optional[Dict]:
        """
        Analyze momentum and pullback from price history.
        
        Args:
            current_prob: Current probability (already on correct side, 0-1)
            price_history: List of price points with timestamp and price
            now: Current datetime
            tracking_yes: Whether we're tracking YES side
            
        Returns:
            Dict with momentum metrics or None if insufficient data
        """
        if not price_history or len(price_history) < 2:
            # No history - use heuristic
            return self._heuristic_momentum(current_prob)
        
        # Filter to last 24 hours and convert to tracked side
        cutoff_time = now - timedelta(hours=self.MOMENTUM_LOOKBACK_HOURS)
        recent_prices = []
        
        for point in price_history:
            timestamp = point.get('timestamp')
            price = point.get('price')
            
            if timestamp and price is not None:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                
                if timestamp >= cutoff_time:
                    # Convert to tracked side
                    tracked_price = float(price) if tracking_yes else (1 - float(price))
                    recent_prices.append({
                        'timestamp': timestamp,
                        'price': tracked_price
                    })
        
        if len(recent_prices) < 2:
            return self._heuristic_momentum(current_prob)
        
        # Sort by timestamp
        recent_prices.sort(key=lambda x: x['timestamp'])
        
        # Find peak probability
        peak_prob = max(p['price'] for p in recent_prices)
        peak_price_point = max(recent_prices, key=lambda x: x['price'])
        peak_time = peak_price_point['timestamp']
        
        # Calculate pullback
        pullback_pct = (peak_prob - current_prob) / peak_prob if peak_prob > 0 else 0
        
        # Calculate 24h move (from earliest to peak)
        earliest_price = recent_prices[0]['price']
        move_24h = peak_prob - earliest_price
        
        # Momentum strength: combination of move size and recency
        hours_since_peak = (now - peak_time).total_seconds() / 3600
        recency_weight = math.exp(-hours_since_peak / self.RECENCY_DECAY_HOURS)
        
        # Momentum strength score (0-1)
        if move_24h >= self.EXTREME_MOVE_THRESHOLD:
            move_score = 1.0
        elif move_24h >= self.STRONG_MOVE_THRESHOLD:
            move_score = 0.5 + (move_24h - self.STRONG_MOVE_THRESHOLD) / (self.EXTREME_MOVE_THRESHOLD - self.STRONG_MOVE_THRESHOLD) * 0.5
        else:
            move_score = move_24h / self.STRONG_MOVE_THRESHOLD * 0.5
        
        momentum_strength = move_score * recency_weight
        
        # Calculate recent volatility (std dev of prices)
        prices = [p['price'] for p in recent_prices]
        mean_price = sum(prices) / len(prices)
        variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
        volatility = math.sqrt(variance)
        
        return {
            'peak_prob': peak_prob,
            'peak_time': peak_time,
            'pullback_pct': pullback_pct,
            'momentum_strength': momentum_strength,
            'move_24h': move_24h,
            'recent_volatility': volatility
        }
    
    def _heuristic_momentum(self, current_prob: float) -> Optional[Dict]:
        """
        Use heuristic when price history is unavailable.
        Assumes market at extreme probability had momentum to get there.
        
        Args:
            current_prob: Current probability
            
        Returns:
            Heuristic momentum data
        """
        # Estimate: if at 80%, assume it peaked at 85% (5% pullback)
        # if at 90%, assume peaked at 92% (2% pullback)
        # This is conservative - real opportunities will have better data
        
        if current_prob >= 0.90:
            estimated_peak = min(0.95, current_prob + 0.02)
        elif current_prob >= 0.80:
            estimated_peak = min(0.90, current_prob + 0.05)
        elif current_prob >= 0.75:
            estimated_peak = min(0.85, current_prob + 0.08)
        else:
            return None  # Don't create heuristic for lower probabilities
        
        pullback_pct = (estimated_peak - current_prob) / estimated_peak
        
        # Conservative momentum score
        momentum_strength = 0.3  # Low confidence without real data
        
        return {
            'peak_prob': estimated_peak,
            'peak_time': datetime.now(timezone.utc) - timedelta(hours=2),  # Assume recent
            'pullback_pct': pullback_pct,
            'momentum_strength': momentum_strength,
            'move_24h': 0.20,  # Assume moderate move
            'recent_volatility': 0.05
        }
    
    def _calculate_score(
        self,
        hours_to_expiry: float,
        momentum_data: Dict,
        current_prob: float
    ) -> float:
        """
        Calculate composite opportunity score.
        
        Args:
            hours_to_expiry: Hours until market expires
            momentum_data: Momentum analysis results
            current_prob: Current probability (tracked side)
            
        Returns:
            Composite score (0-100)
        """
        # 1. Expiration urgency score (0-1)
        # Exponential curve: closer to expiry = higher score
        # At 72h: ~0, At 24h: ~0.5, At 6h: ~0.9, At 1h: ~1.0
        exp_score = 1 - math.exp(-3 * (self.MAX_EXPIRATION_HOURS - hours_to_expiry) / self.MAX_EXPIRATION_HOURS)
        
        # 2. Momentum strength score (0-1) - already calculated
        momentum_score = momentum_data['momentum_strength']
        
        # 3. Pullback quality score (0-1)
        # Optimal at OPTIMAL_PULLBACK_CENTER, decreases on either side
        pullback_pct = momentum_data['pullback_pct']
        if pullback_pct < self.OPTIMAL_PULLBACK_MIN:
            pullback_score = 0
        elif pullback_pct > self.OPTIMAL_PULLBACK_MAX:
            # Too much pullback - might be trend reversal
            pullback_score = max(0, 1 - (pullback_pct - self.OPTIMAL_PULLBACK_MAX) / 0.2)
        else:
            # Score peaks at optimal center
            distance_from_optimal = abs(pullback_pct - self.OPTIMAL_PULLBACK_CENTER)
            pullback_score = 1 - (distance_from_optimal / (self.OPTIMAL_PULLBACK_CENTER - self.OPTIMAL_PULLBACK_MIN))
            pullback_score = max(0, min(1, pullback_score))
        
        # 4. Probability extremity score (0-1)
        # Higher score for more extreme probabilities
        if current_prob >= 0.95:
            extremity_score = 1.0
        elif current_prob >= 0.90:
            extremity_score = 0.8
        elif current_prob >= 0.85:
            extremity_score = 0.6
        elif current_prob >= 0.80:
            extremity_score = 0.4
        else:
            extremity_score = 0.2
        
        # Weighted composite score
        composite = (
            self.EXPIRATION_WEIGHT * exp_score +
            self.MOMENTUM_WEIGHT * momentum_score +
            self.PULLBACK_WEIGHT * pullback_score +
            self.EXTREMITY_WEIGHT * extremity_score
        )
        
        # Scale to 0-100
        return composite * 100
    
    def _calculate_annualized_return(
        self,
        current_prob: float,
        hours_to_expiry: float
    ) -> float:
        """
        Calculate annualized return percentage.
        
        Assumes position goes to 100% (market resolves in predicted direction).
        
        Args:
            current_prob: Current probability (0-1)
            hours_to_expiry: Hours until expiration
            
        Returns:
            Annualized return as percentage
        """
        if current_prob >= 0.99 or hours_to_expiry <= 0:
            return 0
        
        # Cost to enter: current_prob (e.g., 0.85 costs $0.85)
        # Payout if correct: $1.00
        # Profit: 1.00 - current_prob
        profit_pct = (1.0 - current_prob) / current_prob
        
        # Annualize based on time to expiry
        days_to_expiry = hours_to_expiry / 24
        annualized = profit_pct * (365 / days_to_expiry)
        
        return annualized * 100  # Return as percentage
