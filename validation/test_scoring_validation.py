"""
Validation script for multi-modal scoring system.

Tests realistic scenarios, edge cases, and randomized inputs to ensure
the scoring function produces sensible, practical results.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import calculate_opportunity_score
import random
import math
from typing import Dict, List, Tuple


class ScoringValidator:
    """Validates scoring system behavior across various scenarios."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []
    
    def validate_scenario(self, name: str, params: Dict, expectations: Dict) -> bool:
        """
        Validate a single scenario.
        
        Args:
            name: Scenario name
            params: Parameters to pass to calculate_opportunity_score
            expectations: Dict with 'min_score', 'max_score', and optional component checks
        
        Returns:
            True if validation passed
        """
        try:
            result = calculate_opportunity_score(**params)
            score = result['total_score']
            components = result['components']
            
            # Check score range
            min_score = expectations.get('min_score', 0)
            max_score = expectations.get('max_score', 100)
            
            if not (min_score <= score <= max_score):
                self.failed += 1
                self.results.append({
                    'name': name,
                    'status': 'FAIL',
                    'reason': f"Score {score:.2f} outside expected range [{min_score}, {max_score}]",
                    'params': params,
                    'result': result
                })
                return False
            
            # Check component ranges if specified
            for comp_name, (comp_min, comp_max) in expectations.get('components', {}).items():
                comp_value = components.get(comp_name, 0)
                if not (comp_min <= comp_value <= comp_max):
                    self.warnings += 1
                    self.results.append({
                        'name': name,
                        'status': 'WARNING',
                        'reason': f"{comp_name} = {comp_value:.2f} outside [{comp_min}, {comp_max}]",
                        'params': params,
                        'result': result
                    })
            
            # Check sweet spot detection
            if 'in_sweet_spot' in expectations:
                expected_sweet = expectations['in_sweet_spot']
                actual_sweet = result.get('in_sweet_spot', False)
                if expected_sweet != actual_sweet:
                    self.warnings += 1
                    self.results.append({
                        'name': name,
                        'status': 'WARNING',
                        'reason': f"Sweet spot mismatch: expected {expected_sweet}, got {actual_sweet}",
                        'params': params,
                        'result': result
                    })
            
            self.passed += 1
            self.results.append({
                'name': name,
                'status': 'PASS',
                'score': score,
                'result': result
            })
            return True
            
        except Exception as e:
            self.failed += 1
            self.results.append({
                'name': name,
                'status': 'ERROR',
                'reason': str(e),
                'params': params
            })
            return False
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"⚠️  Warnings: {self.warnings}")
        print("="*80)
        
        # Print failures
        if self.failed > 0:
            print("\nFAILURES:")
            for r in self.results:
                if r['status'] in ['FAIL', 'ERROR']:
                    print(f"\n❌ {r['name']}")
                    print(f"   Reason: {r['reason']}")
                    if 'result' in r:
                        print(f"   Score: {r['result']['total_score']:.2f}")
        
        # Print warnings
        if self.warnings > 0:
            print("\nWARNINGS:")
            for r in self.results:
                if r['status'] == 'WARNING':
                    print(f"\n⚠️  {r['name']}")
                    print(f"   Reason: {r['reason']}")


