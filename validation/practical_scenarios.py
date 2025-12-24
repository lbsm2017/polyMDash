"""
Practical scenario validation examples.

This script demonstrates how the scoring system evaluates
real-world market situations with practical interpretations.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import calculate_opportunity_score


def print_scenario(title, description, result, params):
    """Print formatted scenario analysis."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")
    print(f"{description}")
    print(f"\nMarket Setup:")
    print(f"  Probability: {params['current_prob']:.1%} ({params['direction']})")
    print(f"  Distance to extreme: {result['distance_to_target']*100:.2f}%")
    print(f"  Days to expiry: {result['days_to_expiry']:.1f}")
    print(f"  Volume: ${params['volume']:,.0f}")
    print(f"  Bid/Ask: {params['best_bid']:.3f} / {params['best_ask']:.3f}")
    print(f"  APY: {params['annualized_yield']:.1f}%")
    
    print(f"\n📊 SCORE: {result['total_score']:.1f}/100 | Grade: {result['grade']}")
    print(f"   Sweet Spot: {'✅ YES' if result['in_sweet_spot'] else '❌ NO'}")
    
    print(f"\n   Component Scores:")
    for comp, score in result['components'].items():
        bars = '█' * int(score/5) + '░' * (20 - int(score/5))
        print(f"   {comp:20s} [{bars}] {score:5.1f}")
    

