# Polymarket Dashboard

Market scanner for Polymarket with two strategies: trader tracking and momentum detection.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Strategies

**Momentum Hunter**
- Finds markets moving toward extremes (>75% or <25%)
- Extends time window for high momentum markets (≥30% price change)
- Filters out crypto markets
- Scores: extremity (30%), urgency (25%), volume (20%), momentum (25%)

**Conviction Tracker**
- Tracks specific traders' positions
- Scores based on time decay, position size, price extremity, consensus
- Sorts by recent activity, conviction, volume, or trade count

## Usage

Select strategy from dropdown. Momentum Hunter scans markets, Conviction Tracker monitors tracked users in `tracked_users.csv`.

## Structure

```
app.py                      # Main dashboard
momentum_terminal.py        # CLI scanner
algorithms/                 # Scoring logic
clients/                    # API clients
tests/                      # 130 tests
```

