"""
End-to-end test for momentum hunter with all 8 strategies.
This tests the actual scan_pullback_markets function.
"""

import sys
import logging
from datetime import datetime

# Import the function
from app import scan_pullback_markets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_scan_pullback_markets():
    """Test the complete scan_pullback_markets function with all strategies."""
    
    print("\n" + "="*70)
    print("MOMENTUM HUNTER END-TO-END TEST")
    print("="*70)
    print("\nTesting scan_pullback_markets with all 8 strategies...")
    print("This will fetch from:")
    print("  1. Liquidity-sorted markets")
    print("  2. Default-sorted markets")
    print("  3. Volume-sorted with offsets")
    print("  4. Hot markets")
    print("  5. Breaking markets")
    print("  6. Event markets")
    print("  7. Newest markets")
    print("  8. Category-specific (10 categories)")
    print("\n" + "-"*70)
    
    # Run scan with relaxed filters to get results
    try:
        start_time = datetime.now()
        
        opportunities = scan_pullback_markets(
            max_expiry_hours=720,      # 30 days
            min_extremity=0.20,        # >=70% or <=30%
            limit=500,                 # Process more markets
            debug_mode=True,
            momentum_window_hours=168, # 7 days
            min_momentum=0.05,         # Lower threshold
            min_volume=100_000,        # Lower volume requirement
            min_distance=0.01          # 1% from extreme
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "-"*70)
        print("RESULTS:")
        print("-"*70)
        print(f"⏱️  Scan Duration: {duration:.2f} seconds")
        print(f"📊 Opportunities Found: {len(opportunities)}")
        
        if opportunities:
            print("\nTop 5 Opportunities:")
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"\n{i}. {opp['question'][:60]}")
                print(f"   Score: {opp['score']:.2f} | Grade: {opp.get('grade', 'N/A')}")
                print(f"   Prob: {opp['current_prob']:.1%} | Direction: {opp['direction']}")
                print(f"   Momentum: {opp.get('momentum', 0):.1%} | Charm: {opp.get('charm', 0):.2f}")
                print(f"   Expires: {opp['hours_to_expiry']:.1f}h | Volume: ${opp['volume_24h']:,.0f}")
        else:
            print("\n⚠️  No opportunities found with current filters.")
            print("   This could be expected if market conditions don't match criteria.")
        
        print("\n" + "="*70)
        print("✅ TEST PASSED - Function executed successfully!")
        print("="*70 + "\n")
        
        return True
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ TEST FAILED")
        print("="*70)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*70 + "\n")
        return False


if __name__ == "__main__":
    success = test_scan_pullback_markets()
    sys.exit(0 if success else 1)
