"""
Utility functions for the Polymarket Dashboard.
"""

from typing import Dict, List, Any
from datetime import datetime, timedelta
import json


def format_address(address: str, length: int = 10) -> str:
    """
    Format a wallet address for display.
    
    Args:
        address: Full wallet address
        length: Number of characters to show on each end
        
    Returns:
        Formatted address string
    """
    if len(address) <= length * 2:
        return address
    return f"{address[:length]}...{address[-length:]}"


def format_currency(value: float, decimals: int = 2) -> str:
    """
    Format a number as currency.
    
    Args:
        value: Numeric value
        decimals: Number of decimal places
        
    Returns:
        Formatted currency string
    """
    return f"${value:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format a number as percentage.
    
    Args:
        value: Numeric value (0-1 for decimal, >1 for percentage)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if value <= 1:
        value = value * 100
    return f"{value:.{decimals}f}%"


def format_timestamp(timestamp: str or datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format a timestamp for display.
    
    Args:
        timestamp: ISO timestamp string or datetime object
        format_str: strftime format string
        
    Returns:
        Formatted timestamp string
    """
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return timestamp.strftime(format_str)


def time_ago(timestamp: str or datetime) -> str:
    """
    Get human-readable time difference.
    
    Args:
        timestamp: ISO timestamp string or datetime object
        
    Returns:
        Human-readable time string (e.g., "5 minutes ago")
    """
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    
    diff = datetime.now() - timestamp
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def calculate_price_change(old_price: float, new_price: float) -> Dict[str, Any]:
    """
    Calculate price change statistics.
    
    Args:
        old_price: Previous price
        new_price: Current price
        
    Returns:
        Dictionary with change statistics
    """
    if old_price == 0:
        return {
            'change': 0,
            'change_percent': 0,
            'direction': 'neutral'
        }
    
    change = new_price - old_price
    change_percent = (change / old_price) * 100
    
    return {
        'change': change,
        'change_percent': change_percent,
        'direction': 'up' if change > 0 else 'down' if change < 0 else 'neutral'
    }


def parse_outcome_prices(outcome_prices: Dict or str) -> Dict[str, float]:
    """
    Parse outcome prices from various formats.
    
    Args:
        outcome_prices: Dictionary or JSON string of outcome prices
        
    Returns:
        Dictionary of outcome -> price
    """
    if isinstance(outcome_prices, str):
        outcome_prices = json.loads(outcome_prices)
    
    # Ensure all values are floats
    return {k: float(v) for k, v in outcome_prices.items()}


def calculate_implied_probability(price: float) -> float:
    """
    Calculate implied probability from price.
    
    Args:
        price: Market price (0-1)
        
    Returns:
        Implied probability (0-100)
    """
    return price * 100


def get_color_for_change(change_percent: float) -> str:
    """
    Get color code for price change.
    
    Args:
        change_percent: Percentage change
        
    Returns:
        Color name or hex code
    """
    if change_percent > 0:
        return "green"
    elif change_percent < 0:
        return "red"
    else:
        return "gray"


def validate_market_data(market: Dict) -> bool:
    """
    Validate market data has required fields.
    
    Args:
        market: Market data dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['id', 'question']
    return all(field in market for field in required_fields)


def aggregate_volume_by_period(
    trades: List[Dict],
    period: str = "hour"
) -> Dict[str, float]:
    """
    Aggregate trade volume by time period.
    
    Args:
        trades: List of trade dictionaries
        period: Time period ('hour', 'day', 'week')
        
    Returns:
        Dictionary of period -> volume
    """
    volumes = {}
    
    for trade in trades:
        timestamp = datetime.fromisoformat(
            trade.get('timestamp', '').replace('Z', '+00:00')
        )
        
        if period == "hour":
            key = timestamp.strftime('%Y-%m-%d %H:00')
        elif period == "day":
            key = timestamp.strftime('%Y-%m-%d')
        elif period == "week":
            key = timestamp.strftime('%Y-W%W')
        else:
            key = timestamp.strftime('%Y-%m-%d')
        
        price = float(trade.get('price', 0))
        size = float(trade.get('size', 0))
        volume = price * size
        
        volumes[key] = volumes.get(key, 0) + volume
    
    return volumes


def get_market_status_emoji(market: Dict) -> str:
    """
    Get emoji for market status.
    
    Args:
        market: Market data dictionary
        
    Returns:
        Emoji string
    """
    if market.get('closed'):
        return "🔒"
    elif market.get('active'):
        return "🟢"
    else:
        return "⚫"


def format_large_number(number: float) -> str:
    """
    Format large numbers with K/M/B suffixes.
    
    Args:
        number: Number to format
        
    Returns:
        Formatted string
    """
    if number >= 1_000_000_000:
        return f"${number/1_000_000_000:.1f}B"
    elif number >= 1_000_000:
        return f"${number/1_000_000:.1f}M"
    elif number >= 1_000:
        return f"${number/1_000:.1f}K"
    else:
        return f"${number:.2f}"
