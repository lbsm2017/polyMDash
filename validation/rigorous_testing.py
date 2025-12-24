"""
Rigorous scenario testing to identify scoring issues.
Tests edge cases and realistic scenarios to find non-sensible behavior.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import calculate_opportunity_score


def test_scenario(name, params, expected_behavior):
    """Test a scenario and check if it makes sense."""
    result = calculate_opportunity_score(**params)
    score = result['total_score']
    
    print(f"\n{'='*80}")
    print(f"{name}")
    print(f"{'='*80}")
    print(f"Prob: {params['current_prob']:.1%} | Distance: {result['distance_to_target']*100:.1f}% | Days: {result['days_to_expiry']:.1f}")
    print(f"Volume: ${params['volume']:,} | Spread: {((params['best_ask']-params['best_bid'])/params['current_prob']*100):.2f}%")
    print(f"Momentum: {params['momentum']:.2f} | APY: {params['annualized_yield']:.1f}% | Charm: {params['charm']:.1f}")
    print(f"\nSCORE: {score:.1f}/100 | Grade: {result['grade']} | Sweet Spot: {result['in_sweet_spot']}")
    
    print(f"\nComponents:")
    for comp, val in result['components'].items():
        print(f"  {comp:20s}: {val:6.2f}")
    
    print(f"\nExpected: {expected_behavior}")
    
    return result


def main():
    print("\n" + "="*80)
    print("RIGOROUS SCENARIO TESTING - Identifying Scoring Issues")
    print("="*80)
    
    issues = []
    
    # Test 1: Compare similar markets with one key difference
    print("\n\n" + "="*80)
    print("TEST GROUP 1: DISTANCE SENSITIVITY")
    print("="*80)
    
    base = {
        'momentum': 0.30,
        'hours_to_expiry': 8 * 24,
        'volume': 1_000_000,
        'best_bid': 0.96,
        'best_ask': 0.97,
        'direction': 'YES',
        'one_day_change': 0.05,
        'one_week_change': 0.10,
        'annualized_yield': 3.0,
        'charm': 6.0
    }
    
    distances = [
        (0.995, "0.5% - Too close"),
        (0.98, "2% - Sweet spot edge"),
        (0.965, "3.5% - Perfect sweet spot"),
        (0.95, "5% - Sweet spot edge"),
        (0.92, "8% - Outside sweet spot"),
        (0.85, "15% - Far from extreme"),
        (0.70, "30% - Very far")
    ]
    
    distance_scores = []
    for prob, desc in distances:
        params = base.copy()
        params['current_prob'] = prob
        result = test_scenario(f"Distance: {desc}", params, f"Should score based on {desc}")
        distance_scores.append((prob, result['total_score'], result['components']['distance_time_fit']))
    
    print("\n\nDistance Progression Analysis:")
    print(f"{'Distance':<15} {'Total Score':<15} {'Dist-Time Fit':<15}")
    print("-" * 45)
    for prob, total, dist_fit in distance_scores:
        dist_pct = (1.0 - prob) * 100
        print(f"{dist_pct:6.1f}%        {total:6.1f}         {dist_fit:6.1f}")
    
    # Check if progression makes sense
    # Sweet spot (2-5%) should score highest
    sweet_spot_scores = [s for p, s, _ in distance_scores if 0.95 <= p <= 0.98]
    outside_scores = [s for p, s, _ in distance_scores if p < 0.92 or p > 0.99]
    
    if sweet_spot_scores and outside_scores:
        avg_sweet = sum(sweet_spot_scores) / len(sweet_spot_scores)
        avg_outside = sum(outside_scores) / len(outside_scores)
        print(f"\nSweet spot avg: {avg_sweet:.1f} | Outside avg: {avg_outside:.1f}")
        if avg_sweet <= avg_outside:
            issues.append("❌ Sweet spot not scoring higher than outside range!")
    
    # Test 2: TIME SENSITIVITY
    print("\n\n" + "="*80)
    print("TEST GROUP 2: TIME SENSITIVITY")
    print("="*80)
    
    time_tests = [
        (0.5 * 24, "12 hours - Very short"),
        (3 * 24, "3 days - Short"),
        (7 * 24, "7 days - Sweet spot edge"),
        (8.5 * 24, "8.5 days - Perfect sweet spot"),
        (10 * 24, "10 days - Sweet spot edge"),
        (15 * 24, "15 days - Medium term"),
        (30 * 24, "30 days - Long term"),
        (60 * 24, "60 days - Very long")
    ]
    
    time_scores = []
    for hours, desc in time_tests:
        params = base.copy()
        params['current_prob'] = 0.965  # Keep at sweet spot distance
        params['hours_to_expiry'] = hours
        result = test_scenario(f"Time: {desc}", params, f"Should score based on {desc}")
        time_scores.append((hours/24, result['total_score'], result['components']['distance_time_fit']))
    
    print("\n\nTime Progression Analysis:")
    print(f"{'Days':<15} {'Total Score':<15} {'Dist-Time Fit':<15}")
    print("-" * 45)
    for days, total, dist_fit in time_scores:
        print(f"{days:6.1f}         {total:6.1f}         {dist_fit:6.1f}")
    
    # Test 3: VOLUME IMPACT
    print("\n\n" + "="*80)
    print("TEST GROUP 3: VOLUME IMPACT")
    print("="*80)
    
    volume_tests = [
        (0, "Zero volume - Untradeable"),
        (10_000, "$10k - Micro liquidity"),
        (100_000, "$100k - Low liquidity"),
        (500_000, "$500k - Target threshold"),
        (1_000_000, "$1M - Good liquidity"),
        (5_000_000, "$5M - High liquidity"),
        (20_000_000, "$20M - Massive liquidity")
    ]
    
    volume_scores = []
    for vol, desc in volume_tests:
        params = base.copy()
        params['current_prob'] = 0.965
        params['hours_to_expiry'] = 8.5 * 24
        params['volume'] = vol
        result = test_scenario(f"Volume: {desc}", params, f"Should reflect {desc}")
        volume_scores.append((vol, result['total_score'], result['components']['volume']))
    
    print("\n\nVolume Impact Analysis:")
    print(f"{'Volume':<20} {'Total Score':<15} {'Volume Component':<15} {'Delta':<10}")
    print("-" * 60)
    prev_total = None
    for vol, total, vol_comp in volume_scores:
        delta_str = f"+{total - prev_total:.1f}" if prev_total else "---"
        print(f"${vol:>18,}   {total:6.1f}         {vol_comp:6.1f}            {delta_str}")
        prev_total = total
    
    # Check: Zero volume should significantly hurt score
    zero_vol_score = volume_scores[0][1]
    high_vol_score = volume_scores[-1][1]
    vol_diff = high_vol_score - zero_vol_score
    
    if vol_diff < 10:
        issues.append(f"❌ Volume impact too low! Zero vol vs $20M only differs by {vol_diff:.1f} points")
    elif vol_diff > 40:
        issues.append(f"⚠️  Volume impact very high! Zero vol vs $20M differs by {vol_diff:.1f} points (may be too much)")
    else:
        print(f"\n✅ Volume impact reasonable: {vol_diff:.1f} point difference")
    
    # Test 4: APY SCALING
    print("\n\n" + "="*80)
    print("TEST GROUP 4: APY SCALING")
    print("="*80)
    
    apy_tests = [
        (0.5, "50% APY - Low"),
        (1.5, "150% APY - Moderate"),
        (3.0, "300% APY - Good"),
        (5.0, "500% APY - High"),
        (10.0, "1000% APY - Very high"),
        (50.0, "5000% APY - Extreme"),
        (100.0, "10000% APY - Crazy high")
    ]
    
    apy_scores = []
    for apy, desc in apy_tests:
        params = base.copy()
        params['current_prob'] = 0.965
        params['hours_to_expiry'] = 8.5 * 24
        params['annualized_yield'] = apy
        result = test_scenario(f"APY: {desc}", params, f"Should reflect {desc}")
        apy_scores.append((apy, result['total_score'], result['components']['apy']))
    
    print("\n\nAPY Scaling Analysis:")
    print(f"{'APY %':<15} {'Total Score':<15} {'APY Component':<15}")
    print("-" * 45)
    for apy, total, apy_comp in apy_scores:
        print(f"{apy*100:6.0f}%        {total:6.1f}         {apy_comp:6.1f}")
    
    # Test 5: MOMENTUM ALIGNMENT
    print("\n\n" + "="*80)
    print("TEST GROUP 5: MOMENTUM ALIGNMENT")
    print("="*80)
    
    momentum_tests = [
        (0.30, 0.05, 0.10, "Both aligned"),
        (0.30, -0.05, 0.10, "1d misaligned, 7d aligned"),
        (0.30, 0.05, -0.10, "1d aligned, 7d misaligned"),
        (0.30, -0.05, -0.10, "Both misaligned"),
    ]
    
    momentum_scores = []
    for mom, d1, d7, desc in momentum_tests:
        params = base.copy()
        params['current_prob'] = 0.965
        params['hours_to_expiry'] = 8.5 * 24
        params['momentum'] = mom
        params['one_day_change'] = d1
        params['one_week_change'] = d7
        result = test_scenario(f"Momentum: {desc}", params, f"Should reflect {desc}")
        momentum_scores.append((desc, result['total_score'], result['components']['momentum']))
    
    print("\n\nMomentum Alignment Analysis:")
    print(f"{'Alignment':<30} {'Total Score':<15} {'Momentum Comp':<15}")
    print("-" * 60)
    for desc, total, mom_comp in momentum_scores:
        print(f"{desc:<30} {total:6.1f}         {mom_comp:6.1f}")
    
    # Both aligned should score highest
    both_aligned = momentum_scores[0][1]
    both_misaligned = momentum_scores[3][1]
    momentum_diff = both_aligned - both_misaligned
    
    if momentum_diff < 3:
        issues.append(f"Momentum alignment impact too low! Only {momentum_diff:.1f} points difference")
    else:
        print(f"\nMomentum alignment impact: {momentum_diff:.1f} points")
    
    # Test 6: SPREAD QUALITY
    print("\n\n" + "="*80)
    print("TEST GROUP 6: SPREAD QUALITY")
    print("="*80)
    
    spread_tests = [
        (0.9648, 0.9652, "0.04% - Super tight"),
        (0.963, 0.967, "0.4% - Tight"),
        (0.96, 0.97, "1% - Reasonable"),
        (0.95, 0.98, "3% - Wide"),
        (0.94, 0.99, "5% - Very wide"),
        (0.90, 1.00, "10% - Extreme")
    ]
    
    spread_scores = []
    for bid, ask, desc in spread_tests:
        params = base.copy()
        params['current_prob'] = 0.965
        params['hours_to_expiry'] = 8.5 * 24
        params['best_bid'] = bid
        params['best_ask'] = ask
        spread_pct = (ask - bid) / 0.965 * 100
        result = test_scenario(f"Spread: {desc}", params, f"Should reflect {desc}")
        spread_scores.append((spread_pct, result['total_score'], result['components']['spread']))
    
    print("\n\nSpread Impact Analysis:")
    print(f"{'Spread %':<15} {'Total Score':<15} {'Spread Comp':<15}")
    print("-" * 45)
    for spread, total, spread_comp in spread_scores:
        print(f"{spread:6.2f}%       {total:6.1f}         {spread_comp:6.1f}")
    
    # FINAL SUMMARY
    print("\n\n" + "="*80)
    print("ISSUES IDENTIFIED")
    print("="*80)
    
    if issues:
        for issue in issues:
            print(issue)
    else:
        print("No major issues identified - scoring appears sensible")
    
    # RECOMMENDATIONS
    print("\n\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    print("""
Based on rigorous testing, here are recommendations:

1. DISTANCE-TIME FIT (35% weight)
   - Current behavior: Gaussian curves centered at 3.5%, 8.5 days
   - Check: Does the peak happen at the right place?
   - Check: Is the falloff too steep or too gradual?

2. VOLUME (15% weight)
   - Current: Sigmoid centered at $500k
   - Check: Zero volume impact - should it hurt more?
   - Check: High volume ($5M+) - diminishing returns working?

3. APY (25% weight)
   - Current: Polynomial scaling with log for extremes
   - Check: Is extreme APY (>1000%) scaling sensibly?

4. MOMENTUM (10% weight)
   - Current: Multipliers 1.25x, 1.1x, 0.65x
   - Check: Is misalignment penalty strong enough?

5. SPREAD (10% weight)
   - Current: Inverse polynomial
   - Check: Wide spreads (>5%) - harsh enough penalty?

6. CHARM (5% weight)
   - Current: Polynomial scaling
   - Check: Extreme charm (>20) - logarithmic working?
    """)


if __name__ == "__main__":
    main()
