"""
Configuration settings for Polymarket Dashboard.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = BASE_DIR / ".cache"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# API Configuration
GAMMA_API_BASE_URL = "https://gamma-api.polymarket.com"
DATA_API_BASE_URL = "https://data-api.polymarket.com"
WS_URL = "wss://ws-live-data.polymarket.com"

# Database Configuration
DATABASE_PATH = str(DATA_DIR / "polymarket.db")

# Dashboard Settings
DEFAULT_REFRESH_INTERVAL = 15  # seconds
DEFAULT_MARKETS_LIMIT = 20
DEFAULT_LEADERBOARD_LIMIT = 50
DEFAULT_TRADES_LIMIT = 100

# Leaderboard Configuration
LEADERBOARD_TIME_WINDOWS = {
    "Last 15 minutes": 15,
    "Last Hour": 60,
    "Last 24 Hours": 1440,
    "Last 7 Days": 10080,
    "All Time": None
}

# Cache Configuration (in seconds)
CACHE_TTL_MARKETS = 15
CACHE_TTL_TRADES = 10
CACHE_TTL_LEADERBOARD = 30

# Data Retention
DATA_RETENTION_DAYS = 30  # Keep data for 30 days

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Feature Flags
ENABLE_WEBSOCKET = True
ENABLE_AUTO_REFRESH = True
ENABLE_PRICE_CHARTS = True

# Display Configuration
MAX_QUESTION_LENGTH = 100
TRUNCATE_ADDRESS_LENGTH = 10

# Color scheme
COLORS = {
    "primary": "#1f77b4",
    "success": "#2ecc71",
    "danger": "#e74c3c",
    "warning": "#f39c12",
    "info": "#3498db"
}

# Market categories (can be updated based on API)
MARKET_CATEGORIES = [
    "Politics",
    "Sports",
    "Crypto",
    "Entertainment",
    "Science",
    "Business",
    "Other"
]

# User Tracking Configuration
TRACKED_USERS_FILE = "tracked_users.json"
DEFAULT_TIME_WINDOW = "Last 15 minutes"

# Activity Display Settings
MAX_ACTIVITIES_DISPLAY = 50
GROUP_BY_MARKET = True
SHOW_TRADE_DETAILS = True
