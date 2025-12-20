# Polymarket Dashboard

Real-time trader scanner for Polymarket markets. Tracks specific traders and surfaces high-conviction signals using Black-Scholes inspired scoring.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features

- **Smart Conviction Scoring**: Black-Scholes inspired algorithm with time decay, volatility dampening, and Kelly criterion
- **High-Performance API Pool**: Parallel data fetching with connection reuse (5-10x speedup)
- **Real-Time Position Tracking**: Monitor tracked traders' positions with recency indicators
- **Flexible Sorting**: Sort by recent activity, conviction, volume, or number of trades
- **Clean UI**: Compact display showing user positions, prices, and trade timing

## Architecture

**Black-Scholes Inspired Conviction Scoring**
- **Time Decay (Theta)**: Exponential decay with 6-hour half-life
- **Volatility Dampening**: Historical price movement reduces noise (up to 50% score reduction)
- **Direction Strength**: Kelly criterion - maximum conviction at price extremes (0.05/0.95)
- **Size Score**: Log-scaled position sizing prevents outlier dominance
- **Consensus Bonus**: Exponential growth (1.5^n) for multiple users
- **Momentum Detection**: 30% bonus when trades cluster within 1 hour

**Conviction Levels** (0-100 scale):
- 🔥 EXTREME (60+): Very high conviction
- 💎 HIGH (40-60): Strong conviction
- 📈 MODERATE (20-40): Good conviction
- 👀 LOW (10-20): Weak signal
- 💤 MINIMAL (<10): Very weak

**API Integration**
- High-performance connection pooling (100 connections, 20/host)
- Parallel batch fetching for all trades and markets
- Gamma API: Market data and status
- Data API: Trade history via `/trades?user=` endpoint

**Tech Stack**
- Python 3.13 with Streamlit
- Async architecture (aiohttp with TCPConnector)
- CSV-based user tracking
- SQLite for persistence

## Structure

```
app.py                      # Main dashboard with sorting and filtering
tracked_users.csv           # Tracked wallet addresses (11 traders)
algorithms/
  conviction_scorer.py      # Black-Scholes inspired scoring
clients/
  api_pool.py               # High-performance connection pool
  gamma_client.py           # Market data client
  trades_client.py          # Trade history client
data/
  database.py               # SQLite persistence
utils/
  user_tracker.py           # CSV user management
  helpers.py                # Utility functions
tests/                      # 47 passing tests
docs/                       # API and architecture docs
```

## Usage

Dashboard displays open markets with tracked user positions. Features:
- **Sorting Options**: Recent Activity (default), Conviction, Volume ($), Number of Trades
- **Position Details**: Each trader shows [time since last trade] · position size @ price
- **Time Formatting**: 
  - < 60m: `[15m]`
  - 60m-24h: `[1h23m]`
  - 24h-30d: `[2d5h]`
  - > 30d: `[1M15d]`
- **Auto-Refresh**: Updates every 30 seconds

## Configuration

Edit `tracked_users.csv` to modify tracked traders:
```csv
name,address
HolyMoses7,0x1234...
Bass,0x5678...
```

Tune algorithm parameters in `algorithms/conviction_scorer.py`:
- `TIME_DECAY_HOURS`: Time decay half-life (default: 6.0)
- `SIZE_WEIGHT`: Position size weighting (default: 15.0)
- `CONSENSUS_BASE`: Consensus exponential base (default: 1.5)
- `DIRECTION_WEIGHT`: Price extremity weight (default: 10.0)
- `MOMENTUM_BONUS`: Clustering bonus multiplier (default: 1.3)

## Testing

```bash
python run_tests.py
# or
pytest
```

All 47 tests passing.

## Performance

- **Connection Pooling**: Persistent TCP connections with keep-alive
- **Parallel Fetching**: All trades and markets fetched in single batch
- **Expected Speedup**: 5-10x faster than sequential requests
- **Concurrency Limit**: Max 20 parallel requests via semaphore