def main():
    print("\n" + "="*80)
    print(" "*20 + "PRACTICAL SCENARIO VALIDATION")
    print("="*80)
    print("\nReal-world examples showing how the scoring system evaluates")
    print("different market opportunities with practical interpretations.\n")
    
    # Scenario 1: The Ideal Trade
    params1 = {
        'current_prob': 0.965,
        'momentum': 0.40,
        'hours_to_expiry': 8.5 * 24,
        'volume': 2_000_000,
        'best_bid': 0.963,
        'best_ask': 0.967,
        'direction': 'YES',
        'one_day_change': 0.06,
        'one_week_change': 0.11,
        'annualized_yield': 4.5,
        'charm': 9.0
    }
    result1 = calculate_opportunity_score(**params1)
    
    print_scenario(
        "🎯 Scenario 1: The Ideal Trade Setup",
        """
You find a market at 96.5% probability with 8.5 days to expiry.
- Perfect sweet spot positioning (3.5% from 100%, 8.5 days)
- High liquidity ($2M volume)
- Tight spread (0.4%)
- Strong momentum aligned with direction
- Healthy charm (9 pp/day acceleration)
- Good APY (450%)

💡 INTERPRETATION: This is exactly what the system looks for.
   Perfect distance-time fit + strong fundamentals = Top grade.
   This is a STRONG BUY signal.
        """,
        result1,
        params1
    )
    
    # Scenario 2: Too Close for Comfort
    params2 = {
        'current_prob': 0.993,
        'momentum': 0.50,
        'hours_to_expiry': 5 * 24,
        'volume': 5_000_000,
        'best_bid': 0.992,
        'best_ask': 0.994,
        'direction': 'YES',
        'one_day_change': 0.08,
        'one_week_change': 0.15,
        'annualized_yield': 1.5,
        'charm': 25.0
    }
    result2 = calculate_opportunity_score(**params2)
    
    print_scenario(
        "⚠️  Scenario 2: Too Close for Comfort",
        """
You find a market at 99.3% probability with 5 days to expiry.
- Only 0.7% from resolution (very close!)
- Massive liquidity ($5M volume)
- Extremely tight spread
- Very strong momentum and charm
- But limited upside potential

💡 INTERPRETATION: Despite perfect fundamentals, proximity to
   extreme severely limits profit potential. The system correctly
   penalizes this - it's not worth the risk/reward.
   This is a PASS.
        """,
        result2,
        params2
    )
    
    # Scenario 3: The Long Shot
    params3 = {
        'current_prob': 0.80,
        'momentum': 0.25,
        'hours_to_expiry': 25 * 24,
        'volume': 1_200_000,
        'best_bid': 0.79,
        'best_ask': 0.81,
        'direction': 'YES',
        'one_day_change': 0.02,
        'one_week_change': 0.07,
        'annualized_yield': 3.0,
        'charm': 3.0
    }
    result3 = calculate_opportunity_score(**params3)
    
    print_scenario(
        "📉 Scenario 3: The Long Shot",
        """
You find a market at 80% probability with 25 days to expiry.
- 20% from extreme (too far)
- Long time frame (outside sweet spot)
- Good liquidity and spread
- Moderate fundamentals

💡 INTERPRETATION: Too far from the extreme and too long to expiry.
   While fundamentals are decent, this isn't the optimal setup.
   The system wants 2-5% distance in 7-10 days, not this.
   This is a MAYBE - consider but not priority.
        """,
        result3,
        params3
    )
    
    # Scenario 4: Low Liquidity Gem
    params4 = {
        'current_prob': 0.97,
        'momentum': 0.35,
        'hours_to_expiry': 9 * 24,
        'volume': 50_000,
        'best_bid': 0.96,
        'best_ask': 0.98,
        'direction': 'YES',
        'one_day_change': 0.05,
        'one_week_change': 0.10,
        'annualized_yield': 3.8,
        'charm': 7.5
    }
    result4 = calculate_opportunity_score(**params4)
    
    print_scenario(
        "💎 Scenario 4: Low Liquidity Gem",
        """
You find a market at 97% probability with 9 days to expiry.
- Perfect sweet spot positioning (3%, 9 days)
- Low liquidity ($50k volume) - might be hard to enter/exit
- Moderate spread (2%)
- Good fundamentals otherwise

💡 INTERPRETATION: Great positioning but liquidity concerns.
   The system still scores this well because the opportunity
   quality is high - but YOU need to decide if you can trade
   the size you want. For small trades, this is good.
   This is a CONDITIONAL BUY - size dependent.
        """,
        result4,
        params4
    )
    
    # Scenario 5: The Sprint
    params5 = {
        'current_prob': 0.96,
        'momentum': 0.55,
        'hours_to_expiry': 1.5 * 24,
        'volume': 800_000,
        'best_bid': 0.958,
        'best_ask': 0.962,
        'direction': 'YES',
        'one_day_change': 0.10,
        'one_week_change': 0.18,
        'annualized_yield': 25.0,
        'charm': 30.0
    }
    result5 = calculate_opportunity_score(**params5)
    
    print_scenario(
        "⚡ Scenario 5: The Sprint",
        """
You find a market at 96% probability expiring in 1.5 days.
- Good distance (4%)
- Very short timeframe (not sweet spot)
- Extremely high momentum and charm
- Very high APY (2500%) due to short time
- Good liquidity

💡 INTERPRETATION: This is a fast-moving momentum play, not
   the sweet spot trade. The system penalizes short expiry
   because it prefers 7-10 day setups with less urgency.
   If you like short-term scalps, this could work, but it's
   not what the strategy optimizes for.
   This is a TACTICAL OPPORTUNITY - different strategy.
        """,
        result5,
        params5
    )
    
    # Scenario 6: Counter-Trend Setup
    params6 = {
        'current_prob': 0.965,
        'momentum': 0.20,
        'hours_to_expiry': 8 * 24,
        'volume': 1_500_000,
        'best_bid': 0.96,
        'best_ask': 0.97,
        'direction': 'YES',
        'one_day_change': -0.03,  # Negative!
        'one_week_change': -0.02,  # Negative!
        'annualized_yield': 3.5,
        'charm': 6.0
    }
    result6 = calculate_opportunity_score(**params6)
    
    print_scenario(
        "🔄 Scenario 6: Counter-Trend Setup",
        """
You find a market at 96.5% probability with 8 days to expiry.
- Perfect sweet spot positioning
- Good liquidity and spread
- BUT momentum is AGAINST the direction (both 1d/7d negative)
- Market has been declining despite high probability

💡 INTERPRETATION: Perfect positioning but momentum misalignment
   is a red flag. The market might be topping out or traders
   are taking profits. The system reduces the momentum component
   score significantly (0.65x multiplier vs 1.25x for alignment).
   This is a CAUTION - investigate why momentum is opposite.
        """,
        result6,
        params6
    )
    
    # Summary
    print("\n" + "="*80)
    print(" "*25 + "KEY TAKEAWAYS")
    print("="*80)
    print("""
1. SWEET SPOT DOMINATES (35% weight)
   - 2-5% distance from extreme
   - 7-10 days to expiry
   - This is the #1 factor in scoring

2. LIQUIDITY IS SECONDARY (15% weight)
   - System measures opportunity quality, not just tradeability
   - Low liquidity gems can score well if positioned perfectly
   - YOU decide if you can trade the size

3. TIME MATTERS
   - Very short (<5d) or very long (>15d) = penalty
   - System optimizes for medium-term setups
   - Different strategies need different timeframes

4. MOMENTUM ALIGNMENT IMPORTANT
   - Both 1d/7d aligned: 1.25x boost
   - Neither aligned: 0.65x penalty
   - Counter-trend setups are flagged

5. PRACTICAL SCORES
   - 70-95: Strong buy - ideal setup
   - 60-75: Good buy - some compromises
   - 45-60: Maybe - conditional/tactical
   - <45: Pass - not optimal

6. CONTEXT MATTERS
   - Score is a guide, not absolute truth
   - Consider YOUR strategy, size, risk tolerance
   - System finds sweet spot trades, you decide execution
    """)
    
    print("="*80)
    print(" "*20 + "✅ VALIDATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
