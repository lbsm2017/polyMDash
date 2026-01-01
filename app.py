"""
Polymarket Dashboard - Conviction-Weighted Tracker
Surfaces high-conviction trades from tracked users with consensus signals.
"""

import streamlit as st
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional, Tuple
import logging
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="Polymarket Conviction Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import modules
from clients.gamma_client import GammaClient
from clients.trades_client import TradesClient
from clients.api_pool import fetch_all_data, APIPool
from clients.leaderboard_client import LeaderboardClient
from utils.user_tracker import get_user_tracker
from algorithms.conviction_scorer import ConvictionScorer

# Initialize
tracker = get_user_tracker()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 1.4rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.2rem;
        margin-top: 0;
    }
    .compact-metric {
        text-align: center;
        padding: 0.3rem;
        background: #f8f9fa;
        border-radius: 0.3rem;
        border-left: 3px solid #3498db;
    }
    .metric-value {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 0;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #7f8c8d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 0;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.7rem;
    }
    .market-row {
        padding: 0.25rem 0;
        border-bottom: 1px solid #ecf0f1;
        line-height: 1.2;
    }
    .market-row:hover {
        background-color: #f8f9fa;
    }
    h3 {
        margin-top: 0.3rem;
        margin-bottom: 0.2rem;
    }
    .stMarkdown {
        margin-bottom: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Sidebar
    st.sidebar.title("PolyMarket Dashboard")
    st.sidebar.markdown("Advanced Trading Analytics")
    st.sidebar.markdown("---")
    
    # Strategy Selection - FIRST
    st.sidebar.markdown("**Strategy**")
    strategy = st.sidebar.radio(
        "Select Strategy:",
        ["Conviction Tracker", "Momentum Hunter", "Arbitrage Scanner"],
        index=1,
        help="Choose trading strategy"
    )
    
    # Route to appropriate strategy
    if strategy == "Momentum Hunter":
        render_pullback_hunter()
        return
    elif strategy == "Arbitrage Scanner":
        render_arbitrage_scanner()
        return
    
    # Continue with Conviction Tracker
    st.sidebar.markdown("Track high-conviction moves from top traders")
    st.sidebar.markdown("---")
    
    # Trader source selection
    st.sidebar.markdown("**📊 Trader Source**")
    trader_source = st.sidebar.radio(
        "Select source:",
        ["👤 User List", "🏆 Leaderboard"],
        index=0,
        help="Choose between your custom list or Polymarket's monthly profit leaderboard"
    )
    
    # Leaderboard filters (only show when Leaderboard is selected)
    category = "overall"
    period = "monthly"
    if trader_source == "🏆 Leaderboard":
        category_map = {
            "All Categories": "overall",
            "Politics": "politics",
            "Sports": "sports",
            "Crypto": "crypto",
            "Finance": "finance",
            "Culture": "culture",
            "Mentions": "mentions",
            "Weather": "weather",
            "Economics": "economics",
            "Tech": "tech"
        }
        
        selected_category = st.sidebar.selectbox(
            "Category",
            options=list(category_map.keys()),
            index=0,
            help="Filter leaderboard by market category"
        )
        category = category_map[selected_category]
        
        period_map = {
            "Today": "daily",
            "Weekly": "weekly",
            "Monthly": "monthly",
            "All": "all"
        }
        
        selected_period = st.sidebar.radio(
            "Time Period",
            options=list(period_map.keys()),
            index=2,  # Default to Monthly
            horizontal=True,
            help="Select time period for leaderboard rankings"
        )
        period = period_map[selected_period]
    
    st.sidebar.markdown("---")
    
    # Tracked users display with edit capabilities
    tracked_users = tracker.get_all_users()
    st.sidebar.markdown(f"### 👥 Tracked Traders ({len(tracked_users)})")
    
    # Add custom CSS for compact trader list
    st.sidebar.markdown("""
    <style>
        .trader-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.15rem 0.2rem;
            margin: 0.1rem 0;
            border-bottom: 1px solid #eee;
        }
        .trader-row:hover {
            background-color: #f5f5f5;
        }
        .trader-name {
            font-size: 0.8rem;
            font-weight: 500;
            color: #333;
            flex: 1;
        }
        .trader-remove {
            font-size: 0.7rem;
            color: #666;
            cursor: pointer;
            padding: 0.1rem 0.3rem;
            border: none;
            background: transparent;
            text-align: center;
        }
        .trader-remove:hover {
            color: #000;
            background-color: #e0e0e0;
            border-radius: 3px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Display each user with remove button in compact format
    for user in tracked_users:
        col1, col2 = st.sidebar.columns([6, 1])
        with col1:
            st.markdown(f"<div style='font-size: 0.8rem; font-weight: 500; color: #333; line-height: 1.2; padding: 0.2rem 0;'>{user['name']}</div>", unsafe_allow_html=True)
        with col2:
            if st.button("×", key=f"remove_{user['wallet']}", help="Remove", type="secondary"):
                tracker.remove_user(user['wallet'])
                st.cache_data.clear()
                st.rerun()
    
    # Add new user section
    st.sidebar.markdown("---")
    st.sidebar.markdown("**➕ Add New Trader**")
    
    with st.sidebar.form("add_user_form", clear_on_submit=True):
        new_name = st.text_input("Name", placeholder="e.g., TraderName")
        new_address = st.text_input("Wallet Address", placeholder="0x...")
        submit = st.form_submit_button("Add Trader", use_container_width=True)
        
        if submit:
            if new_name and new_address:
                if tracker.add_user(new_name, new_address):
                    st.success(f"Added {new_name}!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Wallet already tracked!")
            else:
                st.warning("Please fill in both fields")
    
    st.sidebar.markdown("---")
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False)
    
    if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Main content
    display_conviction_dashboard(trader_source, category, period)
    
    # Auto-refresh logic
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_leaderboard_traders(category: str = "overall", period: str = "monthly", limit: int = 50) -> List[Dict[str, str]]:
    """Fetch traders from Polymarket leaderboard."""
    try:
        async def fetch():
            client = LeaderboardClient()
            return await client.fetch_leaderboard(category=category, period=period, limit=limit)
        
        return asyncio.run(fetch())
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return []


def display_conviction_dashboard(trader_source: str = "👤 User List", category: str = "overall", period: str = "monthly"):
    """Main dashboard view showing conviction-weighted markets."""
    
    st.markdown('<div class="main-header">📡 Traders Scanner</div>', unsafe_allow_html=True)
    
    # Determine which traders to use
    if trader_source == "🏆 Leaderboard":
        # Fetch from leaderboard
        with st.spinner("Fetching leaderboard traders..."):
            leaderboard_data = fetch_leaderboard_traders(category=category, period=period, limit=50)
            
        if not leaderboard_data:
            st.error("❌ Failed to fetch leaderboard. Falling back to user list.")
            tracked_users = tracker.get_all_users()
            wallet_addresses = tracker.get_wallet_addresses()
            source_label = "User List (fallback)"
        else:
            wallet_addresses = [t['wallet'] for t in leaderboard_data]
            tracked_users = {t['wallet']: t['name'] for t in leaderboard_data}
            source_label = "Leaderboard"
            
        st.info(f"📊 Using: **{source_label}** ({len(wallet_addresses)} traders)")
    else:
        # Use custom user list
        tracked_users = tracker.get_all_users()
        if not tracked_users:
            st.warning("⚠️ No tracked users! Add traders to `tracked_users.csv`")
            return
        
        wallet_addresses = tracker.get_wallet_addresses()
        st.info(f"📊 Using: **User List** ({len(wallet_addresses)} traders)")
    
    logger.info(f"Tracking {len(wallet_addresses)} wallets: {wallet_addresses[:3]}...")
    
    # Phase 1: Load trades with high-performance pool
    with st.spinner("Loading trader activity..."):
        # First fetch trades to get market slugs
        trades, _ = fetch_all_data(wallet_addresses, [], cutoff_minutes=1440)
        
        logger.info(f"Loaded {len(trades)} trades from API")
        
        if not trades:
            st.info("No recent activity from tracked users in the last 24 hours.")
            return
    
    # Phase 2: Fetch all market data in parallel (need this for expiration urgency)
    with st.spinner("Fetching current prices..."):
        market_slugs = list(set([t.get('slug', '') for t in trades if t.get('slug')]))
        _, batch_market_data = fetch_all_data([], market_slugs, cutoff_minutes=1440)
        
        # Score markets WITH market data for expiration urgency
        scorer = ConvictionScorer(wallet_addresses)
        scored_markets = scorer.score_markets(trades, market_data_dict=batch_market_data)
    
    # Filter out closed markets and markets without tracked user positions
    open_markets = [
        market for market in scored_markets 
        if batch_market_data.get(market['slug']) is not None
        and (len(market['bullish_users']) > 0 or len(market['bearish_users']) > 0)
    ]
    
    if not open_markets:
        st.info("No open markets found with tracked user positions.")
        return
    
    # Sorting controls
    col_sort, col_spacer = st.columns([2, 6])
    with col_sort:
        sort_by = st.selectbox(
            "Sort by:",
            ["Recent Activity", "Conviction", "Expiration", "Volume ($)", "Number of Trades"],
            key="market_sort"
        )
    
    # Apply sorting
    if sort_by == "Conviction":
        open_markets.sort(key=lambda x: x['conviction_score'], reverse=True)
    elif sort_by == "Expiration":
        # Sort by expiration time (soonest first)
        def get_expiration_minutes(market):
            market_data = batch_market_data.get(market['slug'])
            if market_data:
                end_date_iso = market_data.get('end_date_iso', '')
                if end_date_iso:
                    _, minutes = get_time_until_expiration(end_date_iso)
                    return minutes
            return float('inf')  # Put markets without expiration data at the end
        open_markets.sort(key=get_expiration_minutes)
    elif sort_by == "Volume ($)":
        open_markets.sort(key=lambda x: x['bullish_volume'] + x['bearish_volume'], reverse=True)
    elif sort_by == "Number of Trades":
        open_markets.sort(key=lambda x: x['total_trades'], reverse=True)
    # else: Recent Activity is already sorted by weighted_avg_time from ConvictionScorer
    
    # Table header - only show for User List mode
    if trader_source == "👤 User List":
        header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([3.5, 1, 1, 1.5, 1.5])
        with header_col1:
            st.markdown("**Market**")
        with header_col2:
            st.markdown("**Conviction**")
        with header_col3:
            st.markdown("**Expire**")
        with header_col4:
            st.markdown("**📈 YES Position**")
        with header_col5:
            st.markdown("**📉 NO Position**")
        st.markdown('<div style="border-bottom: 2px solid #3498db; margin: 0.3rem 0 0.5rem 0;"></div>', unsafe_allow_html=True)
    
    # Store tracked_users in session state for use in display functions
    if 'user_lookup' not in st.session_state or st.session_state.get('trader_source') != trader_source:
        st.session_state.user_lookup = tracked_users if isinstance(tracked_users, dict) else {u['wallet']: u['name'] for u in tracked_users} if isinstance(tracked_users, list) else tracker.get_all_users()
        st.session_state.trader_source = trader_source
    
    for market in open_markets:
        display_market_card(market, batch_market_data)


def format_time_elapsed(minutes: int) -> str:
    """
    Format elapsed time in a human-readable format.
    
    - < 60m: Xm
    - 60m - 24h: XhYm
    - 24h - 30d: XdYh
    - > 30d: XMYd
    """
    if minutes < 60:
        return f"{minutes}m"
    elif minutes < 1440:  # Less than 24 hours
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h{mins}m"
    elif minutes < 43200:  # Less than 30 days
        days = minutes // 1440
        hours = (minutes % 1440) // 60
        return f"{days}d{hours}h"
    else:  # 30 days or more
        months = minutes // 43200
        days = (minutes % 43200) // 1440
        return f"{months}M{days}d"


def get_time_until_expiration(end_date_iso: str) -> tuple:
    """
    Calculate time until market expiration.
    
    Args:
        end_date_iso: ISO format date string
        
    Returns:
        Tuple of (formatted_datetime, minutes_remaining)
    """
    from datetime import datetime, timezone
    
    if not end_date_iso:
        return ("N/A", 0)
    
    try:
        # Parse ISO date with timezone support
        end_date = datetime.fromisoformat(end_date_iso.replace('Z', '+00:00'))
        
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        
        # Calculate minutes remaining
        time_delta = end_date - now
        minutes_remaining = int(time_delta.total_seconds() / 60)
        
        # Format datetime as yyyy-mm-dd hh:mm:ss
        formatted_date = end_date.strftime('%Y-%m-%d %H:%M:%S')
        
        return (formatted_date, max(0, minutes_remaining))
    except Exception as e:
        logger.warning(f"Failed to parse expiration date '{end_date_iso}': {e}")
        return ("N/A", 0)


def get_user_positions(trades: List[Dict], is_yes_side: bool) -> List[tuple]:
    """
    Calculate user positions (average price and total size) for one side.
    
    Args:
        trades: List of all trades for the market
        is_yes_side: True for YES side, False for NO side
        
    Returns:
        List of tuples: (user_name, avg_price, total_size, minutes_ago)
    """
    from collections import defaultdict
    from datetime import datetime
    
    user_positions = defaultdict(lambda: {'total_volume': 0, 'total_size': 0, 'weighted_sum': 0, 'last_timestamp': 0})
    
    for trade in trades:
        side = trade.get('side', '').upper()
        outcome = trade.get('outcome', '').upper()
        wallet = trade.get('proxyWallet', '').lower()
        
        is_bullish = (side == 'BUY' and 'YES' in outcome) or (side == 'SELL' and 'NO' in outcome)
        is_bearish = (side == 'BUY' and 'NO' in outcome) or (side == 'SELL' and 'YES' in outcome)
        
        if (is_yes_side and is_bullish) or (not is_yes_side and is_bearish):
            price = float(trade.get('price', 0))
            size = float(trade.get('size', 0))
            volume = price * size
            timestamp = trade.get('timestamp', 0)
            
            user_positions[wallet]['weighted_sum'] += price * volume
            user_positions[wallet]['total_volume'] += volume
            user_positions[wallet]['total_size'] += size
            # Track most recent trade for this user
            if timestamp > user_positions[wallet]['last_timestamp']:
                user_positions[wallet]['last_timestamp'] = timestamp
    
    # Convert to list with names and calculated averages
    result = []
    current_time = datetime.now().timestamp()
    user_lookup = st.session_state.get('user_lookup', {})
    
    for wallet, data in user_positions.items():
        # Get user name from session state or fallback to tracker
        if isinstance(user_lookup, dict):
            user_name = user_lookup.get(wallet, wallet[:8])
        else:
            user_name = tracker.get_user_name(wallet)
        
        avg_price = data['weighted_sum'] / data['total_volume'] if data['total_volume'] > 0 else 0
        total_size = data['total_size']
        # Calculate minutes since last trade
        minutes_ago = int((current_time - data['last_timestamp']) / 60) if data['last_timestamp'] > 0 else 0
        result.append((user_name, avg_price, total_size, minutes_ago))
    
    # Sort by total size (largest positions first)
    result.sort(key=lambda x: x[2], reverse=True)
    return result


def calculate_side_prices(trades: List[Dict], is_yes_side: bool) -> Tuple[float, float]:
    """
    Calculate weighted average entry price and last execution price for one side.
    
    Args:
        trades: List of all trades for the market
        is_yes_side: True for YES side, False for NO side
        
    Returns:
        Tuple of (weighted_avg_entry_price, last_execution_price)
    """
    # Filter trades for this side
    relevant_trades = []
    for trade in trades:
        side = trade.get('side', '').upper()
        outcome = trade.get('outcome', '').upper()
        
        is_bullish = (side == 'BUY' and 'YES' in outcome) or (side == 'SELL' and 'NO' in outcome)
        is_bearish = (side == 'BUY' and 'NO' in outcome) or (side == 'SELL' and 'YES' in outcome)
        
        if (is_yes_side and is_bullish) or (not is_yes_side and is_bearish):
            relevant_trades.append(trade)
    
    if not relevant_trades:
        return 0.0, 0.0
    
    # Calculate weighted average entry price
    total_volume = 0
    weighted_sum = 0
    
    for trade in relevant_trades:
        price = float(trade.get('price', 0))
        size = float(trade.get('size', 0))
        volume = price * size
        
        weighted_sum += price * volume
        total_volume += volume
    
    avg_entry = weighted_sum / total_volume if total_volume > 0 else 0
    
    # Get last execution price (most recent trade)
    sorted_trades = sorted(relevant_trades, key=lambda t: t.get('timestamp', 0), reverse=True)
    last_price = float(sorted_trades[0].get('price', 0)) if sorted_trades else 0
    
    return avg_entry, last_price



def display_market_card(market: Dict, batch_market_data: Dict[str, Optional[Dict]]):
    """Display a single market in compact tabular format."""
    
    direction = market['direction']
    score = market['conviction_score']
    slug = market['slug']
    
    # Get conviction level
    scorer = ConvictionScorer([])
    level_name, emoji = scorer.get_conviction_level(score)
    
    # Direction styling
    direction_emoji = "📈" if direction == "BULLISH" else "📉"
    direction_color = "#38ef7d" if direction == "BULLISH" else "#f45c43"
    
    # Get current market prices from batch data
    market_data = batch_market_data.get(slug)
    yes_price = market_data.get('yes_price', 0.5) if market_data else 0.5
    no_price = market_data.get('no_price', 0.5) if market_data else 0.5
    
    # Create market URL - Polymarket uses /market/ path with slug
    market_url = f"https://polymarket.com/market/{slug}"
    
    # Consensus users
    user_lookup = st.session_state.get('user_lookup', {})
    if isinstance(user_lookup, dict):
        user_names = [user_lookup.get(w, w[:8]) for w in market['consensus_users'][:3]]
    else:
        user_names = [tracker.get_user_name(w) for w in market['consensus_users'][:3]]
    users_display = ", ".join(user_names)
    if len(market['consensus_users']) > 3:
        users_display += f" +{len(market['consensus_users']) - 3}"
    
    # Count YES and NO positions
    yes_traders = len(market['bullish_users'])
    no_traders = len(market['bearish_users'])
    
    # Calculate prices for each side
    yes_avg, yes_last = calculate_side_prices(market['trades'], is_yes_side=True)
    no_avg, no_last = calculate_side_prices(market['trades'], is_yes_side=False)
    
    # Create compact row with container
    st.markdown('<div class="market-row">', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns([3.5, 1, 1, 1.5, 1.5])
    
    with col1:
        st.markdown(f"**[{slug[:80]}]({market_url})**")
        # Display user positions for YES side
        yes_positions = get_user_positions(market['trades'], is_yes_side=True)
        no_positions = get_user_positions(market['trades'], is_yes_side=False)
        
        # Build user position display with one line per user
        positions_html = '<div style="font-size: 0.75rem; line-height: 1.4; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif; color: #5a6c7d;">'
        
        if yes_positions:
            for name, price, size, minutes_ago in yes_positions[:5]:  # Show up to 5 users
                time_str = format_time_elapsed(minutes_ago)
                time_color = "#27ae60" if minutes_ago < 60 else "#95a5a6" if minutes_ago < 360 else "#7f8c8d"
                positions_html += f'<div style="margin: 0.1rem 0;"><span style="color: {time_color}; font-weight: 500;">[{time_str}]</span> 🟢 <strong style="color: #2c3e50;">{name}</strong> · ${size:,.0f} @ {price:.1%}</div>'
        
        if no_positions:
            for name, price, size, minutes_ago in no_positions[:5]:  # Show up to 5 users
                time_str = format_time_elapsed(minutes_ago)
                time_color = "#e74c3c" if minutes_ago < 60 else "#95a5a6" if minutes_ago < 360 else "#7f8c8d"
                positions_html += f'<div style="margin: 0.1rem 0;"><span style="color: {time_color}; font-weight: 500;">[{time_str}]</span> 🔴 <strong style="color: #2c3e50;">{name}</strong> · ${size:,.0f} @ {price:.1%}</div>'
        
        positions_html += '</div>'
        st.markdown(positions_html, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<span style='font-size: 0.85rem;'><strong>{level_name}</strong></span>", unsafe_allow_html=True)
        st.caption(f"Score: {score:.1f}")
    
    with col3:
        # Calculate and display expiration time
        end_date_iso = market_data.get('end_date_iso', '') if market_data else ''
        exp_date, exp_minutes = get_time_until_expiration(end_date_iso)
        exp_time_str = format_time_elapsed(exp_minutes)
        exp_color = "#e74c3c" if exp_minutes < 60 else "#7f8c8d"
        st.markdown(f"""
        <div style='text-align: center; padding-top: 0.3rem;'>
            <div style='font-size: 0.7rem; color: {exp_color}; font-weight: 500;'>{exp_date}</div>
            <div style='color: {exp_color}; font-weight: 600; font-size: 0.85rem;'>[{exp_time_str}]</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # YES position
        yes_bg = "rgba(56, 239, 125, 0.1)"
        st.markdown(f"""
        <div style="background: {yes_bg}; padding: 0.3rem; border-radius: 0.3rem;">
            <div style="text-align: center; margin-bottom: 0.3rem;">
                <div style="font-size: 0.6rem; color: #7f8c8d; margin-bottom: 0.05rem; line-height: 1;">CURRENT</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #38ef7d; line-height: 1;">{yes_price:.1%}</div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; line-height: 1.1;">
                <span style="font-weight: 600;">👥 {yes_traders}</span>
                <span style="color: #7f8c8d;">${market['bullish_volume']:,.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        # NO position
        no_bg = "rgba(244, 92, 67, 0.1)"
        st.markdown(f"""
        <div style="background: {no_bg}; padding: 0.3rem; border-radius: 0.3rem;">
            <div style="text-align: center; margin-bottom: 0.3rem;">
                <div style="font-size: 0.6rem; color: #7f8c8d; margin-bottom: 0.05rem; line-height: 1;">CURRENT</div>
                <div style="font-size: 1.3rem; font-weight: 700; color: #f45c43; line-height: 1;">{no_price:.1%}</div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.85rem; line-height: 1.1;">
                <span style="font-weight: 600;">👥 {no_traders}</span>
                <span style="color: #7f8c8d;">${market['bearish_volume']:,.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_trade_row(trade: Dict):
    """Display a single trade in compact format."""
    side = trade.get('side', '')
    outcome = trade.get('outcome', '')
    price = float(trade.get('price', 0))
    size = float(trade.get('size', 0))
    volume = price * size
    wallet = trade.get('proxyWallet', '')
    
    # Get user name from session state or fallback to tracker
    user_lookup = st.session_state.get('user_lookup', {})
    if isinstance(user_lookup, dict):
        user_name = user_lookup.get(wallet, wallet[:8])
    else:
        user_name = tracker.get_user_name(wallet)
    
    timestamp = trade.get('timestamp', 0)
    
    side_emoji = "🟢" if side == "BUY" else "🔴"
    time_str = format_time_ago(timestamp) if timestamp else ""
    
    st.caption(
        f"{side_emoji} **{side} {outcome}** · "
        f"${volume:.2f} @ {price:.2%} · "
        f"👤 {user_name} · ⏱️ {time_str}"
    )


@st.cache_data(ttl=30)
def load_tracked_trades(time_window: str) -> List[Dict]:
    """Load trades for all tracked users in parallel."""
    
    minutes = parse_time_window(time_window)
    cutoff = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
    wallet_addresses = tracker.get_wallet_addresses()
    
    if not wallet_addresses:
        return []
    
    try:
        async def fetch_all():
            async with TradesClient() as client:
                # Fetch all users' trades in parallel
                tasks = [
                    client.get_user_trades(wallet, limit=200) 
                    for wallet in wallet_addresses
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Flatten and filter trades
                all_trades = []
                for trades in results:
                    if isinstance(trades, list):
                        for trade in trades:
                            if isinstance(trade, dict) and trade.get('timestamp', 0) >= cutoff:
                                all_trades.append(trade)
                    elif isinstance(trades, Exception):
                        logger.warning(f"Error fetching trades: {trades}")
                
                return all_trades
        
        return asyncio.run(fetch_all())
    except Exception as e:
        logger.error(f"Error loading trades: {e}")
        return []


@st.cache_data(ttl=60)
def get_market_data(slug: str) -> Optional[Dict]:
    """Fetch current market prices from Gamma API."""
    try:
        async def fetch():
            async with GammaClient() as client:
                market = await client.get_market_by_slug(slug)
                if market:
                    # Check if market is closed
                    is_closed = market.get('closed', False)
                    is_active = market.get('active', True)
                    
                    # Filter out closed/inactive markets
                    if is_closed or not is_active:
                        logger.debug(f"Market {slug} is closed or inactive, skipping")
                        return None
                    
                    prices = market.get('outcomePrices', [0.5, 0.5])
                    if isinstance(prices, str):
                        import json
                        prices = json.loads(prices)
                    
                    # For grouped markets, prefer the event's end date over the market's end date
                    end_date = market.get('endDate', '')
                    events = market.get('events', [])
                    if events and isinstance(events, list) and len(events) > 0:
                        event_end_date = events[0].get('endDate', '')
                        if event_end_date:
                            end_date = event_end_date
                    
                    return {
                        'yes_price': float(prices[0]) if prices else 0.5,
                        'no_price': float(prices[1]) if len(prices) > 1 else 0.5,
                        'volume': market.get('volume', 0),
                        'liquidity': market.get('liquidity', 0),
                        'active': is_active,
                        'closed': is_closed,
                        'endDate': end_date,
                    }
            return None
        
        return asyncio.run(fetch())
    except Exception as e:
        logger.debug(f"Could not fetch market data for {slug}: {e}")
        return None


@st.cache_data(ttl=60)
def get_batch_market_data(slugs: List[str]) -> Dict[str, Optional[Dict]]:
    """Fetch market data for multiple markets in parallel."""
    if not slugs:
        return {}
    
    try:
        async def fetch_all():
            async with GammaClient() as client:
                # Fetch all markets in parallel
                tasks = [client.get_market_by_slug(slug) for slug in slugs]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                market_data = {}
                for slug, market in zip(slugs, results):
                    if isinstance(market, dict):
                        # Check if market is closed
                        is_closed = market.get('closed', False)
                        is_active = market.get('active', True)
                        
                        # Filter out closed/inactive markets
                        if is_closed or not is_active:
                            market_data[slug] = None
                            continue
                        
                        prices = market.get('outcomePrices', [0.5, 0.5])
                        if isinstance(prices, str):
                            import json
                            prices = json.loads(prices)
                        
                        # For grouped markets, prefer the event's end date over the market's end date
                        end_date = market.get('endDate', '')
                        events = market.get('events', [])
                        if events and isinstance(events, list) and len(events) > 0:
                            event_end_date = events[0].get('endDate', '')
                            if event_end_date:
                                end_date = event_end_date
                        
                        market_data[slug] = {
                            'yes_price': float(prices[0]) if prices else 0.5,
                            'no_price': float(prices[1]) if len(prices) > 1 else 0.5,
                            'volume': market.get('volume', 0),
                            'liquidity': market.get('liquidity', 0),
                            'active': is_active,
                            'closed': is_closed,
                            'endDate': end_date,
                        }
                    else:
                        market_data[slug] = None
                
                return market_data
        
        return asyncio.run(fetch_all())
    except Exception as e:
        logger.error(f"Error fetching batch market data: {e}")
        return {slug: None for slug in slugs}


def parse_time_window(window: str) -> int:
    """Parse time window string to minutes."""
    mappings = {
        "Last 1 hour": 60,
        "Last 6 hours": 360,
        "Last 24 hours": 1440,
        "Last 3 days": 4320,
    }
    return mappings.get(window, 360)


def format_time_ago(timestamp: int) -> str:
    """Format timestamp as human-readable time ago."""
    try:
        dt = datetime.fromtimestamp(timestamp)
        diff = datetime.now() - dt
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds >= 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds >= 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"
    except:
        return ""


# ============================================================================
# PULLBACK HUNTER STRATEGY
# ============================================================================

def calculate_composite_momentum(current_price: float, price_change: float) -> dict:
    """
    Calculate composite momentum score combining proportional and absolute moves.
    
    Uses log-scaled proportional momentum + absolute momentum with intelligent weighting.
    
    Examples:
    - 5% → 1% = strong proportional move (80% relative decline toward 0%)
    - 60% → 88% = strong absolute move (+28pp, significant swing)
    - 95% → 99% = moderate proportional but strong signal near extreme
    
    Returns dict with signal_strength on 0-1 scale.
    """
    # Calculate old price from current and change
    old_price = current_price - price_change
    
    # Clamp prices to valid range
    old_price = max(0.001, min(0.999, old_price))
    current_price_clamped = max(0.001, min(0.999, current_price))
    
    # 1. ABSOLUTE MOMENTUM: Simple difference
    absolute_momentum = abs(price_change)
    
    # 2. PROPORTIONAL MOMENTUM using log-odds (handles asymmetry near extremes)
    def log_odds(p):
        p = max(0.001, min(0.999, p))
        return math.log(p / (1 - p))
    
    old_log_odds = log_odds(old_price)
    new_log_odds = log_odds(current_price_clamped)
    log_odds_change = abs(new_log_odds - old_log_odds)
    
    # Normalize log-odds change to 0-1 scale
    # log-odds change of 1.5 = significant move
    # log-odds change of 3.0 = major move
    proportional_momentum = min(log_odds_change / 3.0, 1.0)
    
    # 3. DISTANCE-WEIGHTED ABSOLUTE: Moves near extremes matter more
    distance_to_center = abs(current_price_clamped - 0.5)
    extremity_multiplier = 1.0 + distance_to_center
    weighted_absolute = absolute_momentum * extremity_multiplier
    
    # 4. VELOCITY: Reward acceleration toward extremes
    moving_toward_extreme = (
        (current_price_clamped > 0.5 and price_change > 0) or
        (current_price_clamped < 0.5 and price_change < 0)
    )
    velocity_bonus = 1.2 if moving_toward_extreme else 0.8
    
    # 5. COMPOSITE SCORE
    raw_composite = (
        proportional_momentum * 0.35 +
        min(weighted_absolute * 2.0, 1.0) * 0.35 +
        min(absolute_momentum * 2.5, 1.0) * 0.30
    )
    composite = raw_composite * velocity_bonus
    signal_strength = min(composite, 1.0)
    
    return {
        'proportional': proportional_momentum,
        'absolute': absolute_momentum,
        'log_odds_change': log_odds_change,
        'weighted_absolute': weighted_absolute,
        'composite': composite,
        'signal_strength': signal_strength,
        'moving_toward_extreme': moving_toward_extreme
    }


def calculate_opportunity_score(
    current_prob: float,
    momentum: float,
    hours_to_expiry: float,
    volume: float,
    best_bid: float,
    best_ask: float,
    direction: str,
    one_day_change: float = 0,
    one_week_change: float = 0,
    annualized_yield: float = 0,
    charm: float = 0
) -> dict:
    """
    Multi-modal scoring function optimized for 2-5% distance, 7-10 day window sweet spot.
    
    Uses polynomial/sigmoid curves for smooth transitions instead of hard cutoffs.
    Penalizes deviations from optimal conditions proportionally.
    
    Core metrics:
    - Distance-Time fit (35%): Sweet spot at 2-5% distance, 7-10 days
    - APY (25%): Logarithmic scale
    - Volume (15%): Liquidity conviction
    - Spread Quality (10%): Execution efficiency
    - Momentum (10%): Directional strength
    - Charm (5%): Acceleration factor
    
    Returns dict with total_score (0-100), grade, and components.
    """
    
    # Calculate distance to target
    if direction == 'YES':
        distance_to_target = 1.0 - current_prob
    else:
        distance_to_target = current_prob
    
    days_to_expiry = hours_to_expiry / 24
    
    # =================================================================
    # 1. DISTANCE-TIME FIT SCORE (0-100) - 35% weight
    # Multi-modal function with sweet spot at 2-5% distance, 7-10 days
    # =================================================================
    
    # Distance component: Gaussian curve peaked at 3.5% (midpoint of 2-5%)
    optimal_distance = 0.035  # 3.5%
    distance_sigma = 0.015    # Controls width of optimal zone
    
    # Gaussian formula: exp(-((x - mu)^2) / (2 * sigma^2))
    distance_deviation = (distance_to_target - optimal_distance) ** 2
    distance_fitness = math.exp(-distance_deviation / (2 * distance_sigma ** 2))
    
    # Time component: Gaussian curve peaked at 8.5 days (midpoint of 7-10)
    optimal_days = 8.5
    time_sigma = 2.0  # Controls width of optimal zone
    
    time_deviation = (days_to_expiry - optimal_days) ** 2
    time_fitness = math.exp(-time_deviation / (2 * time_sigma ** 2))
    
    # Combined distance-time fit with interaction term
    # When both are optimal, score is maximized
    distance_time_fit = distance_fitness * time_fitness
    
    # Boost for being in the exact sweet spot (2-5% distance AND 7-10 days)
    in_sweet_spot = (0.02 <= distance_to_target <= 0.05) and (7 <= days_to_expiry <= 10)
    if in_sweet_spot:
        distance_time_fit = min(1.0, distance_time_fit * 1.3)
    
    # Polynomial penalty for extreme distances (too close to 0% or 100%)
    # Sigmoid function to smoothly penalize distances < 1% or > 20%
    if distance_to_target < 0.01:  # Very close to extreme
        extreme_penalty = 1.0 / (1.0 + math.exp(10 * (distance_to_target - 0.005)))
        distance_time_fit *= extreme_penalty
    elif distance_to_target > 0.20:  # Too far from extreme
        far_penalty = 1.0 / (1.0 + math.exp(-10 * (distance_to_target - 0.25)))
        distance_time_fit *= far_penalty
    
    distance_time_score = distance_time_fit * 100
    
    # =================================================================
    # 2. APY SCORE (0-100) - 25% weight
    # Logarithmic scale with smooth transitions
    # =================================================================
    apy_decimal = annualized_yield
    
    if apy_decimal <= 0:
        apy_score = 0
    elif apy_decimal < 0.50:  # <50% APY
        # Polynomial: x^0.7 for diminishing returns at low APY
        apy_score = (apy_decimal / 0.50) ** 0.7 * 20
    elif apy_decimal < 1.0:  # 50-100% APY
        apy_score = 20 + ((apy_decimal - 0.50) / 0.50) ** 0.8 * 20
    elif apy_decimal < 5.0:  # 100-500% APY
        log_progress = math.log10(apy_decimal) / math.log10(5.0)
        apy_score = 40 + log_progress * 30
    elif apy_decimal < 10.0:  # 500-1000% APY
        log_progress = (math.log10(apy_decimal) - math.log10(5.0)) / (math.log10(10.0) - math.log10(5.0))
        apy_score = 70 + log_progress * 20
    else:  # >1000% APY
        log_progress = min(1.0, (math.log10(apy_decimal) - math.log10(10.0)) / 1.0)
        apy_score = 85 + log_progress * 15
    
    apy_score = min(100, apy_score)
    
    # =================================================================
    # 3. VOLUME SCORE (0-100) - 15% weight
    # Smooth S-curve for liquidity assessment
    # =================================================================
    if volume <= 0:
        volume_score = 0
    else:
        # S-curve (sigmoid): 1 / (1 + exp(-k * (x - midpoint)))
        # Midpoint at 500k, inflection creates smooth transition
        log_volume = math.log10(max(volume, 1))
        
        # Sigmoid centered at log10(500k) = 5.7
        volume_midpoint = 5.7
        volume_steepness = 1.5
        
        sigmoid = 1.0 / (1.0 + math.exp(-volume_steepness * (log_volume - volume_midpoint)))
        volume_score = sigmoid * 100
        
        # Boost for very high volume (>2M)
        if volume > 2_000_000:
            volume_bonus = min(0.2, (volume - 2_000_000) / 10_000_000)
            volume_score = min(100, volume_score * (1.0 + volume_bonus))
    
    volume_score = min(100, volume_score)
    
    # =================================================================
    # 4. SPREAD QUALITY SCORE (0-100) - 10% weight
    # Polynomial curve rewarding tight spreads
    # =================================================================
    if best_bid is not None and best_ask is not None and best_ask > 0 and best_bid > 0:
        spread = best_ask - best_bid
        spread_pct = spread / best_ask
        
        # Inverse polynomial: tighter spread = higher score
        # Perfect spread (0%) = 100, 10% spread = ~0
        if spread_pct <= 0:
            spread_score = 100
        else:
            # Polynomial decay: (1 - (spread/0.10))^2 * 100
            normalized_spread = min(spread_pct / 0.10, 1.0)
            spread_score = ((1.0 - normalized_spread) ** 1.5) * 100
    else:
        spread_score = 30  # Default for missing spread data
    
    spread_score = max(0, min(100, spread_score))
    
    # =================================================================
    # 5. MOMENTUM SCORE (0-100) - 10% weight
    # With directional consistency bonus (polynomial)
    # =================================================================
    momentum_score = momentum * 100
    
    # Consistency bonus using polynomial multiplier
    short_term_aligned = (direction == 'YES' and one_day_change > 0) or (direction == 'NO' and one_day_change < 0)
    long_term_aligned = (direction == 'YES' and one_week_change > 0) or (direction == 'NO' and one_week_change < 0)
    
    # Track counter-trend risk for final penalty
    is_counter_trend = False
    
    if short_term_aligned and long_term_aligned:
        # Both aligned: stronger polynomial boost
        consistency_factor = 1.5  # Increased from 1.25
        momentum_score = min(100, momentum_score * consistency_factor)
    elif short_term_aligned or long_term_aligned:
        # One aligned: neutral baseline (no boost/penalty to momentum itself)
        consistency_factor = 1.0  # Changed from 1.1
        momentum_score = min(100, momentum_score * consistency_factor)
    else:
        # Neither aligned: stronger polynomial penalty + risk flag
        consistency_factor = 0.5  # Increased penalty from 0.65
        momentum_score *= consistency_factor
        is_counter_trend = True  # Flag for additional overall penalty
    
    momentum_score = min(100, momentum_score)
    
    # =================================================================
    # 6. CHARM SCORE (0-100) - 5% weight
    # Polynomial scaling for acceleration
    # =================================================================
    abs_charm = abs(charm)
    
    if abs_charm <= 0:
        charm_score = 0
    elif abs_charm < 2.0:  # <2pp/day
        # Quadratic growth for low charm
        charm_score = (abs_charm / 2.0) ** 2 * 40
    elif abs_charm < 5.0:  # 2-5pp/day
        charm_score = 40 + ((abs_charm - 2.0) / 3.0) ** 1.5 * 30
    elif abs_charm < 10.0:  # 5-10pp/day
        charm_score = 70 + ((abs_charm - 5.0) / 5.0) ** 1.2 * 20
    else:  # >10pp/day
        # Logarithmic for extreme charm (diminishing returns)
        log_charm = min(1.0, math.log10(abs_charm - 9) / 1.0)
        charm_score = 90 + log_charm * 10
    
    charm_score = min(100, charm_score)
    
    # =================================================================
    # 7. DYNAMIC WEIGHTING based on context
    # Smooth transitions instead of hard cutoffs
    # =================================================================
    w_distance_time = 0.35
    w_apy = 0.25
    w_volume = 0.15
    w_spread = 0.10
    w_momentum = 0.10
    w_charm = 0.05
    
    # Adjust weights based on time horizon (smooth sigmoid)
    if days_to_expiry < 3:  # Very short-term
        # Increase spread and charm importance
        shift = min(0.08, (3 - days_to_expiry) / 10)
        w_spread += shift / 2
        w_charm += shift / 2
        w_apy -= shift
    elif days_to_expiry > 14:  # Long-term
        # Increase volume importance
        shift = min(0.08, (days_to_expiry - 14) / 30)
        w_volume += shift
        w_distance_time -= shift
    
    # Adjust based on distance from sweet spot (polynomial)
    distance_from_sweet_spot = abs(distance_to_target - optimal_distance) / optimal_distance
    if distance_from_sweet_spot > 0.5:
        # Far from sweet spot: APY matters more
        shift = min(0.10, distance_from_sweet_spot * 0.15)
        w_apy += shift
        w_distance_time -= shift
    
    # =================================================================
    # 8. FINAL SCORE - Weighted combination
    # No hard penalties, all handled by smooth component scores
    # =================================================================
    raw_score = (
        distance_time_score * w_distance_time +
        apy_score * w_apy +
        volume_score * w_volume +
        spread_score * w_spread +
        momentum_score * w_momentum +
        charm_score * w_charm
    )
    
    # Apply counter-trend risk penalty if momentum is misaligned
    # This creates additional ~5% penalty beyond the momentum component reduction
    if is_counter_trend:
        risk_penalty = 0.95  # 5% overall reduction for counter-trend setups
    else:
        risk_penalty = 1.0
    
    final_score = min(100, max(0, raw_score * risk_penalty))
    
    # =================================================================
    # 9. GRADE based on final score
    # =================================================================
    if final_score >= 85:
        grade, grade_color = "A+", "#27ae60"
    elif final_score >= 75:
        grade, grade_color = "A", "#2ecc71"
    elif final_score >= 65:
        grade, grade_color = "B+", "#f1c40f"
    elif final_score >= 55:
        grade, grade_color = "B", "#f39c12"
    elif final_score >= 45:
        grade, grade_color = "C+", "#e67e22"
    elif final_score >= 35:
        grade, grade_color = "C", "#e74c3c"
    else:
        grade, grade_color = "D", "#c0392b"
    
    return {
        'total_score': final_score,
        'grade': grade,
        'grade_color': grade_color,
        'components': {
            'distance_time_fit': distance_time_score,
            'apy': apy_score,
            'volume': volume_score,
            'spread': spread_score,
            'momentum': momentum_score,
            'charm': charm_score
        },
        'distance_to_target': distance_to_target,
        'days_to_expiry': days_to_expiry,
        'in_sweet_spot': in_sweet_spot
    }


def render_pullback_hunter():
    """Render the Pullback Hunter dashboard page."""
    
    # Check for force refresh flag
    if st.query_params.get('refresh') == 'true':
        logger.info("🔄 Force refresh triggered - clearing all cached data")
        for key in list(st.session_state.keys()):
            if key in ['opportunities', 'scan_time', 'data_version']:
                del st.session_state[key]
        st.query_params.clear()
        st.rerun()
    
    # Compact header with minimal padding
    st.markdown('<h2 style="margin-top: -1rem; margin-bottom: 0.3rem; padding-top: 0;">🎯 Momentum Hunter</h2>', unsafe_allow_html=True)
    
    # Add CSS to reduce sidebar spacing
    st.markdown("""
    <style>
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [style*="flex-direction"] > div > [data-testid="stVerticalBlock"] {
            gap: 0.3rem !important;
        }
        [data-testid="stSidebar"] [data-baseweb="input"],
        [data-testid="stSidebar"] [data-baseweb="select"],
        [data-testid="stSidebar"] [data-baseweb="slider"],
        [data-testid="stSidebar"] [data-baseweb="checkbox"] {
            margin-bottom: 0.5rem !important;
        }
        [data-testid="stSidebar"] .stSelectbox,
        [data-testid="stSidebar"] .stSlider,
        [data-testid="stSidebar"] .stCheckbox,
        [data-testid="stSidebar"] .stNumberInput {
            margin-bottom: 0.4rem !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Move all controls to sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Momentum Hunter Settings")
        
        max_expiry_hours = st.select_slider(
            "Max Time to Expiry",
            options=[24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 288, 312, 336, 360, 384, 408, 432, 456, 480, 504, 528, 552, 576, 600, 624, 648, 672, 696, 720, 768, 816, 864, 912, 960, 1008, 1056, 1104, 1152, 1200, 1248, 1296, 1344, 1392, 1440, 1488, 1536, 1584, 1632, 1680, 1728, 1776, 1824, 1872, 1920, 1968, 2016, 2064, 2112, 2160],
            value=336,
            format_func=lambda x: f"{x//24}d",
            help="Maximum time until market expiration"
        )
        
        min_extremity = st.slider(
            "Max % from Extremes", 
            min_value=5, 
            max_value=50, 
            value=25, 
            step=5,
            help="Show markets from 0-X% and (100-X)-100%. Ex: 25% shows 0-25% and 75-100%"
        ) / 100.0  # Convert to decimal
        
        # min_distance must be <= min_extremity (can't exclude more than we're showing)
        min_extremity_pct = min_extremity * 100  # Convert back to percentage for slider
        min_distance_default = min(1.5, min_extremity_pct)
        
        min_distance = st.slider(
            "Min Distance from Extreme (%)",
            min_value=0.0,
            max_value=min_extremity_pct,
            value=min_distance_default,
            step=0.5,
            help=f"Minimum distance from 0% or 100%. Must be ≤ {min_extremity_pct:.0f}% (max extremity). Excludes markets too close to resolution."
        ) / 100.0  # Convert to decimal
        
        momentum_window_hours = st.select_slider(
            "Momentum Time Window",
            options=[12, 24, 48, 72, 96, 120, 144, 168],
            value=48,
            format_func=lambda x: f"{x}h" if x < 48 else f"{x//24}d",
            help="Time window for measuring directional momentum. YES: price must be rising. NO: price must be falling."
        )
        
        min_momentum = st.slider(
            "Min Momentum (%)",
            min_value=0,
            max_value=100,
            value=10,
            step=5,
            help="Minimum composite momentum signal (0-100%). Combines proportional (log-odds) and absolute moves. Example: 5%→1% or 60%→88% both score high."
        ) / 100.0  # Convert to decimal
        
        min_volume = st.select_slider(
            "Min Volume",
            options=[50_000, 100_000, 250_000, 500_000, 750_000, 1_000_000],
            value=250_000,
            format_func=lambda x: f"${x/1000:.0f}k" if x < 1_000_000 else f"${x/1_000_000:.1f}M",
            help="Minimum 24h trading volume. Higher volume = better liquidity."
        )
        
        limit = st.number_input(
            "Max Markets to Scan", 
            min_value=10, 
            max_value=5000, 
            value=1000,
            help="Higher values = more comprehensive scan but slower"
        )
        
        debug_mode = st.checkbox(
            "🐛 Debug Mode", 
            value=False, 
            help="Show all markets without extremity/expiry filters"
        )
        
        # Clear cache button
        if st.button("🗑️ Clear Cache", use_container_width=True):
            for key in ['opportunities', 'scan_time', 'data_version']:
                if key in st.session_state:
                    del st.session_state[key]
            logger.info("🗑️ Cache cleared")
            st.rerun()
        
        st.markdown('<div style="margin-top: 0.3rem;"></div>', unsafe_allow_html=True)
        st.caption("💡 Qualifies if extreme (>75%/<25%) OR high momentum (≥30%) with >60%/<40% probability")
    
    # Scan button, sort dropdown, and stats in one row
    col_scan, col_sort, col_stats = st.columns([1.5, 2, 2])
    
    with col_scan:
        scan_clicked = st.button("🔍 Scan Markets", type="primary", use_container_width=True)
    
    with col_sort:
        # Sort dropdown (only shown when there are opportunities)
        if 'opportunities' in st.session_state and st.session_state['opportunities']:
            sort_method = st.selectbox(
                "Sort by:",
                ["Score (High to Low)", "Probability (High to Low)", "Probability (Low to High)", 
                 "Momentum (High to Low)", "Charm (High to Low)", "APY (High to Low)", "Expires (Soonest First)"],
                index=0,
                label_visibility="collapsed"
            )
            st.session_state['sort_method'] = sort_method
    
    with col_stats:
        # Display results status in the same row
        if 'opportunities' in st.session_state:
            opportunities = st.session_state['opportunities']
            scan_time = st.session_state.get('scan_time', datetime.now())
            st.markdown(
                f'<div style="padding: 0.4rem 0.75rem; background-color: #d4edda; color: #155724; '
                f'border-radius: 0.25rem; margin-top: 0.15rem;">'
                f'✅ Found {len(opportunities)} opportunities (scanned at {scan_time.strftime("%H:%M:%S")})</div>',
                unsafe_allow_html=True
            )
    
    # Auto-scan on page load if no opportunities exist
    if 'opportunities' not in st.session_state:
        scan_clicked = True
    
    # Handle scan button click
    if scan_clicked:
        with st.spinner("Scanning markets..."):
            try:
                # Clear old opportunities to prevent stale data
                if 'opportunities' in st.session_state:
                    del st.session_state['opportunities']
                
                # Fresh scan
                logger.info("🔄 Starting fresh market scan...")
                opportunities = scan_pullback_markets(max_expiry_hours, min_extremity, limit, debug_mode, momentum_window_hours, min_momentum, min_volume, min_distance)
                
                # Store with version tag to invalidate old data
                st.session_state['opportunities'] = opportunities
                st.session_state['scan_time'] = datetime.now()
                st.session_state['data_version'] = '2024-12-22-v2'  # Increment to invalidate old caches
                
                logger.info(f"✅ Scan complete: {len(opportunities)} opportunities found")
                st.rerun()
            except Exception as e:
                logger.error(f"Scan error: {e}", exc_info=True)
                st.error(f"Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                return
    
    # Display results table
    if 'opportunities' in st.session_state:
        # Validate data version - reject old cached data
        data_version = st.session_state.get('data_version', 'unknown')
        expected_version = '2024-12-22-v2'
        
        if data_version != expected_version:
            logger.warning(f"⚠️ Stale data detected (version {data_version}), clearing...")
            del st.session_state['opportunities']
            st.warning("Cached data was outdated. Please scan again.")
            return
        
        opportunities = st.session_state['opportunities']
        
        if opportunities:
            
            display_pullback_table(opportunities)
        else:
            st.warning("No opportunities found. Try adjusting filters.")


def scan_pullback_markets(
    max_expiry_hours: int, 
    min_extremity: float, 
    limit: int, 
    debug_mode: bool = False, 
    momentum_window_hours: int = 48, 
    min_momentum: float = 0.15, 
    min_volume: float = 500_000, 
    min_distance: float = 0.015
) -> List[Dict]:
    """
    Elite momentum scanner with architectural excellence.
    
    Pipeline Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │  STAGE 1: MULTI-SOURCE AGGREGATION                      │
    │  • 8 diverse API strategies for comprehensive coverage  │
    │  • Intelligent deduplication by market slug             │
    └─────────────────────────────────────────────────────────┘
                            ↓
    ┌─────────────────────────────────────────────────────────┐
    │  STAGE 2: STRUCTURAL VALIDATION                         │
    │  • Verify required fields (question, slug, outcomes)    │
    │  • Parse and validate price data integrity              │
    │  • Clear rejection logging with categorization          │
    └─────────────────────────────────────────────────────────┘
                            ↓
    ┌─────────────────────────────────────────────────────────┐
    │  STAGE 3: QUALITY FILTERS                               │
    │  • Expiry window (>0h, <max_hours)                      │
    │  • Volume threshold (≥min_volume)                       │
    │  • Position filter (avoid 25%-75% middle zone)          │
    │  • Momentum threshold (≥min_momentum)                   │
    └─────────────────────────────────────────────────────────┘
                            ↓
    ┌─────────────────────────────────────────────────────────┐
    │  STAGE 4: SCORING & RANKING                             │
    │  • Composite momentum calculation                       │
    │  • Multi-factor opportunity scoring                     │
    │  • Annualized yield projection                          │
    └─────────────────────────────────────────────────────────┘
    
    Returns: Ranked list of momentum opportunities
    """
    import json
    from datetime import datetime, timezone
    
    # ═══════════════════════════════════════════════════════════════
    # HELPER FUNCTIONS: Clean, testable, single-responsibility
    # ═══════════════════════════════════════════════════════════════
    
    def categorize_market(question: str) -> str:
        """Categorize market by domain for analytics."""
        q = question.lower()
        if any(w in q for w in ['nfl', 'nba', 'mlb', 'nhl', 'super bowl', 'championship', 'playoff']):
            return 'Sports'
        if any(w in q for w in ['trump', 'biden', 'election', 'president', 'senate', 'congress']):
            return 'Politics'
        if any(w in q for w in ['movie', 'film', 'box office', 'oscar', 'grammy', 'celebrity']):
            return 'Entertainment'
        if any(w in q for w in ['bitcoin', 'stock', 'market', 'economy', 'fed', 'rate', 'gdp']):
            return 'Finance'
        return 'Other'
    
    def validate_market_structure(market: Dict) -> tuple[bool, str, List[str], List[float]]:
        """
        Validate market has required fields and parseable data.
        
        Returns: (is_valid, question, outcomes, prices)
        """
        # Required fields
        question = market.get('question', 'Unknown')
        if not question or question == 'Unknown':
            return False, '', [], []
        
        # Parse outcomes
        outcomes = market.get('outcomes', [])
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except:
                outcomes = [o.strip() for o in outcomes.split(',') if o.strip()]
        
        if not isinstance(outcomes, list) or len(outcomes) < 2:
            return False, question, [], []
        
        # Parse prices - with fallback strategy
        outcome_prices = []
        
        # PRIMARY: Try outcomePrices field
        if 'outcomePrices' in market:
            raw_prices = market.get('outcomePrices', [])
            
            # Handle string outcomePrices (JSON or comma-separated)
            if isinstance(raw_prices, str):
                try:
                    # Try JSON first
                    outcome_prices = json.loads(raw_prices)
                except:
                    # Try comma-separated values
                    try:
                        outcome_prices = [float(p.strip()) for p in raw_prices.split(',') if p.strip()]
                    except:
                        outcome_prices = []
            elif isinstance(raw_prices, list):
                outcome_prices = raw_prices
            else:
                outcome_prices = []
            
            # Convert all elements to float
            if outcome_prices:
                try:
                    outcome_prices = [float(p) for p in outcome_prices if p is not None]
                except (ValueError, TypeError):
                    outcome_prices = []
        
        # FALLBACK: Use lastTradePrice for binary markets
        if (not outcome_prices or len(outcome_prices) != len(outcomes)) and len(outcomes) == 2:
            last_trade = market.get('lastTradePrice', 0)
            
            # Convert to float if it's a string
            try:
                last_trade = float(last_trade) if last_trade else 0
            except (ValueError, TypeError):
                last_trade = 0
            
            if last_trade > 0:
                # Binary market: YES price = lastTradePrice, NO price = 1 - lastTradePrice
                outcome_prices = [last_trade, 1.0 - last_trade]
            else:
                # Try bid/ask midpoint
                bid = market.get('bestBid', 0)
                ask = market.get('bestAsk', 0)
                
                # Convert to float if strings
                try:
                    bid = float(bid) if bid else 0
                except (ValueError, TypeError):
                    bid = 0
                
                try:
                    ask = float(ask) if ask else 0
                except (ValueError, TypeError):
                    ask = 0
                
                if bid > 0 and ask > 0 and ask >= bid:
                    mid_price = (bid + ask) / 2
                    outcome_prices = [mid_price, 1.0 - mid_price]
        
        # Validate price count matches outcomes
        if not outcome_prices or len(outcome_prices) != len(outcomes):
            return False, question, outcomes, []
        
        # Validate prices are in valid range (0-1)
        if not all(0 <= p <= 1 for p in outcome_prices):
            return False, question, outcomes, []
        
        return True, question, outcomes, outcome_prices
    
    def parse_expiry(market: Dict, now: datetime) -> Optional[datetime]:
        """Parse market end date safely."""
        end_date = market.get('endDate') or market.get('end_date_iso') or market.get('end_date')
        if not end_date:
            return None
        try:
            return datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # MAIN ASYNC PIPELINE
    # ═══════════════════════════════════════════════════════════════
    
    async def fetch():
        now = datetime.now(timezone.utc)
        
        # ──────────────────────────────────────────────────────────
        # STAGE 1: MULTI-SOURCE MARKET AGGREGATION
        # ──────────────────────────────────────────────────────────
        
        async with GammaClient() as client:
            all_markets = []
            
            # Strategy 1: Liquidity sort
            logger.info("📊 Fetching markets sorted by liquidity...")
            try:
                markets = await client.get_markets(limit=1000, active=True, closed=False, order_by="liquidity")
                logger.info(f"   Liquidity: {len(markets)} markets")
                all_markets.extend(markets)
            except Exception as e:
                logger.warning(f"   Liquidity fetch failed: {e}")
            
            # Strategy 2: Default sort
            logger.info("📊 Fetching markets with default sorting...")
            try:
                markets = await client.get_markets(limit=1000, active=True, closed=False, order_by="")
                logger.info(f"   Default: {len(markets)} markets")
                all_markets.extend(markets)
            except Exception as e:
                logger.warning(f"   Default fetch failed: {e}")
            
            # Strategy 3: Hot markets
            logger.info("🔥 Fetching hot markets...")
            try:
                markets = await client.get_hot_markets(limit=500)
                logger.info(f"   Hot: {len(markets)} markets")
                all_markets.extend(markets)
            except Exception as e:
                logger.warning(f"   Hot markets failed: {e}")
            
            # Strategy 4: Breaking markets (from events)
            logger.info("📰 Fetching breaking markets...")
            try:
                breaking = await client.get_breaking_markets(limit=500)
                if breaking and isinstance(breaking, list) and breaking and 'markets' in breaking[0]:
                    # Extract from events
                    markets = []
                    for event in breaking:
                        markets.extend(event.get('markets', []))
                    breaking = markets
                logger.info(f"   Breaking: {len(breaking)} markets")
                all_markets.extend(breaking)
            except Exception as e:
                logger.warning(f"   Breaking markets failed: {e}")
            
            # Strategy 5: Event markets
            logger.info("🎯 Fetching event markets...")
            try:
                events = await client.get_events(limit=200, archived=False)
                event_markets = []
                for event in events:
                    event_markets.extend(event.get('markets', []))
                logger.info(f"   Events: {len(event_markets)} markets from {len(events)} events")
                all_markets.extend(event_markets)
            except Exception as e:
                logger.warning(f"   Events failed: {e}")
            
            # Strategy 6: Newest markets
            logger.info("✨ Fetching newest markets...")
            try:
                markets = await client.get_markets(limit=500, active=True, closed=False, order_by="createdAt")
                logger.info(f"   Newest: {len(markets)} markets")
                all_markets.extend(markets)
            except Exception as e:
                logger.warning(f"   Newest markets failed: {e}")
            
            # Deduplicate by slug
            seen = set()
            unique_markets = []
            for m in all_markets:
                slug = m.get('slug', '')
                if slug and slug not in seen:
                    seen.add(slug)
                    unique_markets.append(m)
            
            logger.info(f"✅ Aggregation complete: {len(all_markets)} total → {len(unique_markets)} unique ({len(all_markets) - len(unique_markets)} duplicates removed)")
            
            if not unique_markets:
                logger.error("❌ No markets found from any source")
                return []
            
            # Sample
            if len(unique_markets) >= 5:
                samples = [m.get('question', 'N/A')[:50] for m in unique_markets[:5]]
                logger.info(f"📝 Sample: {samples}")
            
            # ──────────────────────────────────────────────────────────
            # STAGE 2: STRUCTURAL VALIDATION
            # ──────────────────────────────────────────────────────────
            
            logger.info(f"\n🔍 Validating {len(unique_markets)} markets...")
            
            validation_stats = {
                'no_question': 0,
                'no_outcomes': 0,
                'no_prices_field': 0,
                'invalid_prices': 0,
                'price_mismatch': 0,
                'valid': 0
            }
            
            category_stats = {cat: {'total': 0, 'rejected': 0, 'passed': 0} 
                            for cat in ['Sports', 'Politics', 'Entertainment', 'Finance', 'Other']}
            
            validated_markets = []
            validation_debug_count = 0  # Track debug message count
            
            for market in unique_markets:
                question = market.get('question', '')
                category = categorize_market(question)
                category_stats[category]['total'] += 1
                
                is_valid, question, outcomes, prices = validate_market_structure(market)
                
                if not is_valid:
                    category_stats[category]['rejected'] += 1
                    # Determine why it failed
                    if not question:
                        validation_stats['no_question'] += 1
                    elif not outcomes or len(outcomes) < 2:
                        validation_stats['no_outcomes'] += 1
                    elif 'outcomePrices' not in market:
                        validation_stats['no_prices_field'] += 1
                    elif not prices:
                        validation_stats['invalid_prices'] += 1
                        validation_debug_count += 1  # Increment for price parsing issues
                    elif len(prices) != len(outcomes):
                        validation_stats['price_mismatch'] += 1
                    continue
                
                # Store validated data
                market['_validated_question'] = question
                market['_validated_outcomes'] = outcomes
                market['_validated_prices'] = prices
                validated_markets.append(market)
                validation_stats['valid'] += 1
                category_stats[category]['passed'] += 1
            
            logger.info(f"✅ Validation complete: {validation_stats['valid']}/{len(unique_markets)} passed")
            logger.info(f"   Rejections:")
            logger.info(f"     • Missing outcomePrices field: {validation_stats['no_prices_field']}")
            logger.info(f"     • Invalid price data: {validation_stats['invalid_prices']}")
            logger.info(f"     • Price/outcome mismatch: {validation_stats['price_mismatch']}")
            logger.info(f"     • Invalid outcomes: {validation_stats['no_outcomes']}")
            
            if debug_mode:
                logger.info(f"\n📊 Validation by category:")
                for cat in ['Sports', 'Politics', 'Entertainment', 'Finance', 'Other']:
                    stats = category_stats[cat]
                    if stats['total'] > 0:
                        pass_rate = (stats['passed'] / stats['total']) * 100
                        logger.info(f"   {cat}: {stats['passed']}/{stats['total']} ({pass_rate:.1f}%)")
            
            # ──────────────────────────────────────────────────────────
            # STAGE 3: QUALITY FILTERING & PROCESSING
            # ──────────────────────────────────────────────────────────
            
            logger.info(f"\n🎯 Applying quality filters to {len(validated_markets)} valid markets...")
            
            filter_stats = {
                'expired': 0,
                'low_volume': 0,
                'middle_zone': 0,
                'too_extreme': 0,
                'low_momentum': 0,
                'passed': 0
            }
            
            # Debug: Check first few markets for expiry parsing
            expiry_debug_count = 0
            
            opportunities = []
            
            # DEBUG MODE: Bypass all filters and show raw data
            if debug_mode:
                logger.info("🐛 DEBUG MODE: Bypassing all quality filters - showing raw market data")
                for market in validated_markets:
                    question = market['_validated_question']
                    outcomes = market['_validated_outcomes']
                    prices = market['_validated_prices']
                    
                    # Market metadata
                    slug = market.get('slug', '')
                    url = f"https://polymarket.com/market/{slug}"
                    is_binary = len(outcomes) == 2 and all(o.lower() in ['yes', 'no'] for o in outcomes)
                    
                    # Expiry check (for display only in debug mode)
                    end_dt = parse_expiry(market, now)
                    if not end_dt:
                        end_dt = now
                    hours_to_expiry = (end_dt - now).total_seconds() / 3600
                    
                    # Volume
                    volume = float(market.get('volume') or 0)
                    
                    # Process each outcome
                    outcome_indices = [0] if is_binary else range(len(outcomes))
                    
                    for idx in outcome_indices:
                        outcome_name = outcomes[idx]
                        yes_price = prices[idx]
                        
                        # Bid/ask spread
                        if is_binary:
                            best_bid = float(market.get('bestBid', yes_price - 0.01))
                            best_ask = float(market.get('bestAsk', yes_price + 0.01))
                        else:
                            spread = max(0.01, yes_price * 0.02)
                            best_bid = max(0.001, yes_price - spread / 2)
                            best_ask = min(0.999, yes_price + spread / 2)
                        
                        # Direction logic (simplified for debug)
                        if is_binary:
                            if yes_price > 0.5:
                                direction = 'YES'
                            else:
                                direction = 'NO'
                        else:
                            direction = 'YES'
                        
                        # Momentum calculation (simplified for debug)
                        one_day_change = float(market.get('oneDayPriceChange') or 0)
                        momentum_data = calculate_composite_momentum(yes_price, one_day_change)
                        momentum = momentum_data['signal_strength']
                        
                        # Calculate yield
                        if direction == 'YES':
                            entry_price = best_ask
                            profit_if_win = (1.0 - entry_price) / entry_price if entry_price > 0 else 0
                        else:
                            entry_price = 1.0 - best_bid
                            profit_if_win = (1.0 - entry_price) / entry_price if 0 < entry_price < 1 else 0
                        
                        days_to_expiry = hours_to_expiry / 24
                        if days_to_expiry > 0.1:
                            exponent = 365 / days_to_expiry
                            try:
                                annualized_yield = ((1 + profit_if_win) ** min(exponent, 1000)) - 1
                            except (OverflowError, ValueError):
                                annualized_yield = 0
                        else:
                            annualized_yield = 0
                        
                        # Calculate charm (delta decay)
                        charm = (momentum * 100) / days_to_expiry if days_to_expiry > 0 else 0
                        
                        # Calculate score (simplified for debug)
                        score_data = calculate_opportunity_score(
                            current_prob=yes_price,
                            momentum=momentum,
                            hours_to_expiry=hours_to_expiry,
                            volume=volume,
                            best_bid=best_bid,
                            best_ask=best_ask,
                            direction=direction,
                            one_day_change=one_day_change,
                        )
                        
                        # Format question
                        display_question = question if is_binary else f"{question} [{outcome_name}]"
                        
                        # Add ALL markets in debug mode
                        opportunities.append({
                            'question': display_question,
                            'slug': slug,
                            'url': url,
                            'current_prob': yes_price,
                            'hours_to_expiry': hours_to_expiry,
                            'end_date': end_dt,
                            'volume_24h': volume,
                            'momentum': momentum,
                            'charm': charm,
                            'score': score_data['total_score'],
                            'grade': score_data['grade'],
                            'direction': direction,
                            'annualized_yield': annualized_yield,
                            'best_bid': best_bid,
                            'best_ask': best_ask
                        })
                
                # Sort by score
                opportunities.sort(key=lambda x: x['score'], reverse=True)
                
                # Final report for debug mode
                logger.info(f"\n{'='*70}")
                logger.info(f"DEBUG MODE RESULTS:")
                logger.info(f"  All validated markets: {len(validated_markets)}")
                logger.info(f"  Opportunities shown: {len(opportunities)}")
                logger.info(f"{'='*70}\n")
                
                logger.info(f"🎉 Found {len(opportunities)} momentum opportunities (DEBUG MODE)")
                return opportunities
            
            # NORMAL MODE: Apply quality filters
            
            for market in validated_markets:
                question = market['_validated_question']
                outcomes = market['_validated_outcomes']
                prices = market['_validated_prices']
                
                # Market metadata
                slug = market.get('slug', '')
                url = f"https://polymarket.com/market/{slug}"
                is_binary = len(outcomes) == 2 and all(o.lower() in ['yes', 'no'] for o in outcomes)
                
                # Expiry check
                end_dt = parse_expiry(market, now)
                if not end_dt:
                    end_dt = now
                hours_to_expiry = (end_dt - now).total_seconds() / 3600
                
                # Debug first few markets with failed expiry
                if expiry_debug_count < 5 and (not end_dt or end_dt == now or hours_to_expiry <= 0 or hours_to_expiry > max_expiry_hours):
                    logger.info(f"DEBUG Expiry: {question[:60]}")
                    logger.info(f"  endDate: {market.get('endDate')}")
                    logger.info(f"  end_date_iso: {market.get('end_date_iso')}")
                    logger.info(f"  end_date: {market.get('end_date')}")
                    logger.info(f"  Parsed: {end_dt}")
                    logger.info(f"  Hours: {hours_to_expiry:.2f}, Max: {max_expiry_hours}")
                    expiry_debug_count += 1
                
                if hours_to_expiry <= 0 or hours_to_expiry > max_expiry_hours:
                    filter_stats['expired'] += 1
                    continue
                
                # Volume check
                volume = float(market.get('volume') or 0)
                if volume < min_volume:
                    filter_stats['low_volume'] += 1
                    continue
                
                # Process each outcome
                outcome_indices = [0] if is_binary else range(len(outcomes))
                
                for idx in outcome_indices:
                    outcome_name = outcomes[idx]
                    yes_price = prices[idx]
                    
                    # Bid/ask spread
                    if is_binary:
                        best_bid = float(market.get('bestBid', yes_price - 0.01))
                        best_ask = float(market.get('bestAsk', yes_price + 0.01))
                    else:
                        spread = max(0.01, yes_price * 0.02)
                        best_bid = max(0.001, yes_price - spread / 2)
                        best_ask = min(0.999, yes_price + spread / 2)
                    
                    # Direction logic
                    if is_binary:
                        if yes_price > 0.75:
                            direction = 'YES'
                        elif yes_price < 0.25:
                            direction = 'NO'
                        else:
                            filter_stats['middle_zone'] += 1
                            continue
                    else:
                        direction = 'YES'
                    
                    # Distance from extreme check
                    if direction == 'YES' and yes_price >= (1.0 - min_distance):
                        filter_stats['too_extreme'] += 1
                        continue
                    if direction == 'NO' and yes_price <= min_distance:
                        filter_stats['too_extreme'] += 1
                        continue
                    
                    # Momentum calculation
                    one_day_change = float(market.get('oneDayPriceChange') or 0)
                    one_week_change = float(market.get('oneWeekPriceChange') or 0)
                    directional_momentum = one_day_change if momentum_window_hours <= 24 else one_week_change
                    
                    momentum_data = calculate_composite_momentum(yes_price, directional_momentum)
                    momentum = momentum_data['signal_strength']
                    
                    if momentum < min_momentum:
                        filter_stats['low_momentum'] += 1
                        continue
                    
                    # Passed all filters!
                    filter_stats['passed'] += 1
                    
                    # Calculate yield
                    if direction == 'YES':
                        entry_price = best_ask
                        profit_if_win = (1.0 - entry_price) / entry_price if entry_price > 0 else 0
                    else:
                        entry_price = 1.0 - best_bid
                        profit_if_win = (1.0 - entry_price) / entry_price if 0 < entry_price < 1 else 0
                    
                    days_to_expiry = hours_to_expiry / 24
                    if days_to_expiry > 0.1:
                        exponent = 365 / days_to_expiry
                        try:
                            annualized_yield = ((1 + profit_if_win) ** min(exponent, 1000)) - 1
                        except (OverflowError, ValueError):
                            annualized_yield = 0
                    else:
                        annualized_yield = 0
                    
                    # Calculate charm (delta decay)
                    charm = (momentum * 100) / days_to_expiry if days_to_expiry > 0 else 0
                    
                    # Calculate score
                    score_data = calculate_opportunity_score(
                        current_prob=yes_price,
                        momentum=momentum,
                        hours_to_expiry=hours_to_expiry,
                        volume=volume,
                        best_bid=best_bid,
                        best_ask=best_ask,
                        direction=direction,
                        one_day_change=one_day_change,
                        one_week_change=one_week_change,
                        annualized_yield=annualized_yield,
                        charm=charm
                    )
                    
                    # Format question
                    display_question = question if is_binary else f"{question} [{outcome_name}]"
                    
                    # Add opportunity
                    opportunities.append({
                        'question': display_question,
                        'slug': slug,
                        'url': url,
                        'current_prob': yes_price,
                        'hours_to_expiry': hours_to_expiry,
                        'end_date': end_dt,
                        'volume_24h': volume,
                        'momentum': momentum,
                        'charm': charm,
                        'score': score_data['total_score'],
                        'grade': score_data['grade'],
                        'direction': direction,
                        'annualized_yield': annualized_yield,
                        'best_bid': best_bid,
                        'best_ask': best_ask
                    })
            
            # Sort by score
            opportunities.sort(key=lambda x: x['score'], reverse=True)
            
            # ──────────────────────────────────────────────────────────
            # STAGE 4: DEDUPLICATION & REPORTING
            # ──────────────────────────────────────────────────────────
            
            # Deduplicate opportunities
            seen_keys = set()
            unique_opportunities = []
            for opp in opportunities:
                key = (opp['slug'], opp['direction'], round(opp['current_prob'], 4))
                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_opportunities.append(opp)
            
            if len(opportunities) != len(unique_opportunities):
                logger.info(f"🔄 Deduplication: {len(opportunities)} → {len(unique_opportunities)} ({len(opportunities) - len(unique_opportunities)} removed)")
                opportunities = unique_opportunities
            
            # Final report
            logger.info(f"\n{'='*70}")
            logger.info(f"QUALITY FILTER RESULTS:")
            logger.info(f"  Filtered markets: {len(validated_markets)}")
            logger.info(f"  ❌ Expired/too far: {filter_stats['expired']}")
            logger.info(f"  ❌ Low volume (<${min_volume:,.0f}): {filter_stats['low_volume']}")
            logger.info(f"  ❌ Middle zone (25%-75%): {filter_stats['middle_zone']}")
            logger.info(f"  ❌ Too close to extreme: {filter_stats['too_extreme']}")
            logger.info(f"  ❌ Low momentum (<{min_momentum:.1%}): {filter_stats['low_momentum']}")
            logger.info(f"  ✅ PASSED: {filter_stats['passed']}")
            logger.info(f"{'='*70}\n")
            
            logger.info(f"🎉 Found {len(opportunities)} momentum opportunities")
            return opportunities
    
    return asyncio.run(fetch())


def display_pullback_table(opportunities: List[Dict]):
    """Display opportunities in a compact table."""
    
    st.markdown('<h3 style="margin-top: 0.5rem; margin-bottom: 0.5rem;">Momentum Opportunities</h3>', unsafe_allow_html=True)
    
    if not opportunities:
        st.warning("No opportunities to display")
        return
    
    # Apply sorting based on session state selection
    sort_method = st.session_state.get('sort_method', 'Score (High to Low)')
    
    # Sort opportunities based on selection
    if sort_method == "Score (High to Low)":
        opportunities = sorted(opportunities, key=lambda x: x['score'], reverse=True)
    elif sort_method == "Probability (High to Low)":
        opportunities = sorted(opportunities, key=lambda x: x['current_prob'], reverse=True)
    elif sort_method == "Probability (Low to High)":
        opportunities = sorted(opportunities, key=lambda x: x['current_prob'])
    elif sort_method == "Momentum (High to Low)":
        opportunities = sorted(opportunities, key=lambda x: x.get('momentum', 0), reverse=True)
    elif sort_method == "Charm (High to Low)":
        opportunities = sorted(opportunities, key=lambda x: abs(x.get('charm', 0)), reverse=True)
    elif sort_method == "APY (High to Low)":
        opportunities = sorted(opportunities, key=lambda x: x.get('annualized_yield', 0), reverse=True)
    elif sort_method == "Expires (Soonest First)":
        opportunities = sorted(opportunities, key=lambda x: x['hours_to_expiry'])
    
    # Build HTML table
    html = """
    <style>
        .momentum-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; font-family: Helvetica, Arial, sans-serif; }
        .momentum-table th { background: #2c3e50; color: white; padding: 4px 6px; text-align: left; font-size: 0.8rem; font-weight: 600; }
        .momentum-table td { padding: 3px 6px; border-bottom: 1px solid #ecf0f1; }
        .momentum-table tr:nth-child(even) { background: #f8f9fa; }
        .momentum-table tr:nth-child(odd) { background: white; }
        .momentum-table tr:hover { background: #e8f4f8; }
        .market-link { color: #2980b9; text-decoration: none; font-size: 0.9rem; font-weight: 500; }
        .market-link:hover { text-decoration: underline; }
        .prob-yes { color: #27ae60; font-weight: 600; }
        .prob-no { color: #e74c3c; font-weight: 600; }
        .mom-high { color: #9b59b6; font-weight: 600; }
        .mom-med { color: #9b59b6; }
        .mom-low { color: #95a5a6; }
        .exp-urgent { color: #e74c3c; font-weight: 600; }
        .exp-soon { color: #f39c12; font-weight: 600; }
        .exp-normal { color: #3498db; }
        .apy-extreme { color: #1e7e34; font-weight: 600; }  /* dark green for >10000% */
        .apy-high { color: #27ae60; font-weight: 600; }  /* light green for 100-1000% */
        .score-a { color: #27ae60; font-weight: 600; }
        .score-b { color: #f39c12; font-weight: 600; }
        .score-c { color: #3498db; }
    </style>
    <table class="momentum-table">
        <thead>
            <tr>
                <th style="width: 38%;">Market</th>
                <th style="width: 5%;">Prob</th>
                <th style="width: 4%;">Dir</th>
                <th style="width: 5%;">Price</th>
                <th style="width: 6%;">Mom</th>
                <th style="width: 6%;" title="Delta decay per day">Charm</th>
                <th style="width: 6%;">Vol</th>
                <th style="width: 8%;">Expires</th>
                <th style="width: 7%;">APY</th>
                <th style="width: 6%;">Score</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for opp in opportunities[:50]:
        question = opp['question'][:65] + "..." if len(opp['question']) > 65 else opp['question']
        url = opp['url']
        
        # Probability - ALWAYS show YES probability (0-1)
        prob = opp['current_prob']
        prob_class = "prob-yes" if prob > 0.5 else "prob-no"
        prob_str = f"{prob:.1%}"
        
        # Direction
        direction = "YES" if opp['direction'] == "YES" else "NO"
        dir_class = "prob-yes" if direction == "YES" else "prob-no"
        
        # Bid/Ask for this direction - 1 decimal
        best_bid = opp.get('best_bid')
        best_ask = opp.get('best_ask')
        if direction == "YES":
            price_display = f"${best_ask:.2f}" if best_ask is not None else "N/A"
        else:
            # For NO, show (1 - best_bid)
            price_display = f"${(1.0 - best_bid):.2f}" if best_bid is not None else "N/A"
        
        # Momentum - 1 decimal
        momentum = opp.get('momentum', 0)
        if momentum >= 0.30:
            mom_class = "mom-high"
        elif momentum >= 0.15:
            mom_class = "mom-med"
        else:
            mom_class = "mom-low"
        mom_str = f"{momentum:+.1%}"
        
        # Volume
        vol = opp['volume_24h']
        if vol >= 1_000_000:
            vol_str = f"${vol/1_000_000:.1f}M"
        elif vol >= 1000:
            vol_str = f"${vol/1000:.0f}K"
        else:
            vol_str = f"${vol:.0f}"
        
        # Expiration
        hours = opp['hours_to_expiry']
        if hours < 24:
            time_str = f"{int(hours)}h"
            exp_class = "exp-urgent"
        elif hours < 72:
            time_str = f"{hours/24:.1f}d"
            exp_class = "exp-soon"
        else:
            time_str = f"{int(hours/24)}d"
            exp_class = "exp-normal"
        exp_date = opp['end_date'].strftime('%m/%d')
        exp_str = f"{time_str} {exp_date}"
        
        # Score with grade from scoring algorithm
        score = opp['score']
        grade = opp.get('grade', 'C')
        
        # Determine CSS class based on grade
        if grade in ['A+', 'A']:
            score_class = "score-a"
        elif grade in ['B+', 'B']:
            score_class = "score-b"
        else:
            score_class = "score-c"
        
        score_str = f"{score:.0f} {grade}"
        
        # Annualized Yield - use multiples (x) for >10000%
        ann_yield = opp.get('annualized_yield', 0)
        if ann_yield > 100:  # >10000% - dark green
            apy_class = "apy-extreme"
            apy_str = f"x{ann_yield:.0f}"
        elif ann_yield > 1:  # 100-1000% - light green
            apy_class = "apy-high"
            apy_str = f"{ann_yield:.1%}"
        elif ann_yield > 0.5:  # >50%
            apy_class = "score-b"
            apy_str = f"{ann_yield:.1%}"
        else:
            apy_class = "score-c"
            apy_str = f"{ann_yield:.1%}"
        
        # Charm (delta decay)
        charm = opp.get('charm', 0)
        if abs(charm) >= 2.0:
            charm_class = "mom-high"
        elif abs(charm) >= 1.0:
            charm_class = "mom-med"
        else:
            charm_class = "mom-low"
        charm_str = f"{charm:+.1f}%"
        
        html += f"""
            <tr>
                <td><a href="{url}" class="market-link" target="_blank">{question}</a></td>
                <td><span class="{prob_class}">{prob_str}</span></td>
                <td><span class="{dir_class}">{direction}</span></td>
                <td>{price_display}</td>
                <td><span class="{mom_class}">{mom_str}</span></td>
                <td><span class="{charm_class}">{charm_str}</span></td>
                <td>{vol_str}</td>
                <td><span class="{exp_class}">{exp_str}</span></td>
                <td><span class="{apy_class}">{apy_str}</span></td>
                <td><span class="{score_class}">{score_str}</span></td>
            </tr>
        """
    
    html += """
        </tbody>
    </table>
    """
    
    # Use st.write with HTML to ensure proper rendering
    import streamlit.components.v1 as components
    components.html(html, height=min(len(opportunities) * 35 + 100, 1200), scrolling=True)


# ============================================================================
# ARBITRAGE SCANNER STRATEGY
# ============================================================================

def detect_non_exclusive_outcomes(outcomes: List[str], question: str) -> bool:
    """
    Detect if outcomes might NOT be mutually exclusive.
    
    Examples of non-exclusive patterns:
    - ">2%" and ">3%" (if 3.5%, both win)
    - "Over 100" and "Over 200" (if 250, both win)
    - "At least 50%" and "At least 75%" (if 80%, both win)
    
    Returns True if market appears to have non-exclusive outcomes.
    """
    if len(outcomes) < 2:
        return False
    
    # Keywords that suggest range/threshold markets
    range_keywords = [
        'over', 'under', 'above', 'below', 'more than', 'less than',
        'at least', 'at most', 'greater', 'higher', 'lower', 'exceed',
        '>', '<', '≥', '≤', 'minimum', 'maximum'
    ]
    
    # Check if multiple outcomes contain range keywords
    outcomes_with_ranges = 0
    for outcome in outcomes:
        outcome_lower = outcome.lower()
        if any(keyword in outcome_lower for keyword in range_keywords):
            outcomes_with_ranges += 1
    
    # If 2+ outcomes have range keywords, likely non-exclusive
    if outcomes_with_ranges >= 2:
        return True
    
    # Check for percentage/number patterns that suggest ranges
    import re
    number_patterns = []
    for outcome in outcomes:
        # Look for patterns like ">2%", "Over 100", "<50"
        if re.search(r'[><≥≤]\s*\d+', outcome):
            number_patterns.append(outcome)
    
    # If 2+ outcomes have comparison operators with numbers, likely non-exclusive
    if len(number_patterns) >= 2:
        return True
    
    return False


def calculate_arbitrage_opportunities(
    outcomes: List[str], 
    outcome_prices: List[float],
    best_bids: List[float], 
    best_asks: List[float]
) -> Dict:
    """
    Calculate ALL possible arbitrage opportunities with rigorous math.
    
    For N outcomes where exactly ONE will resolve to $1 and others to $0:
    
    STRATEGY 1: BUY ALL OUTCOMES
    - Cost = Σ(ask_i) for all i
    - Guaranteed return = $1 (exactly one wins)
    - Profit = $1 - Cost
    - Arbitrage exists if: Σ(ask_i) < 1.0
    
    STRATEGY 2: SELL ALL OUTCOMES  
    - Revenue = Σ(bid_i) for all i
    - Liability = $1 (must pay winner)
    - Profit = Revenue - $1
    - Arbitrage exists if: Σ(bid_i) > 1.0
    
    STRATEGY 3: BINARY MARKET YES/NO ARBITRAGE
    - For 2-outcome markets only
    - Check: bid_YES + bid_NO > 1 (sell both)
    - Check: ask_YES + ask_NO < 1 (buy both)
    - Check: bid_YES > ask_NO (buy NO, sell YES equivalent)
    - Check: bid_NO > ask_YES (buy YES, sell NO equivalent)
    
    Returns dict with all opportunities and their exact P&L.
    """
    n = len(outcomes)
    
    if n < 2 or len(outcome_prices) < n:
        return {'opportunities': [], 'best_opportunity': None}
    
    # Check for non-mutually exclusive outcomes
    non_exclusive = detect_non_exclusive_outcomes(outcomes, '')
    
    # Ensure we have proper bid/ask arrays
    if len(best_bids) < n:
        best_bids = best_bids + [max(0.001, outcome_prices[i] - 0.01) for i in range(len(best_bids), n)]
    if len(best_asks) < n:
        best_asks = best_asks + [min(0.999, outcome_prices[i] + 0.01) for i in range(len(best_asks), n)]
    
    opportunities = []
    
    # ==========================================================================
    # STRATEGY 1: BUY ALL OUTCOMES AT ASK
    # ==========================================================================
    # Logic: Pay ask price for each outcome. Exactly one resolves to $1.
    # P&L = $1 - Σ(ask_i)
    total_ask = sum(best_asks)
    buy_all_profit = 1.0 - total_ask
    
    opportunities.append({
        'strategy': 'BUY_ALL',
        'description': f'Buy all {n} outcomes at ASK prices',
        'action': 'BUY',
        'cost': total_ask,
        'guaranteed_return': 1.0,
        'profit': buy_all_profit,
        'profit_pct': buy_all_profit * 100,
        'is_profitable': buy_all_profit > 0,
        'execution': [{'outcome': outcomes[i], 'side': 'BUY', 'price': best_asks[i]} for i in range(n)],
        'formula': f'$1.00 - Σ(asks) = $1.00 - ${total_ask:.4f} = ${buy_all_profit:.4f}',
        'risk': 'Zero (guaranteed profit)' if buy_all_profit > 0 else 'N/A'
    })
    
    # ==========================================================================
    # STRATEGY 2: SELL ALL OUTCOMES AT BID
    # ==========================================================================
    # Logic: Receive bid price for each outcome. Must pay $1 to winner.
    # P&L = Σ(bid_i) - $1
    total_bid = sum(best_bids)
    sell_all_profit = total_bid - 1.0
    
    opportunities.append({
        'strategy': 'SELL_ALL',
        'description': f'Sell all {n} outcomes at BID prices',
        'action': 'SELL',
        'revenue': total_bid,
        'liability': 1.0,
        'profit': sell_all_profit,
        'profit_pct': sell_all_profit * 100,
        'is_profitable': sell_all_profit > 0,
        'execution': [{'outcome': outcomes[i], 'side': 'SELL', 'price': best_bids[i]} for i in range(n)],
        'formula': f'Σ(bids) - $1.00 = ${total_bid:.4f} - $1.00 = ${sell_all_profit:.4f}',
        'risk': 'Zero (guaranteed profit)' if sell_all_profit > 0 else 'N/A'
    })
    
    # ==========================================================================
    # STRATEGY 3: CROSS-OUTCOME ARBITRAGE (for each outcome)
    # ==========================================================================
    for i in range(n):
        other_asks_sum = sum(best_asks[j] for j in range(n) if j != i)
        
        # Action: SELL i at bid_i, BUY all j≠i at ask_j
        # Entry cash: bid_i - other_asks_sum
        # At resolution:
        #   If i wins: I owe $1 to buyer, others worth $0 → -$1
        #   If j wins: I owe $0, I receive $1 from j → +$1
        
        pnl_if_i_wins = best_bids[i] - other_asks_sum - 1.0
        pnl_if_j_wins = best_bids[i] - other_asks_sum + 1.0
        
        # Guaranteed profit = minimum P&L across all scenarios
        guaranteed_profit = min(pnl_if_i_wins, pnl_if_j_wins)
        
        opportunities.append({
            'strategy': f'CROSS_{i}',
            'description': f'Sell "{outcomes[i]}" + Buy all others',
            'action': 'HEDGE',
            'target_outcome': outcomes[i],
            'entry_cash': best_bids[i] - other_asks_sum,
            'pnl_if_target_wins': pnl_if_i_wins,
            'pnl_if_other_wins': pnl_if_j_wins,
            'profit': guaranteed_profit,
            'profit_pct': guaranteed_profit * 100,
            'is_profitable': guaranteed_profit > 0,
            'execution': [
                {'outcome': outcomes[i], 'side': 'SELL', 'price': best_bids[i]}
            ] + [
                {'outcome': outcomes[j], 'side': 'BUY', 'price': best_asks[j]} 
                for j in range(n) if j != i
            ],
            'formula': f'Min(${pnl_if_i_wins:.4f}, ${pnl_if_j_wins:.4f}) = ${guaranteed_profit:.4f}',
            'risk': 'Zero (guaranteed profit)' if guaranteed_profit > 0 else 'N/A'
        })
        
        # Reverse: Buy outcome i, sell all others
        other_bids_sum = sum(best_bids[j] for j in range(n) if j != i)
        
        # Action: BUY i at ask_i, SELL all j≠i at bid_j
        # Entry cash: -ask_i + Σ(bid_j≠i) = other_bids_sum - ask_i
        # At resolution:
        #   If i wins: I receive $1, others owe $0 → +$1
        #   If j wins: I receive $0, I owe $1 to j's buyer → -$1
        
        pnl_if_i_wins_rev = (other_bids_sum - best_asks[i]) + 1.0
        pnl_if_j_wins_rev = (other_bids_sum - best_asks[i]) - 1.0
        
        guaranteed_profit_rev = min(pnl_if_i_wins_rev, pnl_if_j_wins_rev)
        
        opportunities.append({
            'strategy': f'CROSS_REV_{i}',
            'description': f'Buy "{outcomes[i]}" + Sell all others',
            'action': 'HEDGE',
            'target_outcome': outcomes[i],
            'entry_cash': other_bids_sum - best_asks[i],
            'pnl_if_target_wins': pnl_if_i_wins_rev,
            'pnl_if_other_wins': pnl_if_j_wins_rev,
            'profit': guaranteed_profit_rev,
            'profit_pct': guaranteed_profit_rev * 100,
            'is_profitable': guaranteed_profit_rev > 0,
            'execution': [
                {'outcome': outcomes[i], 'side': 'BUY', 'price': best_asks[i]}
            ] + [
                {'outcome': outcomes[j], 'side': 'SELL', 'price': best_bids[j]} 
                for j in range(n) if j != i
            ],
            'formula': f'Min(${pnl_if_i_wins_rev:.4f}, ${pnl_if_j_wins_rev:.4f}) = ${guaranteed_profit_rev:.4f}',
            'risk': 'Zero (guaranteed profit)' if guaranteed_profit_rev > 0 else 'N/A'
        })
    
    # ==========================================================================
    # STRATEGY 4: BINARY MARKET SPECIFIC (n=2)
    # ==========================================================================
    if n == 2:
        yes_bid, yes_ask = best_bids[0], best_asks[0]
        no_bid, no_ask = best_bids[1], best_asks[1]
        
        # Synthetic YES = 1 - NO
        # If YES_bid > (1 - NO_ask), sell YES + buy NO
        synthetic_no_ask = 1.0 - no_ask  # Cost to create synthetic YES via NO
        if yes_bid > synthetic_no_ask and yes_bid > 0.001:
            synth_profit = yes_bid - synthetic_no_ask
            opportunities.append({
                'strategy': 'SYNTH_YES',
                'description': 'Sell YES + Buy NO (synthetic arbitrage)',
                'action': 'SYNTHETIC',
                'profit': synth_profit,
                'profit_pct': synth_profit * 100,
                'is_profitable': synth_profit > 0,
                'execution': [
                    {'outcome': 'YES', 'side': 'SELL', 'price': yes_bid},
                    {'outcome': 'NO', 'side': 'BUY', 'price': no_ask}
                ],
                'formula': f'YES_bid - (1-NO_ask) = {yes_bid:.4f} - {synthetic_no_ask:.4f} = ${synth_profit:.4f}',
                'risk': 'Zero (positions cancel)'
            })
        
        # Synthetic NO check
        synthetic_yes_ask = 1.0 - yes_ask
        if no_bid > synthetic_yes_ask and no_bid > 0.001:
            synth_profit = no_bid - synthetic_yes_ask
            opportunities.append({
                'strategy': 'SYNTH_NO',
                'description': 'Sell NO + Buy YES (synthetic arbitrage)',
                'action': 'SYNTHETIC',
                'profit': synth_profit,
                'profit_pct': synth_profit * 100,
                'is_profitable': synth_profit > 0,
                'execution': [
                    {'outcome': 'NO', 'side': 'SELL', 'price': no_bid},
                    {'outcome': 'YES', 'side': 'BUY', 'price': yes_ask}
                ],
                'formula': f'NO_bid - (1-YES_ask) = {no_bid:.4f} - {synthetic_yes_ask:.4f} = ${synth_profit:.4f}',
                'risk': 'Zero (positions cancel)'
            })
    
    # Find best profitable opportunity
    profitable = [o for o in opportunities if o['is_profitable']]
    best_opportunity = max(profitable, key=lambda x: x['profit']) if profitable else None
    
    # Calculate summary metrics
    return {
        'opportunities': opportunities,
        'profitable_opportunities': profitable,
        'best_opportunity': best_opportunity,
        'n_outcomes': n,
        'total_bid_sum': total_bid,
        'total_ask_sum': total_ask,
        'mid_sum': sum(outcome_prices),
        'overround_bid': (total_bid - 1.0) * 100,
        'overround_ask': (total_ask - 1.0) * 100,
        'overround_mid': (sum(outcome_prices) - 1.0) * 100,
        'has_arbitrage': len(profitable) > 0,
        'max_profit': best_opportunity['profit'] if best_opportunity else 0,
        'max_profit_pct': best_opportunity['profit_pct'] if best_opportunity else 0,
        'non_exclusive_warning': non_exclusive
    }


def calculate_inefficiency_score(arb_result: Dict) -> float:
    """
    Calculate an inefficiency score (0-100) for ranking markets.
    Higher = more interesting for analysis.
    """
    score = 0
    
    # Major bonus for actual arbitrage
    if arb_result['has_arbitrage']:
        score += 50 + min(50, arb_result['max_profit_pct'] * 10)
    else:
        # Score based on how close to arbitrage
        bid_deviation = abs(arb_result['overround_bid'])
        ask_deviation = abs(arb_result['overround_ask'])
        
        score += min(30, bid_deviation * 3)
        score += min(30, ask_deviation * 3)
        
        # Bonus for wide spreads (indicates opportunity)
        spread = arb_result['total_ask_sum'] - arb_result['total_bid_sum']
        score += min(20, spread * 50)
    
    # More outcomes = more complexity = potentially more opportunities
    n = arb_result['n_outcomes']
    if n >= 5:
        score += 10
    elif n >= 3:
        score += 5
    
    return min(100, score)


@st.cache_data(ttl=60)
def scan_arbitrage_markets(min_outcomes: int = 2, limit: int = 500,
                           show_all: bool = False) -> List[Dict]:
    """Scan markets for arbitrage opportunities with rigorous math."""
    
    async def fetch():
        async with GammaClient() as client:
            all_markets = []
            
            logger.info("Fetching markets for arbitrage scan...")
            
            # Fetch from multiple sources for diversity
            for order_by in ["volume", "liquidity", ""]:
                try:
                    markets = await client.get_markets(limit=limit, active=True, closed=False, order_by=order_by)
                    all_markets.extend(markets)
                except Exception as e:
                    logger.warning(f"Fetch with order_by={order_by} failed: {e}")
            
            # Deduplicate
            seen = set()
            markets = []
            for m in all_markets:
                slug = m.get('slug', '')
                if slug and slug not in seen:
                    seen.add(slug)
                    markets.append(m)
            
            logger.info(f"Processing {len(markets)} unique markets")
            
            results = []
            
            # Debug counters
            filtered_outcomes = 0
            filtered_prices = 0
            processed = 0
            errors = 0
            
            # Debug: check first market structure
            if markets and len(markets) > 0:
                sample = markets[0]
                logger.info(f"Sample market keys: {list(sample.keys())}")
                logger.info(f"Sample outcomes: {sample.get('outcomes', 'MISSING')}")
                logger.info(f"Sample outcomePrices: {sample.get('outcomePrices', 'MISSING')}")
            
            for market in markets:
                try:
                    # Parse outcomes - may be JSON string or list
                    outcomes = market.get('outcomes', [])
                    if isinstance(outcomes, str):
                        import json
                        try:
                            outcomes = json.loads(outcomes)
                        except:
                            # If JSON parsing fails, might be comma-separated
                            outcomes = [o.strip() for o in outcomes.split(',') if o.strip()]
                    
                    # Ensure it's a list
                    if not isinstance(outcomes, list):
                        outcomes = []
                    
                    n = len(outcomes)
                    
                    # Debug first few failures
                    if n == 0 and filtered_outcomes < 3:
                        logger.warning(f"Market {market.get('question', 'Unknown')[:50]} has 0 outcomes. Keys: {list(market.keys())}")
                    
                    # In debug mode, process everything; otherwise apply filters
                    if not show_all:
                        if n < min_outcomes:
                            filtered_outcomes += 1
                            continue
                    
                    # Get prices
                    outcome_prices = market.get('outcomePrices', [])
                    if isinstance(outcome_prices, str):
                        import json
                        outcome_prices = json.loads(outcome_prices)
                    
                    # Debug price issues
                    if len(outcome_prices) < n and filtered_prices < 3:
                        logger.warning(f"Market {market.get('question', 'Unknown')[:50]} has {n} outcomes but {len(outcome_prices)} prices")
                    
                    # In debug mode, handle missing prices gracefully; otherwise filter
                    if not show_all:
                        if len(outcome_prices) < n:
                            filtered_prices += 1
                            continue
                    else:
                        # Debug mode: pad with zeros if missing prices
                        if len(outcome_prices) < n:
                            outcome_prices = outcome_prices + [0.0] * (n - len(outcome_prices))
                    
                    # Handle edge case: no outcomes at all
                    if n == 0:
                        if not show_all:
                            filtered_outcomes += 1
                            continue
                        else:
                            # Debug mode: create dummy binary market
                            outcomes = ['YES', 'NO']
                            outcome_prices = [0.5, 0.5]
                            n = 2
                    
                    outcome_prices = [float(p) if p else 0.0 for p in outcome_prices[:max(n, len(outcome_prices))]]
                    if len(outcome_prices) < n:
                        outcome_prices = outcome_prices + [0.0] * (n - len(outcome_prices))
                    
                    # Get volume (for display only, not filtering)
                    volume = float(market.get('volume') or 0)
                    
                    processed += 1
                    
                    # Get bid/ask - handle binary vs multi-outcome
                    best_bid = market.get('bestBid')
                    best_ask = market.get('bestAsk')
                    
                    if n == 2 and best_bid is not None and best_ask is not None:
                        # Binary market with actual bid/ask
                        yes_bid = float(best_bid)
                        yes_ask = float(best_ask)
                        # NO bid/ask are complements
                        no_bid = 1.0 - yes_ask  # Selling NO = buying YES at ask
                        no_ask = 1.0 - yes_bid  # Buying NO = selling YES at bid
                        best_bids = [yes_bid, no_bid]
                        best_asks = [yes_ask, no_ask]
                    else:
                        # Multi-outcome or no bid/ask data - estimate spread
                        liquidity = float(market.get('liquidity') or 0)
                        spread_estimate = 0.02 if liquidity > 10000 else 0.03
                        
                        best_bids = [max(0.001, p - spread_estimate/2) for p in outcome_prices]
                        best_asks = [min(0.999, p + spread_estimate/2) for p in outcome_prices]
                    
                    # Calculate ALL arbitrage opportunities
                    arb_result = calculate_arbitrage_opportunities(
                        outcomes, outcome_prices, best_bids, best_asks
                    )
                    
                    # Calculate inefficiency score
                    ineff_score = calculate_inefficiency_score(arb_result)
                    
                    # Filter: only include if profitable OR show_all is True
                    if not show_all and not arb_result['has_arbitrage']:
                        continue
                    
                    # Get market metadata
                    question = market.get('question', 'Unknown')
                    slug = market.get('slug', '')
                    url = f"https://polymarket.com/market/{slug}"
                    liquidity = float(market.get('liquidity') or 0)
                    
                    # Expiration
                    end_date = market.get('endDate') or market.get('end_date_iso')
                    hours_to_expiry = None
                    if end_date:
                        try:
                            from datetime import datetime, timezone
                            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                            now = datetime.now(timezone.utc)
                            hours_to_expiry = (end_dt - now).total_seconds() / 3600
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to parse end_date '{end_date}': {e}")
                    
                    results.append({
                        'question': question,
                        'slug': slug,
                        'url': url,
                        'n_outcomes': n,
                        'outcomes': outcomes,
                        'outcome_prices': outcome_prices,
                        'best_bids': best_bids,
                        'best_asks': best_asks,
                        'volume': volume,
                        'liquidity': liquidity,
                        'hours_to_expiry': hours_to_expiry,
                        'arb_result': arb_result,
                        'has_arbitrage': arb_result['has_arbitrage'],
                        'max_profit': arb_result['max_profit'],
                        'max_profit_pct': arb_result['max_profit_pct'],
                        'best_strategy': arb_result['best_opportunity']['strategy'] if arb_result['best_opportunity'] else None,
                        'inefficiency_score': ineff_score,
                        'bid_sum': arb_result['total_bid_sum'],
                        'ask_sum': arb_result['total_ask_sum'],
                        'mid_sum': arb_result['mid_sum'],
                        'overround_mid': arb_result['overround_mid'],
                        'non_exclusive_warning': arb_result.get('non_exclusive_warning', False)
                    })
                    
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        logger.warning(f"Error processing market: {e}")
                    continue
            
            # Sort by inefficiency score (highest first)
            results.sort(key=lambda x: x['inefficiency_score'], reverse=True)
            
            arb_count = sum(1 for r in results if r['has_arbitrage'])
            logger.info(f"Found {len(results)} markets, {arb_count} with arbitrage opportunities")
            logger.info(f"Filters applied: {filtered_outcomes} by outcomes, {filtered_prices} by prices, {errors} errors")
            logger.info(f"Processed {processed} markets, {len(results)} included in results")
            
            # Store filter stats for display
            if results or show_all:
                filter_stats = {
                    'total_fetched': len(markets),
                    'filtered_outcomes': filtered_outcomes,
                    'filtered_prices': filtered_prices,
                    'processed': processed,
                    'included': len(results),
                    'with_arbitrage': arb_count
                }
                # Attach to first result if exists
                if results:
                    results[0]['_filter_stats'] = filter_stats
                else:
                    # Create a dummy entry to hold stats
                    results.append({'_filter_stats': filter_stats, '_is_stats_only': True})
            
            return results
    
    return asyncio.run(fetch())


def render_arbitrage_scanner():
    """Render the Arbitrage Scanner dashboard."""
    
    st.markdown('<h2 style="margin-top: -1rem; margin-bottom: 0.3rem;">⚖️ Arbitrage Scanner</h2>', unsafe_allow_html=True)
    st.caption("Rigorous analysis of all BID/ASK combinations for guaranteed profit opportunities")
    
    # Sidebar settings
    with st.sidebar:
        st.markdown("---")
        st.markdown("### ⚙️ Arbitrage Settings")
        
        min_outcomes = st.slider("Min Outcomes", 2, 10, 2)
        
        # Min Profit filter with discrete steps
        profit_steps = [1, 10, 25, 50, 100, 250, 500]
        min_profit_idx = st.select_slider(
            "Min Profit ($)",
            options=range(len(profit_steps)),
            value=0,  # Default to $1 (index 0)
            format_func=lambda i: f"${profit_steps[i]}",
            help="Minimum absolute profit in dollars"
        )
        min_profit = profit_steps[min_profit_idx]
        
        limit = st.number_input("Max Markets", 50, 5000, 1000)
        
        st.markdown("---")
        
        # DEBUG TOGGLE - shows non-profitable too
        debug_mode = st.checkbox(
            "🐛 Debug Mode (Show All)",
            value=False,
            help="Show ALL markets including non-profitable ones to understand the data feed"
        )
        
        st.markdown("---")
        st.markdown("**Strategy Types:**")
        st.markdown("""
        - **BUY_ALL**: Buy every outcome
        - **SELL_ALL**: Sell every outcome  
        - **CROSS_n**: Sell one + buy rest
        - **SYNTH**: YES/NO synthetic arb
        """)
        
        st.markdown("---")
        st.markdown("**Math Verification:**")
        st.markdown("""
        ✓ Exactly ONE outcome = $1  
        ✓ All others = $0  
        ✓ P&L calculated for ALL scenarios  
        ✓ Only guaranteed profits shown
        """)
        
        st.markdown("---")
        st.warning("""
        **⚠️ Important:** This scanner assumes **mutually exclusive** outcomes (only ONE can win).
        
        **Does NOT work for:**
        - Range markets (e.g., ">2%" AND ">3%")
        - Overlapping thresholds
        - Non-exclusive conditions
        
        Markets flagged with ⚠️ may have multiple winners.
        """)
    
    # Scan controls
    col_scan, col_sort, col_stats = st.columns([1.5, 2, 2])
    
    with col_scan:
        scan_clicked = st.button("🔍 Scan Markets", type="primary", use_container_width=True)
    
    with col_sort:
        if 'arb_results' in st.session_state and st.session_state['arb_results']:
            sort_method = st.selectbox(
                "Sort:",
                ["Profit %", "Inefficiency Score", "Book Sum", "# Outcomes", "Volume"],
                index=0,
                label_visibility="collapsed"
            )
            st.session_state['arb_sort'] = sort_method
    
    with col_stats:
        if 'arb_results' in st.session_state:
            results = st.session_state['arb_results']
            # Filter out stats-only entry
            real_results = [r for r in results if not r.get('_is_stats_only', False)]
            scan_time = st.session_state.get('arb_time', datetime.now())
            arb_count = sum(1 for r in real_results if r.get('has_arbitrage', False))
            
            if debug_mode:
                msg = f'📊 {len(real_results)} markets ({arb_count} profitable)'
            else:
                msg = f'✅ {arb_count} arbitrage opportunities'
            
            st.markdown(
                f'<div style="padding: 0.4rem; background: #d4edda; color: #155724; '
                f'border-radius: 0.25rem;">{msg} @ {scan_time.strftime("%H:%M:%S")}</div>',
                unsafe_allow_html=True
            )
    
    # Handle scan
    if scan_clicked:
        with st.spinner("Scanning all bid/ask combinations..."):
            try:
                results = scan_arbitrage_markets(
                    min_outcomes=min_outcomes,
                    limit=limit,
                    show_all=debug_mode
                )
                st.session_state['arb_results'] = results
                st.session_state['arb_time'] = datetime.now()
                st.session_state['arb_min_profit'] = min_profit
                st.rerun()
            except Exception as e:
                logger.error(f"Scan error: {e}", exc_info=True)
                st.error(f"Error: {str(e)}")
                return
    
    # Display results
    if 'arb_results' in st.session_state:
        results = st.session_state['arb_results']
        min_profit_filter = st.session_state.get('arb_min_profit', 1)
        
        if results:
            display_arbitrage_results(results, debug_mode, min_profit_filter)
        else:
            if debug_mode:
                st.warning("No markets found matching filters.")
            else:
                st.info("🎯 No arbitrage opportunities found. This is expected - markets are usually efficient!")
                st.caption("Enable 'Debug Mode' to see all markets and understand pricing.")


def display_arbitrage_results(results: List[Dict], debug_mode: bool, min_profit: float = 1):
    """Display arbitrage analysis results."""
    
    # Check for filter stats and display them in debug mode
    filter_stats = None
    if results and '_filter_stats' in results[0]:
        filter_stats = results[0]['_filter_stats']
        # Remove stats-only entry if exists
        if results[0].get('_is_stats_only'):
            results = results[1:]
    
    # Also filter any other stats entries that might exist
    results = [r for r in results if not r.get('_is_stats_only', False)]
    
    # Apply min profit filter (convert to absolute dollars)
    filtered_count = len(results)
    if not debug_mode:
        # Only filter in non-debug mode
        results = [r for r in results if r.get('max_profit', 0) >= (min_profit / 100.0)]
        filtered_by_profit = filtered_count - len(results)
    else:
        filtered_by_profit = 0
    
    if debug_mode and filter_stats:
        st.info(
            f"📊 **Scan Statistics:** "
            f"Fetched {filter_stats['total_fetched']} markets | "
            f"Filtered: {filter_stats['filtered_outcomes']} (outcomes), "
            f"{filter_stats['filtered_prices']} (prices) | "
            f"Processed: {filter_stats['processed']} | "
            f"Results: {filter_stats['included']} (Arb: {filter_stats['with_arbitrage']})"
        )
    
    if filtered_by_profit > 0:
        st.caption(f"🔽 {filtered_by_profit} markets filtered by min profit ${min_profit}")
    
    # Check if we have any real results after filtering
    if not results:
        if debug_mode:
            st.warning("No markets found. Try adjusting filters (especially Min Volume).")
        else:
            st.warning(f"No arbitrage opportunities with profit ≥ ${min_profit}. Try lowering Min Profit filter.")
        return
    
    # Apply sorting
    sort_method = st.session_state.get('arb_sort', 'Profit %')
    
    if sort_method == "Profit %":
        results = sorted(results, key=lambda x: x['max_profit_pct'], reverse=True)
    elif sort_method == "Inefficiency Score":
        results = sorted(results, key=lambda x: x['inefficiency_score'], reverse=True)
    elif sort_method == "Book Sum":
        results = sorted(results, key=lambda x: abs(x['mid_sum'] - 1.0), reverse=True)
    elif sort_method == "# Outcomes":
        results = sorted(results, key=lambda x: x['n_outcomes'], reverse=True)
    elif sort_method == "Volume":
        results = sorted(results, key=lambda x: x['volume'], reverse=True)
    
    # Summary metrics
    profitable = [r for r in results if r.get('has_arbitrage', False)]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Markets Scanned", len(results))
    with col2:
        st.metric("Arbitrage Found", len(profitable))
    with col3:
        if profitable:
            max_p = max(r['max_profit_pct'] for r in profitable)
            st.metric("Best Profit", f"{max_p:.3f}%")
        else:
            st.metric("Best Profit", "0%")
    with col4:
        avg_book = sum(r['mid_sum'] for r in results) / len(results) if results else 1.0
        st.metric("Avg Book Sum", f"{avg_book:.2%}")
    
    st.markdown("---")
    
    # Build table
    html = """
    <style>
        .arb-tbl { width:100%; border-collapse:collapse; font-size:0.82rem; font-family:monospace; }
        .arb-tbl th { background:#1a252f; color:#fff; padding:6px; text-align:left; }
        .arb-tbl td { padding:5px 6px; border-bottom:1px solid #ddd; }
        .arb-tbl tr:nth-child(even) { background:#f5f5f5; }
        .arb-tbl tr:hover { background:#e3f2fd; }
        .arb-tbl a { color:#1976d2; text-decoration:none; }
        .arb-tbl a:hover { text-decoration:underline; }
        .profit { color:#2e7d32; font-weight:600; }
        .no-profit { color:#9e9e9e; }
        .book-over { color:#c62828; }
        .book-under { color:#2e7d32; }
        .book-ok { color:#1976d2; }
    </style>
    <table class="arb-tbl">
        <tr>
            <th>Market</th>
            <th>N</th>
            <th>Σ Bid</th>
            <th>Σ Ask</th>
            <th>Book</th>
            <th>Strategy</th>
            <th>Profit</th>
            <th>Volume</th>
        </tr>
    """
    
    for r in results[:100]:
        q = r['question'][:50] + "..." if len(r['question']) > 50 else r['question']
        
        # Add warning icon if non-exclusive
        if r.get('non_exclusive_warning', False):
            q = "⚠️ " + q
        
        url = r['url']
        
        n = r['n_outcomes']
        bid_sum = r['bid_sum']
        ask_sum = r['ask_sum']
        mid_sum = r['mid_sum']
        
        # Book sum coloring
        if mid_sum > 1.02:
            book_class = "book-over"
        elif mid_sum < 0.98:
            book_class = "book-under"
        else:
            book_class = "book-ok"
        
        # Profit
        if r['has_arbitrage']:
            profit_str = f'<span class="profit">+{r["max_profit_pct"]:.3f}%</span>'
            strategy = r['best_strategy'] or '-'
        else:
            profit_str = '<span class="no-profit">-</span>'
            strategy = '-'
        
        # Volume
        vol = r['volume']
        vol_str = f"${vol/1e6:.1f}M" if vol >= 1e6 else f"${vol/1e3:.0f}K" if vol >= 1000 else f"${vol:.0f}"
        
        html += f"""
        <tr>
            <td><a href="{url}" target="_blank">{q}</a></td>
            <td>{n}</td>
            <td>{bid_sum:.3f}</td>
            <td>{ask_sum:.3f}</td>
            <td class="{book_class}">{mid_sum:.3f}</td>
            <td>{strategy}</td>
            <td>{profit_str}</td>
            <td>{vol_str}</td>
        </tr>
        """
    
    html += "</table>"
    
    import streamlit.components.v1 as components
    components.html(html, height=min(len(results) * 32 + 80, 800), scrolling=True)
    
    # Detailed view for profitable opportunities
    if profitable:
        st.markdown("---")
        st.markdown("### 📋 Detailed Arbitrage Analysis")
        
        for i, r in enumerate(profitable[:10], 1):
            arb = r['arb_result']
            best = arb['best_opportunity']
            
            with st.expander(f"#{i} {r['question'][:60]}... → +{r['max_profit_pct']:.3f}%"):
                # Warning for non-exclusive outcomes
                if r.get('non_exclusive_warning', False):
                    st.error("⚠️ **WARNING:** This market may have NON-MUTUALLY EXCLUSIVE outcomes. Multiple outcomes could resolve to YES, invalidating arbitrage math. Verify manually!")
                
                # Market info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Outcomes:** {r['n_outcomes']}")
                    st.markdown(f"**Volume:** ${r['volume']:,.0f}")
                with col2:
                    st.markdown(f"**Σ Bids:** {r['bid_sum']:.4f}")
                    st.markdown(f"**Σ Asks:** {r['ask_sum']:.4f}")
                with col3:
                    st.markdown(f"**Book Sum:** {r['mid_sum']:.4f}")
                    st.markdown(f"[View Market]({r['url']})")
                
                st.markdown("---")
                
                # Best opportunity
                st.markdown("**✅ BEST STRATEGY:**")
                st.success(f"**{best['strategy']}**: {best['description']}")
                st.markdown(f"**Formula:** `{best['formula']}`")
                st.markdown(f"**Guaranteed Profit:** ${best['profit']:.4f} ({best['profit_pct']:.3f}%)")
                
                # Execution steps
                st.markdown("**Execution:**")
                exec_df = []
                for step in best['execution']:
                    outcome_name = str(step['outcome']) if step['outcome'] else 'Unknown'
                    exec_df.append({
                        'Action': step['side'],
                        'Outcome': outcome_name,
                        'Price': f"${step['price']:.4f}"
                    })
                st.dataframe(exec_df, use_container_width=True, hide_index=True)
                
                # All strategies analysis
                st.markdown("---")
                st.markdown("**All Strategies Analyzed:**")
                
                strat_data = []
                for opp in arb['opportunities']:
                    strat_data.append({
                        'Strategy': opp['strategy'],
                        'Description': opp['description'][:40],
                        'Profit': f"${opp['profit']:.4f}",
                        'Profitable': '✅' if opp['is_profitable'] else '❌'
                    })
                st.dataframe(strat_data, use_container_width=True, hide_index=True)
                
                # Outcome breakdown
                st.markdown("---")
                st.markdown("**Outcome Prices:**")
                
                outcome_data = []
                for j, (name, price, bid, ask) in enumerate(zip(
                    r['outcomes'], r['outcome_prices'], r['best_bids'], r['best_asks']
                )):
                    outcome_name = str(name) if name else f'Outcome {j+1}'
                    outcome_data.append({
                        'Outcome': outcome_name,
                        'Mid': f"{price:.2%}",
                        'Bid': f"{bid:.4f}",
                        'Ask': f"{ask:.4f}",
                        'Spread': f"{(ask-bid)*100:.2f}%"
                    })
                st.dataframe(outcome_data, use_container_width=True, hide_index=True)
    
    # Debug: show non-profitable analysis
    if debug_mode:
        non_profitable = [r for r in results if not r['has_arbitrage']]
        if non_profitable:
            st.markdown("---")
            st.markdown("### 🔍 Non-Profitable Markets (Debug)")
            st.caption("These markets are efficiently priced - no guaranteed profit exists")
            
            for r in non_profitable[:5]:
                with st.expander(f"{r['question'][:50]}... (Book: {r['mid_sum']:.3f})"):
                    st.markdown(f"**Σ Bids:** {r['bid_sum']:.4f} | **Σ Asks:** {r['ask_sum']:.4f}")
                    
                    arb = r['arb_result']
                    st.markdown("**Why no arbitrage:**")
                    
                    # Show why each strategy fails
                    for opp in arb['opportunities'][:4]:
                        if not opp['is_profitable']:
                            st.markdown(f"- **{opp['strategy']}**: {opp['formula']} → Loss of ${abs(opp['profit']):.4f}")


if __name__ == "__main__":
    main()
