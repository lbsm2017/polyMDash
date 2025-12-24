"""
Database models and schema for Polymarket dashboard.
Uses SQLite for persistent storage of markets, trades, and user data.
"""

import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager for Polymarket data."""
    
    def __init__(self, db_path: str = "data/polymarket.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.conn = None
        self._initialize_schema()
        
    def connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        logger.info(f"Connected to database: {self.db_path}")
        
    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
            
    def _initialize_schema(self):
        """Create database tables if they don't exist."""
        self.connect()
        cursor = self.conn.cursor()
        
        # Markets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                slug TEXT UNIQUE,
                category TEXT,
                active BOOLEAN,
                closed BOOLEAN,
                end_date TIMESTAMP,
                outcomes TEXT,  -- JSON array
                outcome_prices TEXT,  -- JSON object
                liquidity REAL,
                volume REAL,
                volume_24h REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT,
                user_address TEXT NOT NULL,
                side TEXT,  -- BUY/SELL
                outcome TEXT,
                price REAL NOT NULL,
                size REAL NOT NULL,
                volume REAL,  -- price * size
                timestamp TIMESTAMP NOT NULL,
                event_slug TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (market_id) REFERENCES markets(id)
            )
        """)
        
        # Create index on trades for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_user 
            ON trades(user_address)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_market 
            ON trades(market_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
            ON trades(timestamp DESC)
        """)
        
        # Users/Traders table (for leaderboard caching)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                address TEXT PRIMARY KEY,
                display_name TEXT,
                total_volume REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                markets_traded INTEGER DEFAULT 0,
                last_trade_time TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Price history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                outcome TEXT,
                price REAL NOT NULL,
                volume REAL,
                liquidity REAL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (market_id) REFERENCES markets(id)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_history_market 
            ON price_history(market_id, timestamp DESC)
        """)
        
        # Watchlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL UNIQUE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (market_id) REFERENCES markets(id)
            )
        """)
        
        self.conn.commit()
        logger.info("Database schema initialized")
        
    # ===== Cache Management Methods =====
    
    def is_cache_fresh(self, table: str, max_age_seconds: int = 300) -> bool:
        """
        Check if cached data in a table is fresh enough.
        
        Args:
            table: Table name to check
            max_age_seconds: Maximum age in seconds (default 5 minutes)
            
        Returns:
            True if cache is fresh, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT MAX(updated_at) as last_update FROM {table}
        """)
        result = cursor.fetchone()
        
        if not result or not result['last_update']:
            return False
            
        last_update = datetime.fromisoformat(result['last_update'])
        age_seconds = (datetime.now() - last_update).total_seconds()
        
        return age_seconds <= max_age_seconds
    
    def get_cache_age(self, table: str) -> Optional[float]:
        """
        Get the age of cached data in seconds.
        
        Args:
            table: Table name to check
            
        Returns:
            Age in seconds, or None if no data
        """
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT MAX(updated_at) as last_update FROM {table}
        """)
        result = cursor.fetchone()
        
        if not result or not result['last_update']:
            return None
            
        last_update = datetime.fromisoformat(result['last_update'])
        return (datetime.now() - last_update).total_seconds()
        
    # ===== Markets Methods =====
    
    def upsert_market(self, market_data: Dict):
        """
        Insert or update a market record.
        
        Args:
            market_data: Market data dictionary
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO markets (
                id, question, slug, category, active, closed, end_date,
                outcomes, outcome_prices, liquidity, volume, volume_24h, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                question = excluded.question,
                category = excluded.category,
                active = excluded.active,
                closed = excluded.closed,
                end_date = excluded.end_date,
                outcomes = excluded.outcomes,
                outcome_prices = excluded.outcome_prices,
                liquidity = excluded.liquidity,
                volume = excluded.volume,
                volume_24h = excluded.volume_24h,
                updated_at = excluded.updated_at
        """, (
            market_data.get('id'),
            market_data.get('question'),
            market_data.get('slug'),
            market_data.get('category'),
            market_data.get('active'),
            market_data.get('closed'),
            market_data.get('endDate'),
            json.dumps(market_data.get('outcomes', [])),
            json.dumps(market_data.get('outcomePrices', {})),
            market_data.get('liquidity'),
            market_data.get('volume'),
            market_data.get('volume24hr'),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
        
    def get_market(self, market_id: str) -> Optional[Dict]:
        """
        Get a market by ID.
        
        Args:
            market_id: Market identifier
            
        Returns:
            Market data dictionary or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM markets WHERE id = ?", (market_id,))
        row = cursor.fetchone()
        
        if row:
            return self._parse_market_row(row)
        return None
        
    def get_active_markets(self, limit: int = 50) -> List[Dict]:
        """
        Get active markets.
        
        Args:
            limit: Maximum number of markets to return
            
        Returns:
            List of market dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM markets 
            WHERE active = 1 
            ORDER BY volume_24h DESC 
            LIMIT ?
        """, (limit,))
        
        return [self._parse_market_row(row) for row in cursor.fetchall()]
        
    # ===== Trades Methods =====
    
    def insert_trade(self, trade_data: Dict):
        """
        Insert a trade record.
        
        Args:
            trade_data: Trade data dictionary
        """
        cursor = self.conn.cursor()
        
        price = float(trade_data.get('price', 0))
        size = float(trade_data.get('size', 0))
        volume = price * size
        
        cursor.execute("""
            INSERT INTO trades (
                market_id, user_address, side, outcome, price, size, volume,
                timestamp, event_slug
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get('market'),
            trade_data.get('proxyWallet'),
            trade_data.get('side'),
            trade_data.get('outcome'),
            price,
            size,
            volume,
            trade_data.get('timestamp'),
            trade_data.get('eventSlug')
        ))
        
        self.conn.commit()
        
    def get_recent_trades(self, limit: int = 100) -> List[Dict]:
        """
        Get recent trades.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of trade dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM trades 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
        
    def get_user_trades(self, user_address: str, limit: int = 100) -> List[Dict]:
        """
        Get trades for a specific user.
        
        Args:
            user_address: User's wallet address
            limit: Maximum number of trades to return
            
        Returns:
            List of trade dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM trades 
            WHERE user_address = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (user_address, limit))
        
        return [dict(row) for row in cursor.fetchall()]
        
    # ===== Leaderboard Methods =====
    
    def update_user_stats(self, user_address: str, stats: Dict):
        """
        Update user statistics for leaderboard.
        
        Args:
            user_address: User's wallet address
            stats: Statistics dictionary
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO users (
                address, total_volume, total_trades, markets_traded,
                last_trade_time, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                total_volume = excluded.total_volume,
                total_trades = excluded.total_trades,
                markets_traded = excluded.markets_traded,
                last_trade_time = excluded.last_trade_time,
                updated_at = excluded.updated_at
        """, (
            user_address,
            stats.get('total_volume', 0),
            stats.get('trade_count', 0),
            stats.get('markets_traded', 0),
            stats.get('last_trade_time'),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
        
    def get_leaderboard(self, limit: int = 100) -> List[Dict]:
        """
        Get top traders leaderboard.
        
        Args:
            limit: Number of top traders to return
            
        Returns:
            List of user statistics
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM users 
            ORDER BY total_volume DESC 
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
        
    # ===== Price History Methods =====
    
    def add_price_update(self, price_data: Dict):
        """
        Add a price history record.
        
        Args:
            price_data: Price update data
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO price_history (
                market_id, outcome, price, volume, liquidity, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            price_data.get('market_id'),
            price_data.get('outcome'),
            price_data.get('price'),
            price_data.get('volume'),
            price_data.get('liquidity'),
            price_data.get('timestamp', datetime.now().isoformat())
        ))
        
        self.conn.commit()
        
    def get_price_history(
        self,
        market_id: str,
        hours: int = 24
    ) -> List[Dict]:
        """
        Get price history for a market.
        
        Args:
            market_id: Market identifier
            hours: Number of hours of history to retrieve
            
        Returns:
            List of price history records
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM price_history 
            WHERE market_id = ? 
                AND timestamp >= datetime('now', '-' || ? || ' hours')
            ORDER BY timestamp ASC
        """, (market_id, hours))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_momentum_from_cache(self, market_id: str, hours: int = 48) -> Optional[Dict]:
        """
        Calculate momentum from cached price history.
        
        Args:
            market_id: Market identifier
            hours: Time window for momentum calculation
            
        Returns:
            Dict with momentum data or None if insufficient data
        """
        history = self.get_price_history(market_id, hours)
        
        if len(history) < 2:
            return None
            
        oldest = history[0]
        newest = history[-1]
        
        price_change = newest['price'] - oldest['price']
        time_delta = (datetime.fromisoformat(newest['timestamp']) - 
                     datetime.fromisoformat(oldest['timestamp'])).total_seconds() / 3600
        
        return {
            'momentum': price_change,
            'time_hours': time_delta,
            'oldest_price': oldest['price'],
            'newest_price': newest['price'],
            'data_age_seconds': (datetime.now() - 
                               datetime.fromisoformat(newest['timestamp'])).total_seconds()
        }
    
    def bulk_upsert_markets(self, markets: List[Dict]):
        """
        Bulk insert or update multiple markets efficiently.
        
        Args:
            markets: List of market data dictionaries
        """
        cursor = self.conn.cursor()
        
        for market_data in markets:
            cursor.execute("""
                INSERT INTO markets (
                    id, question, slug, category, active, closed, end_date,
                    outcomes, outcome_prices, liquidity, volume, volume_24h, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    question = excluded.question,
                    category = excluded.category,
                    active = excluded.active,
                    closed = excluded.closed,
                    end_date = excluded.end_date,
                    outcomes = excluded.outcomes,
                    outcome_prices = excluded.outcome_prices,
                    liquidity = excluded.liquidity,
                    volume = excluded.volume,
                    volume_24h = excluded.volume_24h,
                    updated_at = excluded.updated_at
            """, (
                market_data.get('id'),
                market_data.get('question'),
                market_data.get('slug'),
                market_data.get('category'),
                market_data.get('active'),
                market_data.get('closed'),
                market_data.get('endDate'),
                json.dumps(market_data.get('outcomes', [])),
                json.dumps(market_data.get('outcomePrices', {})),
                market_data.get('liquidity'),
                market_data.get('volume'),
                market_data.get('volume24hr'),
                datetime.now().isoformat()
            ))
        
        self.conn.commit()
        logger.info(f"Bulk upserted {len(markets)} markets")
        
    # ===== Watchlist Methods =====
    
    def add_to_watchlist(self, market_id: str):
        """
        Add a market to watchlist.
        
        Args:
            market_id: Market identifier
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO watchlist (market_id) 
            VALUES (?)
        """, (market_id,))
        self.conn.commit()
        
    def remove_from_watchlist(self, market_id: str):
        """
        Remove a market from watchlist.
        
        Args:
            market_id: Market identifier
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM watchlist WHERE market_id = ?
        """, (market_id,))
        self.conn.commit()
        
    def get_watchlist(self) -> List[Dict]:
        """
        Get all markets in watchlist.
        
        Returns:
            List of market dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT m.* FROM markets m
            INNER JOIN watchlist w ON m.id = w.market_id
            ORDER BY w.added_at DESC
        """)
        
        return [self._parse_market_row(row) for row in cursor.fetchall()]
        
    # ===== Helper Methods =====
    
    def _parse_market_row(self, row: sqlite3.Row) -> Dict:
        """
        Parse a market row into a dictionary.
        
        Args:
            row: SQLite row object
            
        Returns:
            Market data dictionary
        """
        market = dict(row)
        
        # Parse JSON fields
        if market.get('outcomes'):
            market['outcomes'] = json.loads(market['outcomes'])
        if market.get('outcome_prices'):
            market['outcome_prices'] = json.loads(market['outcome_prices'])
            
        return market
        
    def cleanup_old_data(self, days: int = 30):
        """
        Remove old data to keep database size manageable.
        
        Args:
            days: Number of days of data to keep
        """
        cursor = self.conn.cursor()
        
        # Delete old trades
        cursor.execute("""
            DELETE FROM trades 
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        """, (days,))
        
        # Delete old price history
        cursor.execute("""
            DELETE FROM price_history 
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        """, (days,))
        
        self.conn.commit()
        logger.info(f"Cleaned up data older than {days} days")


# Global database instance
_db_instance: Optional[Database] = None


def get_database(db_path: str = "data/polymarket.db") -> Database:
    """
    Get or create the global database instance.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance


if __name__ == "__main__":
    # Test the database
    db = Database("data/test.db")
    
    print("Testing database operations...")
    
    # Test market insertion
    test_market = {
        'id': 'test-123',
        'question': 'Will this test work?',
        'slug': 'test-market',
        'category': 'Testing',
        'active': True,
        'closed': False,
        'outcomes': ['Yes', 'No'],
        'outcomePrices': {'Yes': 0.6, 'No': 0.4},
        'liquidity': 10000,
        'volume': 50000,
        'volume24hr': 5000
    }
    
    db.upsert_market(test_market)
    print("✓ Market inserted")
    
    # Test retrieval
    retrieved = db.get_market('test-123')
    print(f"✓ Market retrieved: {retrieved['question']}")
    
    # Test trade insertion
    test_trade = {
        'market': 'test-123',
        'proxyWallet': '0xtest123',
        'side': 'BUY',
        'outcome': 'Yes',
        'price': 0.6,
        'size': 100,
        'timestamp': datetime.now().isoformat()
    }
    
    db.insert_trade(test_trade)
    print("✓ Trade inserted")
    
    # Test watchlist
    db.add_to_watchlist('test-123')
    watchlist = db.get_watchlist()
    print(f"✓ Watchlist: {len(watchlist)} markets")
    
    db.disconnect()
    print("\n✓ All database tests passed!")
