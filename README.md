# Polymarket Dashboard

Conviction-based signal detection for Polymarket markets. Tracks specific traders and identifies high-conviction consensus trades.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Architecture

**Conviction Scoring Algorithm**
- Consensus weighting: 1 + (n-1) × 3.0 multiplier for trades by multiple tracked users
- Volume scoring with logarithmic scaling
- Price extremity bonus for >85% or <15% positions
- Recency decay with 6-hour half-life

**API Integration**
- Gamma API: Market data and status
- Data API: Trade history for tracked wallets

**Tech Stack**
- Python 3.13 with Streamlit
- Async clients (aiohttp)
- SQLite for persistence
- CSV-based user tracking

## Structure

```
app.py                      # Main dashboard
tracked_users.csv           # Tracked wallet addresses
algorithms/
  conviction_scorer.py      # Core scoring algorithm
clients/
  gamma_client.py           # Market data client
  trades_client.py          # Trade history client
data/
  database.py               # SQLite persistence
utils/
  user_tracker.py           # CSV user management
  helpers.py                # Utility functions
tests/                      # 44 passing tests
docs/                       # API and architecture docs
```

## Usage

Dashboard displays open markets with consensus trades from tracked users. Filterable by:
- Time window (15min to 7 days)
- Conviction level (EXTREME, HIGH, MODERATE, LOW)
- Minimum consensus count

Auto-refresh enabled by default (30s interval).

## Configuration

Edit `tracked_users.csv` to modify tracked traders:
```csv
name,address
HolyMoses7,0xa4b366ad22fc0d06f1e934ff468e8922431a87b8
Bass,0x596422bcdd897703b96f4f931961b181b79d35df
```

Tune algorithm weights in `algorithms/conviction_scorer.py`.

## Testing

```bash
pytest
```

All 44 tests passing.
