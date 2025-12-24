# Polymarket Dashboard

Advanced market scanner for Polymarket with two strategies: trader tracking and momentum detection.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Strategies

### Momentum Hunter
Identifies high-opportunity markets moving toward extremes using advanced scoring and filtering.

**Key Features:**
- **Smart Scoring**: Analyzes APY, volume, momentum, and delta decay (Charm)
- **Progressive Filtering**: Excludes markets too close to 0% or 100%
- **Volume Filter**: 50k-2M range (default 500k minimum)
- **Distance Control**: Set minimum distance from extremes (0-10%, default 1.5%)
- **Flexible Timeframes**: Up to 90 days, auto-extends for high momentum markets
- **Auto-Scan**: Runs automatically on page load
- **Enhanced Display**: Color-coded metrics, smart APY formatting

**What It Finds:**
- Markets moving toward extremes (typically >75% or <25%)
- High momentum opportunities with significant price movement
- Markets with strong delta decay characteristics
- Liquid markets with sufficient trading volume
- Excludes crypto markets and markets near resolution

### Conviction Tracker
Monitors specific traders' positions with multi-factor conviction analysis.

**Features:**
- Tracks users from `tracked_users.csv`
- Time decay weighting for recent activity
- Position size and price extremity analysis
- Consensus detection across multiple traders
- Sortable by activity, conviction, volume, or trade count

## Usage

1. **Select Strategy**: Choose from dropdown (Momentum Hunter or Conviction Tracker)
2. **Configure Filters**: Adjust sliders for volume, extremity, distance, and expiry
3. **Sort Results**: Click column headers or use sort dropdown
4. **Auto-Refresh**: Momentum Hunter scans automatically on load

## Structure

```
app.py                      # Main Streamlit dashboard
terminal_app.py             # CLI interface
algorithms/
  conviction_scorer.py      # Trader conviction logic
  pullback_scanner.py       # Legacy scanner
clients/
  gamma_client.py           # Polymarket Gamma API
  trades_client.py          # Trading data API
  leaderboard_client.py     # Leaderboard API
  realtime_ws.py            # WebSocket client
data/
  database.py               # SQLite persistence
utils/
  helpers.py                # Utility functions
  user_tracker.py           # User tracking logic
tests/                      # 27 comprehensive tests
```

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test suite
pytest tests/test_momentum_hunter.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

