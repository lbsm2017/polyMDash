# Conviction-Weighted Dashboard Architecture

## Overview

The redesigned Polymarket dashboard emphasizes **high-conviction trades from tracked users** with **consensus weighting**. Markets are grouped, scored, and ranked to surface the strongest signals.

## Core Algorithm: ConvictionScorer

### Location
`algorithms/conviction_scorer.py`

### Key Features

#### 1. Consensus Weighting
- **Single user**: Base score
- **Multiple users agreeing**: Score multiplied by `(1 + (n-1) × 3.0)` 
- Example: 2 users = 4x weight, 3 users = 7x weight

#### 2. Conviction Signals
- **Volume**: Log-scaled (large trades = higher score)
- **Price Extremity**: Bonus for betting at >85% or <15%
- **Recency**: Exponential decay (6-hour half-life)

#### 3. Directional Detection
- **Bullish**: BUY YES or SELL NO
- **Bearish**: BUY NO or SELL YES

### Scoring Formula

```python
conviction = log(volume + 1) × volume_weight
if price_extremity > 0.7:
    conviction *= (1 + extreme_price_bonus × price_extremity)
conviction *= exp(-hours_ago / 6)

final_score = conviction × consensus_multiplier
```

### Conviction Levels
- 🔥 **EXTREME** (>50): Multiple users, large positions, extreme prices
- 💎 **HIGH** (>20): Strong signals with consensus
- 📈 **MODERATE** (>10): Notable activity
- 👀 **LOW** (>5): Weak signals
- 💤 **MINIMAL** (<5): Minimal conviction

## Dashboard Features

### Filters
1. **Time Window**: 1h, 6h, 24h, 3 days
2. **Min Conviction**: All, Low+, Moderate+, High+, Extreme
3. **Min Consensus**: Number of traders that must agree (1-10)

### Market Cards Display
Each card shows:
- ✅ Market question (slug)
- 📊 Current YES/NO prices (from Gamma API)
- 👥 Consensus count & trader chips
- 🎯 Conviction level badge
- 💰 Volume breakdown (bullish/bearish)
- 📋 Expandable trade list

### Summary Metrics
- 🎯 Total signals matching filters
- 📈 Bullish markets count
- 📉 Bearish markets count  
- 💰 Total volume across all markets

## Data Flow

```
1. Load trades for tracked users (last N hours)
2. Group by market slug
3. Categorize each trade (bullish/bearish)
4. Calculate conviction per trade
5. Apply consensus multiplier
6. Sort by conviction score + recency
7. Filter by user criteria
8. Display with live market prices
```

## Configurable Parameters

In `ConvictionScorer` class:
```python
CONSENSUS_WEIGHT = 3.0        # How much to boost multi-user agreement
VOLUME_WEIGHT = 1.0           # Base weight for trade volume
EXTREME_PRICE_BONUS = 2.0     # Bonus for extreme price trades
RECENCY_DECAY_HOURS = 6       # Time decay half-life
```

## Usage

Run the dashboard:
```bash
streamlit run app.py
```

Access in browser at `http://localhost:8501`

## Future Enhancements

Potential additions:
- Historical conviction tracking (time series)
- Alerts for new high-conviction signals
- Win rate analysis per trader
- Market momentum indicators
- Smart money vs retail divergence detection
