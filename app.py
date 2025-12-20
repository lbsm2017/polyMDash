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
        ["Last 5 minutes", "Last 15 minutes", "Last hour", "Last 6 hours", "Last 24 hours"],
        index=3  # Default to Last 6 hours
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
    view_mode = st.radio("View Mode", ["📊 By Trade", "🗂️ By Market"], horizontal=True, index=1)
    
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
                timestamp = trade.get('timestamp', 0)
                if timestamp:
                    try:
                        dt = datetime.fromtimestamp(timestamp)
                        st.caption(f"{format_time_ago(dt)}")
                    except:
                        pass
        
        if i < len(trades) - 1:
            st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #eee;'/>", unsafe_allow_html=True)


def display_trades_by_market(trades: List[Dict], tracked_users: bool):
    """Display trades grouped by market and action."""
    
    # Group by market and action
    markets = {}
    for trade in trades:
        slug = trade.get('slug', 'Unknown')
        side = trade.get('side', 'UNKNOWN')
        outcome = categorize_outcome(trade.get('outcome', ''))
        
        if slug not in markets:
            markets[slug] = {
                'BUY YES': [],
                'BUY NO': [],
                'SELL YES': [],
                'SELL NO': [],
                'OTHER': []
            }
        
        action_key = f"{side} {outcome}"
        if action_key in markets[slug]:
            markets[slug][action_key].append(trade)
        else:
            markets[slug]['OTHER'].append(trade)
    
    # Sort markets by total activity
    def get_market_score(item):
        slug, actions = item
        total_trades = sum(len(trades) for trades in actions.values())
        total_volume = sum(
            float(t.get('price', 0)) * float(t.get('size', 0)) 
            for trades in actions.values() 
            for t in trades
        )
        return (total_trades, total_volume)
    
    sorted_markets = sorted(markets.items(), key=get_market_score, reverse=True)
    
    # Display markets in compact format
    for market_slug, actions in sorted_markets[:25]:  # Top 25 markets
        total_trades = sum(len(trades) for trades in actions.values())
        if total_trades == 0:
            continue
        
        total_vol = sum(
            float(t.get('price', 0)) * float(t.get('size', 0)) 
            for trades in actions.values() 
            for t in trades
        )
        
        # Detect patterns for this market
        all_market_trades = [t for trades_list in actions.values() for t in trades_list]
        pattern_info = detect_market_patterns(all_market_trades)
        patterns = pattern_info.get('patterns', [])
        
        # Build header with pattern badges
        pattern_badges = ' '.join(patterns[:3]) if patterns else ''
        header_text = f"**{market_slug[:90]}** · {total_trades} trades · ${total_vol:.0f}"
        if pattern_badges:
            header_text += f" · {pattern_badges}"
        
        # Compact market header
        with st.expander(header_text, expanded=False):
            # Show all patterns if more than 3
            if len(patterns) > 3:
                st.info(' · '.join(patterns))
            elif patterns:
                st.info(' · '.join(patterns))
            
            # Action breakdown in compact grid
            action_order = ['BUY YES', 'BUY NO', 'SELL YES', 'SELL NO']
            action_colors = {
                'BUY YES': '🟢',
                'BUY NO': '🔴', 
                'SELL YES': '🔵',
                'SELL NO': '🟣'
            }
            
            # Show action summary
            cols = st.columns(4)
            for i, action in enumerate(action_order):
                trades_list = actions[action]
                if trades_list:
                    with cols[i]:
                        emoji = action_colors.get(action, '⚪')
                        vol = sum(float(t.get('price', 0)) * float(t.get('size', 0)) for t in trades_list)
                        st.metric(
                            f"{emoji} {action}",
                            len(trades_list),
                            f"${vol:.0f}"
                        )
            
            st.markdown("---")
            
            # Detailed trades by action
            for action in action_order:
                trades_list = actions[action]
                if not trades_list:
                    continue
                
                emoji = action_colors.get(action, '⚪')
                st.markdown(f"**{emoji} {action}** ({len(trades_list)} trades)")
                
                # Sort by timestamp desc
                trades_list.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                
                for trade in trades_list[:5]:  # Top 5 per action
                    price = float(trade.get('price', 0))
                    size = float(trade.get('size', 0))
                    volume = price * size
                    user = trade.get('proxyWallet', '')
                    user_name = tracker.get_user_name(user) if tracked_users else f"{user[:6]}...{user[-4:]}"
                    timestamp = trade.get('timestamp', 0)
                    
                    # Build indicators
                    indicators = []
                    if volume > 1000:
                        indicators.append('🔥')
                    if price > 0.9 or price < 0.1:
                        indicators.append('💎')
                    if 0.45 <= price <= 0.55:
                        indicators.append('🎯')
                    
                    if timestamp:
                        dt = datetime.fromtimestamp(timestamp)
                        time_ago = format_time_ago(dt)
                        hour = dt.hour
                        if 6 <= hour < 12:
                            indicators.append('🌅')
                        elif 18 <= hour < 24:
                            indicators.append('🌆')
                        elif hour < 6:
                            indicators.append('🌙')
                    else:
                        time_ago = ""
                    
                    indicator_str = ' '.join(indicators)
                    
                    st.caption(
                        f"💰 ${volume:.2f} ({price:.3f} × {size:.0f}) · "
                        f"👤 {user_name} · 🕒 {time_ago}"
                        f"{' · ' + indicator_str if indicator_str else ''}"
                    )
                
                if len(trades_list) > 5:
                    st.caption(f"... and {len(trades_list) - 5} more")


