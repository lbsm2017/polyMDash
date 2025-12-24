# Scoring System Validation

This folder contains comprehensive validation scripts for the multi-modal scoring system used in the pullback hunter.

## Scripts

### test_scoring_validation.py

Main validation script that tests the scoring system across 114 different scenarios:

**Realistic Scenarios (6 tests)**
- Perfect sweet spot market (3.5% distance, 8 days)
- Good market outside sweet spot (8% distance, 12 days)
- Low liquidity in sweet spot
- High APY long-term market
- Short-term momentum play
- Misaligned momentum signals

**Edge Cases (8 tests)**
- Extremely close to resolution (0.5% distance)
- Very far from extreme (30% distance)
- Very short expiry (6 hours)
- Very long expiry (60 days)
- Zero volume market
- Zero momentum
- Extreme APY (10000%)
- Very wide spread (20%)

**Randomized Tests (100 tests)**
- Random but plausible market parameters
- Tests for crashes and range violations
- Ensures scoring is robust across all inputs

**Comparative Analysis**
- Compares similar markets with one variable changed
- Validates that score changes are directionally correct
- Example: Higher volume → Higher score

**Run:**
```bash
python validation/test_scoring_validation.py
```

**Expected Output:**
```
Total Tests Run: 114
✅ Total Passed: 114
❌ Total Failed: 0
⚠️  Total Warnings: 0

🎉 ALL VALIDATION TESTS PASSED!
```

### practical_scenarios.py

Real-world scenario demonstrations with practical trading interpretations:

**Six Practical Examples:**
1. 🎯 The Ideal Trade Setup (Score: ~81) - Perfect sweet spot
2. ⚠️  Too Close for Comfort (Score: ~53) - 0.7% from extreme
3. 📉 The Long Shot (Score: ~48) - 20% distance, 25 days
4. 💎 Low Liquidity Gem (Score: ~69) - Sweet spot but low volume
5. ⚡ The Sprint (Score: ~53) - 1.5 day expiry
6. 🔄 Counter-Trend Setup (Score: ~74) - Misaligned momentum

**Each scenario includes:**
- Market setup details
- Component score visualization (bar charts)
- Practical trading interpretation
- Buy/Pass/Caution recommendation

**Run:**
```bash
python validation/practical_scenarios.py
```

**Key Insights:**
- Sweet spot (3.5%, 8.5d) with good fundamentals = 81 score (A grade)
- Perfect fundamentals but 0.7% from extreme = 53 score (C+) - PASS
- Low liquidity in sweet spot still scores 69 (B+) - quality > tradeability
- Counter-trend momentum reduces score by ~7 points

### detailed_analysis.py

Deep dive analysis of specific scenarios to understand scoring behavior:

**Analyzes:**
- Why certain markets score higher/lower
- How each component contributes to total score
- Sweet spot detection logic
- Distance-time fit dominance
- Volume vs positioning tradeoffs

**Key Insights:**
1. **Distance-Time Fit (35% weight) DOMINATES**
   - Sweet spot: 2-5% distance, 7-10 days
   - Being in sweet spot is crucial for high scores

2. **Sweet Spot > Individual Components**
   - Market in sweet spot with flaws can outscore perfect fundamentals outside sweet spot
   - Example: Low volume in sweet spot scores 69, great fundamentals outside scores 43

3. **Volume Matters Less Than Expected (15% weight)**
   - Sweet spot positioning can overcome low liquidity
   - Measures opportunity quality, not just tradeability

4. **Time Penalties**
   - Sub-5 day expiries: -15 to -25 points
   - 15+ day expiries: -20 to -30 points
   - Optimizes for 7-10 day window

**Run:**
```bash
python validation/detailed_analysis.py
```

## Scoring System Overview

The multi-modal scoring system uses sophisticated mathematical functions:

### Components & Weights

1. **Distance-Time Fit (35%)** - Gaussian curves
   - Optimal: 2-5% distance AND 7-10 days
   - Interaction bonus: 1.3x when both in range
   - σ_distance = 1.5%, σ_time = 2 days

2. **APY Score (25%)** - Polynomial scaling
   - <50%: x^0.7
   - 50-100%: x^0.8
   - >100%: Logarithmic

3. **Volume Score (15%)** - Sigmoid S-curve
   - Centered at $500k (log10 = 5.7)
   - Steepness k = 1.5

4. **Spread Quality (10%)** - Inverse polynomial
   - Formula: ((1-x)^1.5) × 100
   - Tight spreads score higher

5. **Momentum (10%)** - Consistency multipliers
   - Both aligned: 1.25x
   - One aligned: 1.1x
   - Neither aligned: 0.65x

6. **Charm (5%)** - Polynomial scaling
   - <2 pp/day: x^2
   - 2-5 pp/day: x^1.5
   - 5-10 pp/day: x^1.2
   - >10 pp/day: Logarithmic

### Dynamic Weight Adjustment

Weights adjust ±0.08 to ±0.10 based on:
- Distance from sweet spot
- Days to expiry
- Ensures smooth transitions, no hard cutoffs

### Smooth Penalties

All penalties use sigmoids (no step functions):
- Distance <1%: exp(10×(d-0.005))
- Distance >20%: exp(-10×(d-0.25))

## Expected Score Ranges

Based on validation results:

| Scenario | Score Range | Grade |
|----------|-------------|-------|
| Perfect sweet spot | 70-95 | A/A+ |
| Sweet spot with flaws | 55-75 | B+/A- |
| Good fundamentals outside sweet spot | 40-65 | C/B |
| Short-term (<5d) or long-term (>15d) | 30-60 | C/C+ |
| Poor positioning or fundamentals | 10-40 | D/C- |

## Validation Results Summary

**From detailed_analysis.py:**

```
RECOMMENDED ADJUSTMENTS:
- Markets in sweet spot should score 60-80 baseline
- Markets outside sweet spot max out around 40-60
- Low liquidity reduces score by ~10-15 points
- Short expiry (<5d) reduces score by ~15-25 points
- Long expiry (>15d) reduces score by ~20-30 points
```

**Comparative Analysis Results:**
- 5x Higher Volume: +5.5 points
- Tighter Spread: +1.2 points
- Higher Momentum: +2.5 points
- Outside Sweet Spot: -29 points
- Longer Expiry: -30 points

This confirms the system prioritizes **positioning** (distance-time fit) over individual fundamentals.

### quick_validation.py

Fast validation runner for quick checks:

**Runs:**
- 6 realistic scenarios
- 8 edge cases
- 50 randomized tests (reduced from 100 for speed)
- Comparative analysis

**Run:**
```bash
python validation/quick_validation.py
```

**Output:**
```
Realistic Scenarios:  6/6 passed
Edge Cases:           8/8 passed
Randomized Tests:     50/50 passed
Comparative Analysis: ✅ All assertions passed
TOTAL:                64/64 passed
```

## Usage

Run validation after any changes to the scoring system:

```bash
# Quick validation (recommended for regular checks)
python validation/quick_validation.py

# Full validation suite (114 tests)
python validation/test_scoring_validation.py

# Practical scenario examples
python validation/practical_scenarios.py

# Detailed failure analysis
python validation/detailed_analysis.py

# All validations
python validation/test_scoring_validation.py && python validation/practical_scenarios.py
```

## Interpreting Results

**All tests passing:** Scoring system behaves as designed  
**Failed realistic scenarios:** Expected ranges need adjustment or scoring logic issue  
**Failed edge cases:** Boundary conditions not handled properly  
**Failed randomized tests:** Crashes or invalid score ranges  
**Failed comparative:** Score changes not directionally correct
