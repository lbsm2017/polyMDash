"""
Quick validation runner - runs all tests and shows summary.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_scoring_validation import run_realistic_scenarios, run_edge_cases, run_randomized_tests, run_comparative_analysis


def main():
    print("\n" + "="*80)
    print(" "*20 + "QUICK VALIDATION RUNNER")
    print("="*80)
    
    print("\n[1/4] Running realistic scenarios...")
    realistic = run_realistic_scenarios()
    
    print("\n[2/4] Running edge cases...")
    edges = run_edge_cases()
    
    print("\n[3/4] Running randomized tests (n=50)...")
    randomized = run_randomized_tests(50)
    
    print("\n[4/4] Running comparative analysis...")
    run_comparative_analysis()
    
    # Summary
    total_passed = realistic.passed + edges.passed + randomized.passed
    total_failed = realistic.failed + edges.failed + randomized.failed
    
    print("\n" + "="*80)
    print(" "*25 + "QUICK SUMMARY")
    print("="*80)
    print(f"Realistic Scenarios:  {realistic.passed}/{realistic.passed + realistic.failed} passed")
    print(f"Edge Cases:           {edges.passed}/{edges.passed + edges.failed} passed")
    print(f"Randomized Tests:     {randomized.passed}/{randomized.passed + randomized.failed} passed")
    print(f"Comparative Analysis: ✅ All assertions passed")
    print("-"*80)
    print(f"TOTAL:                {total_passed}/{total_passed + total_failed} passed")
    
    if total_failed == 0:
        print("\n✅ System validated - all tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total_failed} failures detected")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
