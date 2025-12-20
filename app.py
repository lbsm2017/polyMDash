"""
Polymarket Dashboard - Activity Tracking Focus
Real-time activity feed for tracked traders and markets.
"""

import streamlit as st
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="Polymarket Activity Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import clients
from clients.gamma_client import GammaClient
from clients.trades_client import TradesClient
from data.database import get_database
from utils.user_tracker import get_user_tracker

# Initialize
db = get_database()
tracker = get_user_tracker()

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .activity-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .buy-card {
        border-left-color: #2ecc71;
        background-color: #eafaf1;
    }
    .sell-card {
        border-left-color: #e74c3c;
        background-color: #fadbd8;
    }
    .metric-container {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Sidebar
    st.sidebar.title("📊 Activity Tracker")
    st.sidebar.markdown("---")
    
    # Mode selection
    tracking_mode = st.sidebar.radio(
        "Tracking Mode",
        ["👥 Tracked Users", "🌍 Global Activity"],
        help="Choose between your tracked users or global leaderboard"
    )
    
    # Time window
    time_window = st.sidebar.selectbox(
        "Time Window",
        ["Last 5 minutes", "Last 15 minutes", "Last hour", "Last 24 hours"],
        index=1
    )
    
    # Filters
    st.sidebar.markdown("### 🔍 Filters")
    show_buys = st.sidebar.checkbox("Show BUYs", value=True)
    show_sells = st.sidebar.checkbox("Show SELLs", value=True)
    
    outcome_filter = st.sidebar.multiselect(
        "Outcome Filter",
        ["YES", "NO", "Other"],
        default=["YES", "NO", "Other"]
    )
    
    # Auto-refresh
    st.sidebar.markdown("---")
    auto_refresh = st.sidebar.checkbox("Auto-refresh (15s)", value=False)
    
    if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Main content
    if tracking_mode == "👥 Tracked Users":
        show_tracked_activity(time_window, show_buys, show_sells, outcome_filter)
    else:
        show_global_activity(time_window, show_buys, show_sells, outcome_filter)
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(15)
        st.rerun()


def show_tracked_activity(time_window: str, show_buys: bool, show_sells: bool, outcome_filter: List[str]):
    """Display activity for tracked users."""
    
    tracked_users = tracker.get_all_users()
    
    if not tracked_users:
        st.warning("⚠️ No users tracked!")
        st.info("Add users to `tracked_users.json` to start tracking.")
        
        with st.expander("📝 Example tracked_users.json"):
            st.code('''
{
  "tracked_users": [
    {
      "name": "Trader Name",
      "wallet": "0x1234567890abcdef..."
    }
  ]
}
            ''', language="json")
        return
    
    st.markdown(f'<h1 class="main-header">👥 Tracked Users Activity</h1>', unsafe_allow_html=True)
    st.info(f"Tracking {len(tracked_users)} users · {time_window}")
    
    # Summary metrics
    with st.spinner("Loading activity..."):
        all_activity = load_tracked_users_activity(tracker.get_wallet_addresses(), time_window)
        
        if all_activity:
            display_activity_summary(all_activity)
            st.markdown("---")
            display_activity_feed(all_activity, show_buys, show_sells, outcome_filter, tracked_users=True)
        else:
            st.info("No recent activity from tracked users.")
    
    # User management
    with st.sidebar.expander("➕ Manage Users"):
        manage_tracked_users()


def show_global_activity(time_window: str, show_buys: bool, show_sells: bool, outcome_filter: List[str]):
    """Display global trading activity."""
    
    st.markdown(f'<h1 class="main-header">🌍 Global Trading Activity</h1>', unsafe_allow_html=True)
    st.info(f"Showing global activity · {time_window}")
    
    with st.spinner("Loading global activity..."):
        all_activity = load_global_activity(time_window)
        
        if all_activity:
            display_activity_summary(all_activity)
            st.markdown("---")
            display_activity_feed(all_activity, show_buys, show_sells, outcome_filter, tracked_users=False)
        else:
            st.info("No recent activity.")


def display_activity_summary(activities: List[Dict]):
    """Display summary metrics for activities."""
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Calculate metrics
    total_trades = len(activities)
    buys = [a for a in activities if a.get('side') == 'BUY']
    sells = [a for a in activities if a.get('side') == 'SELL']
    
    total_volume = sum(float(a.get('price', 0)) * float(a.get('size', 0)) for a in activities)
    
    yes_trades = [a for a in activities if a.get('outcome', '').upper() == 'YES']
    no_trades = [a for a in activities if a.get('outcome', '').upper() == 'NO']
    
    unique_markets = len(set(a.get('slug') for a in activities if a.get('slug')))
    
    with col1:
        st.metric("Total Trades", total_trades)
    
    with col2:
        st.metric("🟢 BUYs", len(buys), help="Total buy orders")
    
    with col3:
        st.metric("🔴 SELLs", len(sells), help="Total sell orders")
    
    with col4:
        st.metric("Total Volume", f"${total_volume:,.0f}")
    
    with col5:
        st.metric("Markets", unique_markets)
    
    # YES/NO breakdown
    col1, col2, col3 = st.columns(3)
    
    with col1:
        yes_pct = (len(yes_trades) / max(total_trades, 1)) * 100
        st.metric("YES Trades", len(yes_trades), f"{yes_pct:.1f}%")
    
    with col2:
        no_pct = (len(no_trades) / max(total_trades, 1)) * 100
        st.metric("NO Trades", len(no_trades), f"{no_pct:.1f}%")
    
    with col3:
        other = total_trades - len(yes_trades) - len(no_trades)
        st.metric("Other Outcomes", other)


def display_activity_feed(
    activities: List[Dict],
    show_buys: bool,
    show_sells: bool,
    outcome_filter: List[str],
    tracked_users: bool = False
):
    """Display activity feed with filters."""
    
    st.subheader("📋 Recent Activity Feed")
    
    # Filter activities
    filtered = activities.copy()
    
    if not show_buys:
        filtered = [a for a in filtered if a.get('side') != 'BUY']
    if not show_sells:
        filtered = [a for a in filtered if a.get('side') != 'SELL']
    
    # Outcome filter
    if outcome_filter:
        filtered = [a for a in filtered if categorize_outcome(a.get('outcome', '')) in outcome_filter]
    
    if not filtered:
        st.info("No trades match your filters.")
        return
    
    # Group by market for better UX
    view_mode = st.radio("View Mode", ["📊 By Trade", "🗂️ By Market"], horizontal=True)
    
    if view_mode == "📊 By Trade":
        display_trades_list(filtered, tracked_users)
    else:
        display_trades_by_market(filtered, tracked_users)


def display_trades_list(trades: List[Dict], tracked_users: bool):
    """Display trades as a chronological list."""
    
    for i, trade in enumerate(trades[:50]):  # Limit to 50 most recent
        side = trade.get('side', 'UNKNOWN')
        outcome = trade.get('outcome', 'Unknown')
        outcome_cat = categorize_outcome(outcome)
        
        # Card styling based on side
        card_class = "buy-card" if side == 'BUY' else "sell-card"
        
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # User info
                user_wallet = trade.get('proxyWallet', 'Unknown')
                user_name = tracker.get_user_name(user_wallet) if tracked_users else f"{user_wallet[:6]}...{user_wallet[-4:]}"
                
                # Market question
                market_slug = trade.get('slug', 'Unknown Market')
                
                st.markdown(f"""
                <div class="activity-card {card_class}">
                    <strong>{'🟢 BUY' if side == 'BUY' else '🔴 SELL'}</strong> · 
                    <strong>{outcome_cat}</strong> · 
                    {user_name}
                    <br/>
                    <small>{market_slug[:80]}...</small>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                price = float(trade.get('price', 0))
                size = float(trade.get('size', 0))
                st.metric("Price", f"{price:.3f}")
                st.caption(f"Size: {size:.1f}")
            
            with col3:
                volume = price * size
                st.metric("Volume", f"${volume:.2f}")
                
                # Timestamp
                timestamp = trade.get('timestamp', '')
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        st.caption(f"{format_time_ago(dt)}")
                    except:
                        pass
        
        if i < len(trades) - 1:
            st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #eee;'/>", unsafe_allow_html=True)


def display_trades_by_market(trades: List[Dict], tracked_users: bool):
    """Display trades grouped by market."""
    
    # Group by market
    markets = {}
    for trade in trades:
        slug = trade.get('slug', 'Unknown')
        if slug not in markets:
            markets[slug] = []
        markets[slug].append(trade)
    
    # Sort markets by number of trades
    sorted_markets = sorted(markets.items(), key=lambda x: len(x[1]), reverse=True)
    
    for market_slug, market_trades in sorted_markets[:20]:  # Top 20 markets
        with st.expander(f"**{market_slug[:80]}...** ({len(market_trades)} trades)", expanded=False):
            
            # Market summary
            buys = len([t for t in market_trades if t.get('side') == 'BUY'])
            sells = len([t for t in market_trades if t.get('side') == 'SELL'])
            total_vol = sum(float(t.get('price', 0)) * float(t.get('size', 0)) for t in market_trades)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("🟢 BUYs", buys)
            col2.metric("🔴 SELLs", sells)
            col3.metric("Volume", f"${total_vol:.2f}")
            
            # Recent trades for this market
            st.markdown("**Recent Trades:**")
            for trade in market_trades[:10]:
                side = trade.get('side')
                outcome = categorize_outcome(trade.get('outcome', ''))
                price = float(trade.get('price', 0))
                size = float(trade.get('size', 0))
                user = trade.get('proxyWallet', '')
                user_name = tracker.get_user_name(user) if tracked_users else f"{user[:6]}...{user[-4:]}"
                
                side_emoji = "🟢" if side == 'BUY' else "🔴"
                st.caption(f"{side_emoji} {side} {outcome} · {price:.3f} × {size:.1f} · {user_name}")


def categorize_outcome(outcome: str) -> str:
    """Categorize outcome into YES/NO/Other."""
    outcome_upper = outcome.upper()
    if 'YES' in outcome_upper:
        return 'YES'
    elif 'NO' in outcome_upper:
        return 'NO'
    else:
        return 'Other'


def format_time_ago(dt: datetime) -> str:
    """Format datetime as 'X ago'."""
    diff = datetime.now() - dt.replace(tzinfo=None)
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds >= 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds >= 60:
        return f"{diff.seconds // 60}m ago"
    else:
        return "just now"


def manage_tracked_users():
    """User management interface."""
    
    # Add new user
    st.markdown("**Add New User**")
    new_name = st.text_input("Name", key="new_user_name")
    new_wallet = st.text_input("Wallet", key="new_user_wallet")
    
    if st.button("➕ Add"):
        if new_name and new_wallet:
            if tracker.add_user(new_name, new_wallet):
                st.success(f"Added {new_name}")
                st.rerun()
            else:
                st.error("Already exists")
    
    # List current users
    st.markdown("**Current Users**")
    for user in tracker.get_all_users():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"**{user['name']}**")
            st.caption(f"`{user['wallet'][:12]}...`")
        with col2:
            if st.button("🗑️", key=f"del_{user['wallet']}"):
                tracker.remove_user(user['wallet'])
                st.rerun()


@st.cache_data(ttl=15)
def load_tracked_users_activity(wallet_addresses: List[str], time_window: str) -> List[Dict]:
    """Load activity for tracked users."""
    
    minutes = parse_time_window(time_window)
    
    try:
        async def fetch():
            async with TradesClient() as client:
                all_trades = []
                for wallet in wallet_addresses:
                    trades = await client.get_user_trades(wallet, limit=100)
                    all_trades.extend(trades)
                return all_trades
        
        trades = asyncio.run(fetch())
        
        # Filter by time window
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent_trades = []
        
        for trade in trades:
            try:
                trade_time = datetime.fromisoformat(trade.get('timestamp', '').replace('Z', '+00:00'))
                if trade_time.replace(tzinfo=None) >= cutoff:
                    recent_trades.append(trade)
            except:
                continue
        
        # Sort by timestamp desc
        recent_trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return recent_trades
        
    except Exception as e:
        logger.error(f"Error loading tracked user activity: {e}")
        return []


@st.cache_data(ttl=15)
def load_global_activity(time_window: str) -> List[Dict]:
    """Load global trading activity."""
    
    minutes = parse_time_window(time_window)
    
    try:
        async def fetch():
            async with TradesClient() as client:
                return await client.get_recent_activity(minutes=minutes, limit=500)
        
        return asyncio.run(fetch())
        
    except Exception as e:
        logger.error(f"Error loading global activity: {e}")
        return []


def parse_time_window(window: str) -> int:
    """Parse time window string to minutes."""
    mapping = {
        "Last 5 minutes": 5,
        "Last 15 minutes": 15,
        "Last hour": 60,
        "Last 24 hours": 1440
    }
    return mapping.get(window, 15)


if __name__ == "__main__":
    main()