def categorize_outcome(outcome: str) -> str:
    """Categorize outcome into YES/NO/Other."""
    outcome_upper = outcome.upper()
    if 'YES' in outcome_upper:
        return 'YES'
    elif 'NO' in outcome_upper:
        return 'NO'
    else:
        return 'Other'


def detect_market_patterns(all_trades: List[Dict]) -> Dict[str, str]:
    """Detect interesting patterns in market trades."""
    if not all_trades:
        return {}
    
    patterns = []
    
    # Sort by timestamp
    sorted_trades = sorted(all_trades, key=lambda x: x.get('timestamp', 0))
    
    # Price trend (first vs last trade)
    if len(sorted_trades) >= 2:
        first_price = float(sorted_trades[0].get('price', 0))
        last_price = float(sorted_trades[-1].get('price', 0))
        price_change = (last_price - first_price) / max(first_price, 0.001)
        
        if abs(price_change) > 0.05:  # >5% change
            if price_change > 0:
                patterns.append('📈 Price trending UP')
            else:
                patterns.append('📉 Price trending DOWN')
    
    # High conviction trades (>$1000)
    high_value_trades = [
        t for t in all_trades 
        if float(t.get('price', 0)) * float(t.get('size', 0)) > 1000
    ]
    if high_value_trades:
        patterns.append(f'🔥 High conviction ({len(high_value_trades)} trades >$1K)')
    
    # Rapid fire (multiple trades within 5 min)
    rapid_fire_count = 0
    for i in range(len(sorted_trades) - 1):
        t1 = sorted_trades[i].get('timestamp', 0)
        t2 = sorted_trades[i + 1].get('timestamp', 0)
        if abs(t2 - t1) < 300:  # 5 minutes
            rapid_fire_count += 1
    if rapid_fire_count >= 3:
        patterns.append(f'⚡ Rapid fire ({rapid_fire_count} within 5min)')
    
    # Precise entry (price near 0.5)
    precise_entries = [
        t for t in all_trades
        if 0.45 <= float(t.get('price', 0)) <= 0.55
    ]
    if precise_entries:
        patterns.append(f'🎯 Precise entry ({len(precise_entries)} near 50/50)')
    
    # Diamond hands (price at extremes)
    extreme_trades = [
        t for t in all_trades
        if float(t.get('price', 0)) > 0.9 or float(t.get('price', 0)) < 0.1
    ]
    if extreme_trades:
        patterns.append(f'💎 Diamond hands ({len(extreme_trades)} at extremes)')
    
    # Calculate average volume for spike detection
    volumes = [float(t.get('price', 0)) * float(t.get('size', 0)) for t in all_trades]
    avg_volume = sum(volumes) / len(volumes) if volumes else 0
    max_volume = max(volumes) if volumes else 0
    
    if max_volume > avg_volume * 3:
        patterns.append('⚠️ Sudden spike (3x avg volume)')
    
    # Contrarian move (buy when mostly selling or vice versa)
    buys = [t for t in all_trades if t.get('side') == 'BUY']
    sells = [t for t in all_trades if t.get('side') == 'SELL']
    total = len(all_trades)
    
    if total > 5:  # Need enough trades to be meaningful
        buy_pct = len(buys) / total
        if buy_pct > 0.9 or buy_pct < 0.1:
            if buy_pct > 0.9:
                patterns.append('🚨 Contrarian alert (90%+ buying)')
            else:
                patterns.append('🚨 Contrarian alert (90%+ selling)')
    
    # FOMO alert (rapid sequence of same-side trades)
    if len(sorted_trades) >= 4:
        same_side_streak = 1
        max_streak = 1
        for i in range(1, len(sorted_trades)):
            if sorted_trades[i].get('side') == sorted_trades[i-1].get('side'):
                same_side_streak += 1
                max_streak = max(max_streak, same_side_streak)
            else:
                same_side_streak = 1
        if max_streak >= 4:
            patterns.append(f'🎪 FOMO alert ({max_streak} same-side in a row)')
    
    # Time-based activity
    morning = [t for t in all_trades if 6 <= datetime.fromtimestamp(t.get('timestamp', 0)).hour < 12]
    evening = [t for t in all_trades if 18 <= datetime.fromtimestamp(t.get('timestamp', 0)).hour < 24]
    night = [t for t in all_trades if datetime.fromtimestamp(t.get('timestamp', 0)).hour < 6]
    
    total_trades = len(all_trades)
    if morning and len(morning) / total_trades > 0.5:
        patterns.append('🌅 Mostly morning activity')
    if evening and len(evening) / total_trades > 0.5:
        patterns.append('🌆 Mostly evening activity')
    if night and len(night) / total_trades > 0.3:
        patterns.append('🌙 Late night activity')
    
    return {'patterns': patterns, 'trade_count': total}


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
    cutoff_timestamp = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
    
    try:
        async def fetch():
            async with TradesClient() as client:
                all_trades = []
                for wallet in wallet_addresses:
                    logger.info(f"Fetching trades for wallet: {wallet}")
                    trades = await client.get_user_trades(wallet, limit=100)
                    
                    # Check if trades is None or empty
                    if not trades:
                        logger.info(f"No trades returned for wallet: {wallet}")
                        continue
                    
                    logger.info(f"Got {len(trades)} trades for wallet: {wallet}")
                    
                    # Filter valid trades by timestamp
                    for trade in trades:
                        if not isinstance(trade, dict):
                            continue
                        
                        trade_ts = trade.get('timestamp', 0)
                        if trade_ts >= cutoff_timestamp:
                            all_trades.append(trade)
                
                logger.info(f"Total trades after filtering: {len(all_trades)}")
                return all_trades
        
        trades = asyncio.run(fetch())
        
        # Sort by timestamp desc
        trades.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return trades
        
    except Exception as e:
        logger.error(f"Error loading tracked user activity: {e}", exc_info=True)
        return []


