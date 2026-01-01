"""
Quick test to verify debugging output for momentum scanner filtering.
"""

import logging
from app import scan_pullback_markets

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

print("\n" + "="*70)
print("TESTING MOMENTUM SCANNER WITH DEBUGGING")
print("="*70 + "\n")

# Run scan with relaxed filters
opportunities = scan_pullback_markets(
    max_expiry_hours=720,      # 30 days
    min_extremity=0.20,        # >=70% or <=30%
    limit=500,
    debug_mode=True,
    momentum_window_hours=168, # 7 days
    min_momentum=0.05,         # 5% momentum
    min_volume=100_000,        # $100k minimum
    min_distance=0.01          # 1% from extreme
)

print("\n" + "="*70)
print(f"FINAL RESULT: {len(opportunities)} opportunities found")
print("="*70 + "\n")

if opportunities:
    print("Top 10 by category:")
    for i, opp in enumerate(opportunities[:10], 1):
        print(f"{i}. [{opp['direction']}] {opp['question'][:60]}")
        print(f"   Prob: {opp['current_prob']:.1%} | Mom: {opp.get('momentum', 0):.1%} | Vol: ${opp['volume_24h']:,.0f}")