def run_realistic_scenarios():
    """Test realistic market scenarios."""
    print("\n" + "="*80)
    print("REALISTIC SCENARIOS")
    print("="*80)
    
    validator = ScoringValidator()
    
    # Scenario 1: Perfect Sweet Spot
    print("\n1. Perfect Sweet Spot Market")
    print("   - 3.5% distance, 8 days, high volume, tight spread")
    validator.validate_scenario(
        "Perfect Sweet Spot",
        {
            'current_prob': 0.965,
            'momentum': 0.35,
            'hours_to_expiry': 8 * 24,
            'volume': 1_500_000,
            'best_bid': 0.96,
            'best_ask': 0.97,
            'direction': 'YES',
            'one_day_change': 0.05,
            'one_week_change': 0.10,
            'annualized_yield': 4.0,
            'charm': 8.0
        },
        {
            'min_score': 70,
            'max_score': 95,
            'in_sweet_spot': True,
            'components': {
                'distance_time_fit': (80, 100),
                'apy': (60, 90)
            }
        }
    )
    
    # Scenario 2: Good Market Outside Sweet Spot
    print("\n2. Good Market - Slightly Outside Sweet Spot")
    print("   - 8% distance, 12 days, good fundamentals")
    validator.validate_scenario(
        "Good Market Outside Sweet Spot",
        {
            'current_prob': 0.92,
            'momentum': 0.28,
            'hours_to_expiry': 12 * 24,
            'volume': 800_000,
            'best_bid': 0.91,
            'best_ask': 0.93,
            'direction': 'YES',
            'one_day_change': 0.03,
            'one_week_change': 0.08,
            'annualized_yield': 2.5,
            'charm': 5.0
        },
        {
            'min_score': 40,
            'max_score': 65,
            'in_sweet_spot': False
        }
    )
    
    # Scenario 3: Low Liquidity Market
    print("\n3. Low Liquidity Market")
    print("   - Sweet spot distance/time but low volume")
    validator.validate_scenario(
        "Low Liquidity in Sweet Spot",
        {
            'current_prob': 0.97,
            'momentum': 0.30,
            'hours_to_expiry': 9 * 24,
            'volume': 75_000,  # Low volume
            'best_bid': 0.96,
            'best_ask': 0.98,  # Wide spread
            'direction': 'YES',
            'one_day_change': 0.04,
            'one_week_change': 0.09,
            'annualized_yield': 3.5,
            'charm': 7.0
        },
        {
            'min_score': 55,
            'max_score': 75,  # Sweet spot dominates despite low liquidity
            'in_sweet_spot': True,
            'components': {
                'volume': (0, 40),
                'spread': (0, 75),
                'distance_time_fit': (90, 100)
            }
        }
    )
    
    # Scenario 4: High APY, Longer Timeframe
    print("\n4. High APY Long-Term Market")
    print("   - 15% distance, 20 days, very high APY")
    validator.validate_scenario(
        "High APY Long-Term",
        {
            'current_prob': 0.85,
            'momentum': 0.20,
            'hours_to_expiry': 20 * 24,
            'volume': 2_000_000,
            'best_bid': 0.84,
            'best_ask': 0.86,
            'direction': 'YES',
            'one_day_change': 0.02,
            'one_week_change': 0.06,
            'annualized_yield': 8.0,  # 800% APY
            'charm': 3.0
        },
        {
            'min_score': 55,
            'max_score': 80,
            'components': {
                'apy': (80, 100),
                'volume': (60, 90)
            }
        }
    )
    
    # Scenario 5: Short-Term High Momentum
    print("\n5. Short-Term High Momentum")
    print("   - 4% distance, 3 days, strong momentum")
    validator.validate_scenario(
        "Short-Term Momentum Play",
        {
            'current_prob': 0.96,
            'momentum': 0.45,
            'hours_to_expiry': 3 * 24,
            'volume': 600_000,
            'best_bid': 0.955,
            'best_ask': 0.965,  # Tight spread
            'direction': 'YES',
            'one_day_change': 0.08,
            'one_week_change': 0.12,
            'annualized_yield': 12.0,  # High APY for short-term
            'charm': 15.0  # High acceleration
        },
        {
            'min_score': 45,
            'max_score': 65,  # Penalized for short expiry
            'in_sweet_spot': False,
            'components': {
                'momentum': (50, 100),
                'charm': (85, 100),
                'distance_time_fit': (0, 15)  # Very low due to 3 days
            }
        }
    )
    
    # Scenario 6: Misaligned Momentum
    print("\n6. Misaligned Momentum Signals")
    print("   - Good setup but conflicting momentum")
    validator.validate_scenario(
        "Misaligned Momentum",
        {
            'current_prob': 0.965,
            'momentum': 0.25,
            'hours_to_expiry': 8 * 24,
            'volume': 1_000_000,
            'best_bid': 0.96,
            'best_ask': 0.97,
            'direction': 'YES',
            'one_day_change': -0.02,  # Negative (misaligned)
            'one_week_change': -0.01,  # Negative (misaligned)
            'annualized_yield': 3.0,
            'charm': 6.0
        },
        {
            'min_score': 50,
            'max_score': 75,  # Lower than aligned momentum
            'components': {
                'momentum': (10, 30)  # Should be penalized
            }
        }
    )
    
    validator.print_summary()
    return validator


