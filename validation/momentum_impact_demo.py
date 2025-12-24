"""
Demonstration of momentum alignment impact after fine-tuning.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import calculate_opportunity_score


print("=" * 80)
print("MOMENTUM ALIGNMENT IMPACT - AFTER FINE-TUNING")
print("=" * 80)

base = {
    'current_prob': 0.965,
    'momentum': 0.30,
    'hours_to_expiry': 8.5 * 24,
    'volume': 1_000_000,
    'best_bid': 0.96,
    'best_ask': 0.97,
    'direction': 'YES',
    'annualized_yield': 3.0,
    'charm': 6.0
}

scenarios = [
    ('Both Aligned', 0.05, 0.10),
    ('1d Aligned Only', 0.05, -0.02),
    ('7d Aligned Only', -0.02, 0.10),
    ('Both Misaligned', -0.05, -0.10)
]

print(f"\n{'Scenario':<20} {'Score':<10} {'Momentum':<12} {'Grade':<8} {'vs Aligned'}")
print("-" * 80)

results = []
for name, d1, d7 in scenarios:
    params = base.copy()
    params.update({'one_day_change': d1, 'one_week_change': d7})
    result = calculate_opportunity_score(**params)
    results.append((
        name,
        result['total_score'],
        result['components']['momentum'],
        result['grade']
    ))

baseline = results[0][1]
for name, score, mom, grade in results:
    diff = score - baseline
    diff_str = f"{diff:+.1f}" if diff != 0 else "---"
    print(f"{name:<20} {score:>6.1f}     {mom:>6.1f}      {grade:<8} {diff_str}")

print(f"\n✅ Improvement Summary:")
print(f"   Counter-trend penalty: {results[0][1] - results[3][1]:.1f} points")
print(f"   (Previous version: only 1.8 points)")
print(f"   Improvement: {((results[0][1] - results[3][1]) / 1.8 - 1) * 100:.0f}% stronger impact!")

print("\n💡 Practical Interpretation:")
print(f"   • Both Aligned ({results[0][1]:.1f}): {results[0][3]} grade - STRONG BUY signal")
print(f"   • Mixed Signals ({results[1][1]:.1f}/{results[2][1]:.1f}): {results[1][3]} grade - GOOD but watch momentum")
print(f"   • Counter-Trend ({results[3][1]:.1f}): {results[3][3]} grade - CAUTION, investigate reversal")

print("\n" + "=" * 80)
