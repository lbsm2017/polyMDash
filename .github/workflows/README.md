# GitHub Workflows Documentation

## Overview

Three automated validation workflows have been set up to ensure the scoring algorithm remains correct and performs sensibly across all scenarios.

## Workflows

### 1. **validation.yml** - Automatic Validation Pipeline
**Trigger:** Automatically runs on push/PR when `app.py` or validation files change

**Jobs:**
- `quick-validation`: Fast smoke test (64 tests, ~10 seconds)
- `full-validation`: Comprehensive test suite (114 tests, ~15 seconds)
- `scenario-testing`: Practical scenarios & edge case testing
- `test-suite`: Project unit tests via pytest
- `validation-summary`: Reports overall results

**What it tests:**
- Sweet spot targeting (2-5% distance, 7-10 days)
- Distance sensitivity
- Time sensitivity
- Volume impact
- APY scaling
- Momentum alignment (including the fine-tuned 6.6pt penalty)
- Spread quality
- Edge cases
- Randomized scenarios (100 tests)

### 2. **manual-validation.yml** - On-Demand Validation
**Trigger:** Manual trigger via GitHub Actions → "Run workflow"

**Options:**
- `quick` - Quick validation (64 tests)
- `full` - Full test suite (114 tests)
- `practical` - Real-world scenarios
- `rigorous` - Edge case testing
- `all` - Run everything

**Use when:**
- You want to manually verify changes
- Testing before committing
- Debugging scoring behavior
- Validating specific scenarios

### 3. **validation-check.yml** - Smart PR Validation
**Trigger:** Automatically runs on all PRs to main/develop

**Features:**
- Detects if `app.py` was modified
- Runs quick validation for all PRs (fast feedback)
- Runs full validation only if `app.py` changed (saves CI time)
- Posts results as PR comment
- Provides detailed validation output

## Running Tests Locally

Before pushing, run locally:

```bash
# Quick smoke test (64 tests)
python validation/quick_validation.py

# Full comprehensive suite (114 tests)
python validation/test_scoring_validation.py

# Real-world scenarios
python validation/practical_scenarios.py

# Edge case testing
python validation/rigorous_testing.py
```

## Validation Test Scripts

### test_scoring_validation.py (114 tests)
**Purpose:** Comprehensive scoring system validation

**Tests:**
- 6 realistic scenarios (perfect sweet spot, low liquidity, high APY, etc.)
- 8 edge cases (0.5% distance, 60 days, extreme APY, wide spreads, etc.)
- 100 randomized tests with random parameters
- 5 comparative analysis assertions

**Expected Output:** All 114 tests pass

### quick_validation.py (64 tests)
**Purpose:** Fast smoke test for rapid feedback

**Tests:**
- 6 realistic scenarios
- 8 edge cases
- 50 randomized tests (reduced for speed)
- Comparative analysis

**Expected Output:** All 64 tests pass (~10 seconds)

### practical_scenarios.py
**Purpose:** Real-world trading scenario demonstrations

**Scenarios:**
1. Perfect sweet spot (3.5%, 8.5d, $2M) → Score 81 (A)
2. Too close (0.7%, 5d, $5M) → Score 53 (C+)
3. Long-term low probability (20%, 25d) → Score 48 (C+)
4. Low liquidity gem (3%, 9d, $50k) → Score 69 (B+)
5. Short-term momentum (4%, 1.5d) → Score 53 (C+)
6. Counter-trend (3.5%, 8d, misaligned) → Score 69 (B+)

**Expected Output:** Visual component scores and trading interpretation

### rigorous_testing.py
**Purpose:** Identify non-sensible scoring behavior

**Tests:** 6 test groups across 40+ scenarios
- Distance sensitivity (0.5% to 30%)
- Time sensitivity (6 hours to 60 days)
- Volume impact ($0 to $20M)
- APY scaling (50% to 10000%)
- Momentum alignment (both aligned to both misaligned)
- Spread quality (0.04% to 10%)

**Expected Output:** Analysis of score progression and recommendations

## What Each Test Validates

### Sweet Spot Detection
- 2-5% distance AND 7-10 days = highest scoring
- Smooth transitions, no hard cutoffs
- Peak at 3.5% distance, 8.5 days

### Momentum Alignment (Fine-Tuned)
- Both aligned: 1.5x multiplier → ~6 point boost vs counter-trend
- One aligned: 1.0x multiplier → neutral
- Neither aligned: 0.5x multiplier + 5% risk penalty → ~6.6 point penalty
- **Improvement:** 269% stronger impact (was 1.8 pts, now 6.6 pts)

### Component Weights
- Distance-Time Fit: 35% (dominant factor)
- APY: 25%
- Volume: 15%
- Spread: 10%
- Momentum: 10%
- Charm: 5%

### Score Ranges
- 85-100: A+/A (Strong opportunities)
- 70-84: A/B+ (Good opportunities)
- 55-69: B/C+ (Fair opportunities)
- <55: C/D (Poor opportunities)

## CI/CD Integration

### GitHub Status Checks
All validation workflows must pass for:
- Merging PRs to main/develop
- Deploying changes
- Releasing new versions

### Artifact Collection
All workflows save results as GitHub artifacts for:
- Historical tracking
- Debugging failed runs
- Performance analysis
- Regression detection

### Notifications
Workflows post PR comments with:
- Validation status
- Test counts
- Performance metrics
- Links to detailed results

## Performance Benchmarks

| Test Suite | Tests | Duration | Purpose |
|-----------|-------|----------|---------|
| Quick | 64 | ~10s | Smoke test |
| Full | 114 | ~15s | Comprehensive |
| Practical | 6 | ~5s | Scenarios |
| Rigorous | 40+ | ~20s | Edge cases |

## Troubleshooting

### Validation fails on PR
1. Run `python validation/quick_validation.py` locally
2. Check which test failed
3. Run `python validation/rigorous_testing.py` for detailed analysis
4. Fix the issue and test locally before pushing

### Specific component not working
1. Run `python validation/practical_scenarios.py` to see component scores
2. Check if new weight changes were made
3. Verify momentum multipliers are correct (1.5x, 1.0x, 0.5x)
4. Ensure no hard cutoffs were accidentally added

### Random test fails
Run the full validation multiple times locally to catch rare failures.

## Adding New Tests

To add new validation tests:

1. Create a new function in one of the validation scripts
2. Follow the pattern:
   ```python
   validator.validate_scenario(
       "Scenario Name",
       {params},
       {'min_score': X, 'max_score': Y, ...}
   )
   ```
3. Run locally: `python validation/quick_validation.py`
4. Commit and push - GitHub workflows will run automatically

## Next Steps

1. **Push this branch** - Workflows will trigger on first push
2. **Monitor GitHub Actions** - Check results on Actions tab
3. **Set up branch protection** - Require passing checks before merge
4. **Track trends** - Monitor validation results over time
5. **Iterate** - Use results to guide algorithm improvements