def run_edge_cases():
    """Test edge case scenarios."""
    print("\n" + "="*80)
    print("EDGE CASE SCENARIOS")
    print("="*80)
    
    validator = ScoringValidator()
    
    # Edge 1: Extremely close to resolution
    print("\n1. Extremely Close to Resolution")
    print("   - 0.5% distance, should get very low score")
    validator.validate_scenario(
        "0.5% from 100%",
        {
            'current_prob': 0.995,
            'momentum': 0.40,
            'hours_to_expiry': 5 * 24,
            'volume': 3_000_000,
            'best_bid': 0.99,
            'best_ask': 0.996,
            'direction': 'YES',
            'one_day_change': 0.05,
            'one_week_change': 0.10,
            'annualized_yield': 0.05,
            'charm': 20.0
        },
        {
            'min_score': 0,
            'max_score': 40,  # Should score low despite good fundamentals
            'components': {
                'distance_time_fit': (0, 25)
            }
        }
    )
    
    # Edge 2: Very far from extreme
    print("\n2. Very Far from Extreme")
    print("   - 30% distance (middle zone)")
    validator.validate_scenario(
        "30% from 100%",
        {
            'current_prob': 0.70,
            'momentum': 0.35,
            'hours_to_expiry': 8 * 24,
            'volume': 1_000_000,
            'best_bid': 0.69,
            'best_ask': 0.71,
            'direction': 'YES',
            'one_day_change': 0.05,
            'one_week_change': 0.10,
            'annualized_yield': 1.5,
            'charm': 8.0
        },
        {
            'min_score': 20,
            'max_score': 55,  # Should score lower, too far from extreme
            'components': {
                'distance_time_fit': (0, 40)
            }
        }
    )
    
    # Edge 3: Very short expiry
    print("\n3. Expiring in 6 Hours")
    print("   - Sweet spot distance but very short time")
    validator.validate_scenario(
        "6 Hours to Expiry",
        {
            'current_prob': 0.965,
            'momentum': 0.50,
            'hours_to_expiry': 6,
            'volume': 2_000_000,
            'best_bid': 0.963,
            'best_ask': 0.967,
            'direction': 'YES',
            'one_day_change': 0.10,
            'one_week_change': 0.15,
            'annualized_yield': 50.0,  # Very high APY for short time
            'charm': 40.0
        },
        {
            'min_score': 50,
            'max_score': 85,
            'in_sweet_spot': False
        }
    )
    
    # Edge 4: Very long expiry
    print("\n4. Expiring in 60 Days")
    print("   - Sweet spot distance but very long time")
    validator.validate_scenario(
        "60 Days to Expiry",
        {
            'current_prob': 0.965,
            'momentum': 0.15,
            'hours_to_expiry': 60 * 24,
            'volume': 5_000_000,
            'best_bid': 0.96,
            'best_ask': 0.97,
            'direction': 'YES',
            'one_day_change': 0.01,
            'one_week_change': 0.03,
            'annualized_yield': 0.6,
            'charm': 1.0
        },
        {
            'min_score': 30,
            'max_score': 65,
            'in_sweet_spot': False
        }
    )
    
    # Edge 5: Zero volume
    print("\n5. Zero Volume Market")
    validator.validate_scenario(
        "Zero Volume",
        {
            'current_prob': 0.965,
            'momentum': 0.30,
            'hours_to_expiry': 8 * 24,
            'volume': 0,
            'best_bid': 0.96,
            'best_ask': 0.97,
            'direction': 'YES',
            'one_day_change': 0.05,
            'one_week_change': 0.10,
            'annualized_yield': 3.0,
            'charm': 6.0
        },
        {
            'min_score': 50,
            'max_score': 70,  # Sweet spot dominates despite zero volume
            'in_sweet_spot': True,
            'components': {
                'volume': (0, 10),
                'distance_time_fit': (95, 100)
            }
        }
    )
    
    # Edge 6: Zero momentum
    print("\n6. Zero Momentum")
    validator.validate_scenario(
        "Zero Momentum",
        {
            'current_prob': 0.965,
            'momentum': 0.0,
            'hours_to_expiry': 8 * 24,
            'volume': 1_000_000,
            'best_bid': 0.96,
            'best_ask': 0.97,
            'direction': 'YES',
            'one_day_change': 0.0,
            'one_week_change': 0.0,
            'annualized_yield': 3.0,
            'charm': 0.0
        },
        {
            'min_score': 30,
            'max_score': 70,
            'components': {
                'momentum': (0, 10),
                'charm': (0, 10)
            }
        }
    )
    
    # Edge 7: Extreme APY
    print("\n7. Extreme APY (10000%)")
    validator.validate_scenario(
        "Extreme APY",
        {
            'current_prob': 0.50,
            'momentum': 0.60,
            'hours_to_expiry': 1,  # 1 hour
            'volume': 500_000,
            'best_bid': 0.49,
            'best_ask': 0.51,
            'direction': 'YES',
            'one_day_change': 0.20,
            'one_week_change': 0.25,
            'annualized_yield': 100.0,  # 10000% APY
            'charm': 100.0
        },
        {
            'min_score': 40,
            'max_score': 90,
            'components': {
                'apy': (85, 100)
            }
        }
    )
    
    # Edge 8: Wide spread
    print("\n8. Very Wide Spread (20%)")
    validator.validate_scenario(
        "Wide Spread",
        {
            'current_prob': 0.965,
            'momentum': 0.35,
            'hours_to_expiry': 8 * 24,
            'volume': 1_000_000,
            'best_bid': 0.90,
            'best_ask': 0.98,  # 8% spread (very wide)
            'direction': 'YES',
            'one_day_change': 0.05,
            'one_week_change': 0.10,
            'annualized_yield': 3.0,
            'charm': 6.0
        },
        {
            'min_score': 30,
            'max_score': 70,
            'components': {
                'spread': (0, 30)
            }
        }
    )
    
    validator.print_summary()
    return validator


