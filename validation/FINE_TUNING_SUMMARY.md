# Scoring Algorithm Fine-Tuning Summary

## Date: December 24, 2025

### Issue Identified

**Problem:** Momentum alignment impact was too low
- Both aligned vs both misaligned: Only **1.8 point difference**
- Expected: 5-10 point difference for significant behavioral signal

**Root Cause:** 
- Momentum has 10% weight in total score
- Even large component differences (37.5 vs 19.5 = 18 points) resulted in small total impact
- Multipliers (1.25x aligned, 0.65x misaligned) were too conservative

### Solution Implemented

**Hybrid Approach:** Stronger multipliers + Risk penalty

#### 1. Increased Momentum Multipliers
```python
# Before:
- Both aligned: 1.25x
- One aligned: 1.1x  
- Neither aligned: 0.65x

# After:
- Both aligned: 1.5x    # +20% stronger boost
- One aligned: 1.0x     # Neutral baseline (no boost/penalty)
- Neither aligned: 0.5x  # -23% stronger penalty
```

#### 2. Added Counter-Trend Risk Penalty
When both 1d and 7d momentum are misaligned with direction:
- Apply **5% overall score reduction** (risk_penalty = 0.95)
- Flags counter-trend setups as higher risk
- Additional penalty beyond component score reduction

### Results

#### Before Fix:
| Scenario | Score | Momentum Component | Difference |
|----------|-------|-------------------|------------|
| Both aligned | 75.2 | 37.5 | baseline |
| One aligned | 74.7 | 33.0 | -0.5 pts |
| Neither aligned | 73.4 | 19.5 | -1.8 pts |

#### After Fix:
| Scenario | Score | Momentum Component | Difference |
|----------|-------|-------------------|------------|
| Both aligned | 75.9 | 45.0 | baseline |
| One aligned | 74.9 | 30.0 | -1.0 pts |
| Neither aligned | **69.3** | 15.0 | **-6.6 pts** ✅ |

**Improvement:** Counter-trend penalty increased from **1.8 → 6.6 points** (3.7x stronger!)

### Validation Results

**All 114 tests passing:**
- ✅ Realistic scenarios: 6/6
- ✅ Edge cases: 8/8
- ✅ Randomized tests: 100/100
- ✅ Comparative analysis: All assertions passed

**Key Validation Points:**
1. Sweet spot positioning still dominates (35% weight unchanged)
2. Counter-trend setups now properly flagged (69.3 vs 75.9 = 6.6 point penalty)
3. Momentum alignment creates meaningful score difference
4. No regression in other components

### Practical Impact

#### Example: Perfect Sweet Spot Market (96.5%, 8.5 days, $1M volume)

**With Aligned Momentum:**
```
Score: 75.9 (A grade)
Momentum Component: 45.0/100
Recommendation: BUY
```

**With Misaligned Momentum (Counter-Trend):**
```
Score: 69.3 (B+ grade)
Momentum Component: 15.0/100
Recommendation: CAUTION - Investigate why momentum opposes direction
```

The 6.6 point difference is meaningful:
- Drops from A to B+ grade
- Signals potential topping/distribution
- Still scores reasonably (69.3) due to sweet spot position
- But traders will notice the momentum warning

### Technical Implementation

**Files Modified:**
1. [app.py](app.py) - Lines 1108-1133, 1191-1209
   - Updated momentum multipliers (1.5x, 1.0x, 0.5x)
   - Added `is_counter_trend` flag
   - Applied 5% risk penalty to final score

**No Changes Required:**
- Weights remain: 35% dist-time, 25% APY, 15% volume, 10% spread, 10% momentum, 5% charm
- All other components unchanged
- Sweet spot targeting unchanged (2-5%, 7-10d)

### Mathematical Validation

**Momentum Component Calculation:**
```python
# Base momentum score
momentum_score = momentum * 100  # e.g., 0.30 * 100 = 30

# Apply alignment multiplier
if both_aligned:
    momentum_score *= 1.5  # 30 * 1.5 = 45
elif one_aligned:
    momentum_score *= 1.0  # 30 * 1.0 = 30
else:  # counter-trend
    momentum_score *= 0.5  # 30 * 0.5 = 15
    is_counter_trend = True

# Final score calculation
raw_score = (components × weights)  # e.g., 75.9

if is_counter_trend:
    final_score = raw_score * 0.95  # 75.9 * 0.95 = 72.1
                                     # Then combined with reduced momentum component = 69.3
```

### Behavioral Changes

| Situation | Old Behavior | New Behavior | Improvement |
|-----------|-------------|--------------|-------------|
| Strong counter-trend setup | 73.4 (B+) - minimal warning | 69.3 (B+) - clear 6.6pt penalty | ✅ More cautious |
| Mixed signals (1 aligned) | 74.7 (B+) - slight penalty | 74.9 (B+) - neutral | ✅ Less harsh |
| Trend-aligned setup | 75.2 (A) - good | 75.9 (A) - rewarded | ✅ Better signal |

### Edge Cases Tested

1. **Zero momentum:** Still handled gracefully (0 × 1.5 = 0)
2. **Extreme momentum (0.8):** Caps at 100 (80 × 1.5 = 120 → capped)
3. **Perfect sweet spot + counter-trend:** Scores 69.3 (properly penalized)
4. **Poor positioning + aligned momentum:** Still scores low (~46) - positioning dominates
5. **Random scenarios:** All 100 random tests pass

### Conclusion

**Status:** ✅ Successfully implemented and validated

The scoring algorithm now properly reflects the risk of counter-trend setups while maintaining:
- Sweet spot dominance (35% weight)
- Smooth transitions (no hard cutoffs)
- Sensible score ranges
- All existing validations passing

**Impact:** Traders will now see a meaningful 5-7 point penalty for markets where momentum opposes the predicted direction, providing a clear risk signal while still allowing the sweet spot positioning to be the primary factor.
