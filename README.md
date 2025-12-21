# Polymarket Dashboard

Real-time market scanner for Polymarket. Dual strategy approach: track specific traders for conviction signals, or hunt momentum opportunities in extreme markets.

## Installation

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Features

### 🎯 Momentum Hunter
- **Extreme Market Detection**: Scans for markets moving toward 100% or 0%
- **Multi-Strategy Fetching**: Combines liquidity, default, and offset-based API queries
- **Smart Time Windows**: 3-day base window, extends to 14 days for high momentum (≥30%)
- **Momentum Scoring**: Weighs extremity (30%), urgency (25%), volume (20%), and momentum (25%)
- **Crypto Filtering**: Always excludes Bitcoin, Ethereum, Solana, XRP markets
- **Qualification Logic**: Markets qualify if extreme (>75%/<25%) OR high momentum (≥30%) with >60%/<40% probability

### 📊 Conviction Tracker
- **Smart Conviction Scoring**: Algorithm with time decay, volatility dampening, and Kelly criterion
- **High-Performance API Pool**: Parallel data fetching with connection reuse (5-10x speedup)
- **Real-Time Position Tracking**: Monitor tracked traders' positions with recency indicators
- **Flexible Sorting**: Sort by recent activity, conviction, volume, or number of trades
- **Clean UI**: Compact display showing user positions, prices, and trade timing

## Architecture

### Momentum Hunter Strategy

**Market Qualification**
- **Extremity Threshold**: >75% or <25% probability (configurable min extremity)
- **Momentum Boost**: ≥30% price change (24h or 1wk) qualifies markets with >60%/<40% probability
- **Time Window Extension**: High momentum markets (≥30%) get 5x longer window (70 days vs 14 days default)
- **Momentum Calculation**: max(oneDayPriceChange, oneWeekPriceChange) for best signal

**Scoring Algorithm** (0-100 scale)
- **Extremity (30%)**: Distance from 50% probability
- **Urgency (25%)**: Time remaining until expiration
- **Volume (20%)**: 24h trading volume (capped at $100K)
- **Momentum (25%)**: Price change velocity (capped at 50%)

**Multi-Strategy Data Fetching**
1. Liquidity-sorted markets (primary)
2. Default API sorting (secondary)
3. Offset pagination (500, 1000, 1500) to skip crypto-heavy top results
4. Deduplication by market slug across all strategies

**Crypto Filtering**
- Excluded terms: bitcoin, btc, crypto, ethereum, eth, solana, sol, xrp, updown, up-down
- Always applied (even in debug mode)
- Filters on both slug and question text

### Conviction Tracker Strategy

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
- Gamma API: Market data, active/closed status, price changes
- Data API: Trade history via `/trades?user=` endpoint
- Multi-strategy market fetching for Momentum Hunter

**Tech Stack**
- Python 3.13 with Streamlit
- Async architecture (aiohttp with TCPConnector)
- CSV-based user tracking
- SQLite for persistence
- HTML component rendering for tables

## Structure

```
app.py                      # Main dashboard with strategy selector
momentum_terminal.py        # CLI momentum scanner
tracked_users.csv           # Tracked wallet addresses
algorithms/
  conviction_scorer.py      # Black-Scholes inspired scoring
  pullback_scanner.py       # Momentum opportunity detection (legacy)
clients/
  api_pool.py               # High-performance connection pool
  gamma_client.py           # Market data client (supports category filtering)
  trades_client.py          # Trade history client
  leaderboard_client.py     # Polymarket leaderboard data
  realtime_ws.py            # WebSocket client for real-time updates
data/
  database.py               # SQLite persistence
utils/
  user_tracker.py           # CSV user management
  helpers.py                # Utility functions
tests/                      # 130 passing tests
  test_momentum_hunter.py   # 13 momentum scanner tests
  test_conviction_scorer.py # Conviction algorithm tests
  test_clients.py           # API client tests
  test_integration.py       # Integration tests
docs/                       # API and architecture docs
```

## Usage

### Momentum Hunter
1. Select "Momentum Hunter" from strategy dropdown
2. Configure in sidebar:
   - **Max Days to Expiry**: Base window (default: 14 days)
   - **Min Extremity**: Distance from 50% (default: 0.25 = 75%/25%)
   - **Max Markets to Scan**: Number of markets (default: 1000)
   - **Debug Mode**: Show all markets without filters
3. Click "🔍 Scan Markets"
4. Results sorted by expiration (soonest first)
5. Table columns: Market, Prob, Dir, Mom, Vol, Expires, Score

### Conviction Tracker
### Conviction Tracker
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

### Momentum Hunter
Adjust scanning parameters in sidebar or modify defaults in `app.py`:
- `max_expiry_days`: Base time window in days (default: 14)
- `min_extremity`: Minimum probability distance from 50% (default: 0.25)
- `limit`: Maximum markets to scan (default: 1000, max: 5000)
- `min_momentum`: Minimum price change to qualify (default: 15%)
- `high_momentum`: Threshold for extended window (default: 30%)

### Conviction Tracker

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

**Test Coverage**
- 130 total tests passing
- 13 Momentum Hunter tests (qualification, scoring, filtering, sorting)
- 54+ Conviction Tracker tests (time decay, volatility, Kelly criterion)
- 18 API client tests (connection pooling, error handling)
- 45+ integration and edge case tests

**Momentum Hunter Test Suite**
- Crypto filtering (Bitcoin, Ethereum, Solana, etc.)
- Extremity qualification (>75%/<25%)
- Momentum qualification (≥30% with >60%/<40%)
- Time window extension (5x for high momentum)
- Price extraction with fallback logic
- Scoring algorithm validation
- Expiration filtering
- Debug mode behavior
- Sorting and display formatting

## Performance

- **Connection Pooling**: Persistent TCP connections with keep-alive
- **Parallel Fetching**: All trades and markets fetched in single batch
- **Multi-Strategy Scanning**: Combines liquidity, default, and offset queries
- **Expected Speedup**: 5-10x faster than sequential requests
- **Concurrency Limit**: Max 20 parallel requests via semaphore
- **Crypto Filtering**: Pre-filters before processing to reduce load

## CLI Tools

**Momentum Terminal**
```bash
python momentum_terminal.py
```
Standalone CLI scanner with colorized output, same logic as dashboard Momentum Hunter.

## Roadmap

- [ ] Real-time WebSocket updates for Momentum Hunter
- [ ] Historical momentum trend charts
- [ ] Category-specific momentum tracking
- [ ] Export opportunities to CSV
- [ ] Mobile-responsive table layout
- [ ] Custom alert thresholds