def run_randomized_tests(n_tests: int = 100):
    """Run randomized tests to check for crashes and range violations."""
    print("\n" + "="*80)
    print(f"RANDOMIZED SCENARIOS (n={n_tests})")
    print("="*80)
    
    validator = ScoringValidator()
    
    for i in range(n_tests):
        # Generate random but plausible parameters
        prob = random.uniform(0.01, 0.99)
        direction = random.choice(['YES', 'NO'])
        
        # If YES, we want high prob (moving toward 100%)
        # If NO, we want low prob (moving toward 0%)
        if direction == 'YES':
            current_prob = random.uniform(0.60, 0.995)
        else:
            current_prob = random.uniform(0.005, 0.40)
        
        days = random.uniform(0.5, 90)
        
        params = {
            'current_prob': current_prob,
            'momentum': random.uniform(0, 0.8),
            'hours_to_expiry': days * 24,
            'volume': random.uniform(0, 10_000_000),
            'best_bid': max(0.001, current_prob - random.uniform(0, 0.10)),
            'best_ask': min(0.999, current_prob + random.uniform(0, 0.10)),
            'direction': direction,
            'one_day_change': random.uniform(-0.15, 0.15),
            'one_week_change': random.uniform(-0.25, 0.25),
            'annualized_yield': random.uniform(0, 50),
            'charm': random.uniform(0, 50)
        }
        
        validator.validate_scenario(
            f"Random Test {i+1}",
            params,
            {
                'min_score': 0,
                'max_score': 100
            }
        )
    
    validator.print_summary()
    return validator


