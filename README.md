# Polymarket Dashboard

A Python-based real-time dashboard for Polymarket, featuring market discovery, trade tracking, and leaderboards.

## Features

- 🔥 **Hot Markets**: Browse trending markets by volume and activity
- 🏆 **Leaderboard**: Track top traders and their performance
- 👁️ **Watchlist**: Monitor selected markets with live updates
- 📊 **Live Data**: Real-time price and trade feeds via WebSocket
- 📈 **Analytics**: Market statistics and trader insights

## Architecture

### API Layers
- **Gamma API**: Market metadata and discovery
- **Data API**: Trade history and user activity
- **WebSocket (RTDS)**: Real-time price and volume updates

### Tech Stack
- **Frontend**: Streamlit
- **Backend**: Async Python with aiohttp
- **Database**: SQLite
- **Real-time**: WebSocket client

## Project Structure

```
polyMDash/
├── app.py                  # Main Streamlit application
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── clients/                # API client modules
│   ├── __init__.py
│   ├── gamma_client.py     # Gamma API client
│   ├── trades_client.py    # Trades API client
│   └── realtime_ws.py      # WebSocket client
├── data/                   # Data layer
│   ├── database.py         # Database models and queries
│   └── polymarket.db       # SQLite database (created on first run)
├── pages/                  # Additional Streamlit pages
├── models/                 # Data models
└── utils/                  # Utility functions

```

## Installation

1. **Clone or navigate to the project directory**

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the dashboard**
```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Usage

### Hot Markets
- Browse trending markets sorted by 24-hour volume
- Filter by category and status
- Add markets to your watchlist

### Leaderboard
- View top traders by volume
- Filter by time window (15 min, 1 hour, 24 hours, etc.)
- See trade counts and market diversity

### Watchlist
- Track selected markets
- View real-time price updates
- Monitor volume and liquidity changes

### Live Data
- Real-time trade feed
- Price update stream
- Market activity monitoring

## Configuration

Edit `config.py` to customize:
- Refresh intervals
- Cache durations
- Data retention periods
- Display settings

## API Clients

### Gamma API Client
```python
from clients.gamma_client import GammaClient

async with GammaClient() as client:
    markets = await client.get_hot_markets(limit=20)
```

### Trades API Client
```python
from clients.trades_client import TradesClient

async with TradesClient() as client:
    leaderboard = await client.compute_leaderboard()
```

### WebSocket Client
```python
from clients.realtime_ws import PriceTracker

tracker = PriceTracker()
await tracker.start(market_ids=["market-1", "market-2"])
```

## Database Schema

### Markets Table
- Market metadata and current state
- Outcome prices and volume
- Activity timestamps

### Trades Table
- Individual trade records
- User addresses and volumes
- Timestamps for analysis

### Users Table
- Trader statistics
- Leaderboard cache
- Activity summaries

### Watchlist Table
- User-selected markets
- Tracking preferences

## Development

### Testing API Clients
Each client module can be run independently:

```bash
python clients/gamma_client.py
python clients/trades_client.py
python clients/realtime_ws.py
```

### Database Management
```bash
python data/database.py
```

## Features Roadmap

- [ ] Advanced price charts and technical indicators
- [ ] User portfolio tracking
- [ ] Market alerts and notifications
- [ ] Historical data analysis
- [ ] Export functionality (CSV, JSON)
- [ ] Custom market filters and search
- [ ] Mobile-responsive design enhancements

## Troubleshooting

**Markets not loading?**
- Check internet connection
- Verify API endpoints are accessible
- Check console for error messages

**Database errors?**
- Ensure `data/` directory has write permissions
- Delete `polymarket.db` to reset database

**WebSocket connection issues?**
- Check firewall settings
- Verify WebSocket URL is accessible
- Review logs for connection errors

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built on [Polymarket](https://polymarket.com) APIs
- Powered by [Streamlit](https://streamlit.io)