@st.cache_data(ttl=15)
def load_global_activity(time_window: str) -> List[Dict]:
    """Load global trading activity."""
    
    minutes = parse_time_window(time_window)
    cutoff_timestamp = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
    
    try:
        async def fetch():
            async with TradesClient() as client:
                logger.info(f"Fetching global trades, limit=500")
                trades = await client.get_trades(limit=500)
                
                # Check if trades is None or empty
                if not trades:
                    logger.info("No global trades returned")
                    return []
                
                logger.info(f"Got {len(trades)} global trades")
                
                # Filter valid trades by timestamp
                recent_trades = []
                for trade in trades:
                    if not isinstance(trade, dict):
                        continue
                    
                    trade_ts = trade.get('timestamp', 0)
                    if trade_ts >= cutoff_timestamp:
                        recent_trades.append(trade)
                
                logger.info(f"Filtered to {len(recent_trades)} recent trades")
                return recent_trades
        
        return asyncio.run(fetch())
        
    except Exception as e:
        logger.error(f"Error loading global activity: {e}", exc_info=True)
        return []


def parse_time_window(window: str) -> int:
    """Parse time window string to minutes."""
    mapping = {
        "Last 5 minutes": 5,
        "Last 15 minutes": 15,
        "Last hour": 60,
        "Last 6 hours": 360,
        "Last 24 hours": 1440
    }
    return mapping.get(window, 360)


if __name__ == "__main__":
    main()
