"""
Polymarket Dashboard - Conviction-Weighted Tracker
Surfaces high-conviction trades from tracked users with consensus signals.
"""

import streamlit as st
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional, Tuple
import logging

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
    st.sidebar.title("🎯 Conviction Tracker")
    st.sidebar.markdown("Track high-conviction moves from top traders")
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
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=True)
    
    if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Main content
    display_conviction_dashboard()
    
    # Auto-refresh logic
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()


def display_conviction_dashboard():
    """Main dashboard view showing conviction-weighted markets."""
    
    st.markdown('<div class="main-header">📡 Traders Scanner</div>', unsafe_allow_html=True)
    
    tracked_users = tracker.get_all_users()
    if not tracked_users:
        st.warning("⚠️ No tracked users! Add traders to `tracked_users.csv`")
        return
    
    wallet_addresses = tracker.get_wallet_addresses()
    logger.info(f"Tracking {len(wallet_addresses)} wallets: {wallet_addresses[:3]}...")
    
    # Phase 1: Load trades with high-performance pool
    with st.spinner("Loading trader activity..."):
        # First fetch trades to get market slugs
        trades, _ = fetch_all_data(wallet_addresses, [], cutoff_minutes=1440)
        
        logger.info(f"Loaded {len(trades)} trades from API")
        
        if not trades:
            st.info("No recent activity from tracked users in the last 24 hours.")
            return
        
        # Score markets
        scorer = ConvictionScorer(wallet_addresses)
        scored_markets = scorer.score_markets(trades)
    
    # Phase 2: Fetch all market data in parallel
    with st.spinner("Fetching current prices..."):
        market_slugs = [m['slug'] for m in scored_markets]
        _, batch_market_data = fetch_all_data([], market_slugs, cutoff_minutes=1440)
    
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
    
    # Table header
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
    for wallet, data in user_positions.items():
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


if __name__ == "__main__":
    main()