def run_comparative_analysis():
    """Compare scores across similar scenarios to verify consistency."""
    print("\n" + "="*80)
    print("COMPARATIVE ANALYSIS")
    print("="*80)
    
    print("\nComparing similar markets with one variable changed:")
    
    base_params = {
        'current_prob': 0.965,
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
    
    base_result = calculate_opportunity_score(**base_params)
    print(f"\nBase Market Score: {base_result['total_score']:.2f}")
    
    # Test 1: Increase volume
    params_high_vol = base_params.copy()
    params_high_vol['volume'] = 5_000_000
    result_high_vol = calculate_opportunity_score(**params_high_vol)
    print(f"\n1. 5x Higher Volume: {result_high_vol['total_score']:.2f}")
    print(f"   Δ Score: {result_high_vol['total_score'] - base_result['total_score']:.2f}")
    assert result_high_vol['total_score'] > base_result['total_score'], "Higher volume should increase score"
    
    # Test 2: Tighter spread
    params_tight = base_params.copy()
    params_tight['best_bid'] = 0.964
    params_tight['best_ask'] = 0.966
    result_tight = calculate_opportunity_score(**params_tight)
    print(f"\n2. Tighter Spread (0.2% vs 1%): {result_tight['total_score']:.2f}")
    print(f"   Δ Score: {result_tight['total_score'] - base_result['total_score']:.2f}")
    assert result_tight['total_score'] > base_result['total_score'], "Tighter spread should increase score"
    
    # Test 3: Higher momentum
    params_momentum = base_params.copy()
    params_momentum['momentum'] = 0.50
    result_momentum = calculate_opportunity_score(**params_momentum)
    print(f"\n3. Higher Momentum (0.50 vs 0.30): {result_momentum['total_score']:.2f}")
    print(f"   Δ Score: {result_momentum['total_score'] - base_result['total_score']:.2f}")
    assert result_momentum['total_score'] > base_result['total_score'], "Higher momentum should increase score"
    
    # Test 4: Move away from sweet spot
    params_far = base_params.copy()
    params_far['current_prob'] = 0.85  # 15% distance instead of 3.5%
    result_far = calculate_opportunity_score(**params_far)
    print(f"\n4. Outside Sweet Spot (15% vs 3.5%): {result_far['total_score']:.2f}")
    print(f"   Δ Score: {result_far['total_score'] - base_result['total_score']:.2f}")
    assert result_far['total_score'] < base_result['total_score'], "Outside sweet spot should decrease score"
    
    # Test 5: Longer time
    params_long = base_params.copy()
    params_long['hours_to_expiry'] = 30 * 24
    result_long = calculate_opportunity_score(**params_long)
    print(f"\n5. Longer Expiry (30d vs 8d): {result_long['total_score']:.2f}")
    print(f"   Δ Score: {result_long['total_score'] - base_result['total_score']:.2f}")
    # Longer time away from sweet spot should decrease score
    
    print("\n✅ All comparative assertions passed!")


def main():
    """Run all validation tests."""
    print("\n" + "="*80)
    print("MULTI-MODAL SCORING SYSTEM VALIDATION")
    print("="*80)
    print("Testing realistic scenarios, edge cases, and randomized inputs")
    print("to ensure practical, sensible scoring behavior.")
    
    # Run all test suites
    realistic = run_realistic_scenarios()
    edges = run_edge_cases()
    randomized = run_randomized_tests(100)
    
    # Comparative analysis
    run_comparative_analysis()
    
    # Overall summary
    total_passed = realistic.passed + edges.passed + randomized.passed
    total_failed = realistic.failed + edges.failed + randomized.failed
    total_warnings = realistic.warnings + edges.warnings + randomized.warnings
    
    print("\n" + "="*80)
    print("OVERALL VALIDATION RESULTS")
    print("="*80)
    print(f"Total Tests Run: {total_passed + total_failed}")
    print(f"✅ Total Passed: {total_passed}")
    print(f"❌ Total Failed: {total_failed}")
    print(f"⚠️  Total Warnings: {total_warnings}")
    
    if total_failed == 0:
        print("\n🎉 ALL VALIDATION TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_failed} tests failed. Review failures above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
