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
        margin-bottom: 0.3rem;
        margin-top: 0;
    }
    .compact-metric {
        text-align: center;
        padding: 0.5rem;
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
        padding: 0.4rem 0;
        border-bottom: 1px solid #ecf0f1;
    }
    .market-row:hover {
        background-color: #f8f9fa;
    }
    h3 {
        margin-top: 0.5rem;
        margin-bottom: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Sidebar
    st.sidebar.title("🎯 Conviction Tracker")
    st.sidebar.markdown("Track high-conviction moves from top traders")
    st.sidebar.markdown("---")
    
    # Time window
    time_window = st.sidebar.selectbox(
        "⏱️ Time Window",
        ["Last 1 hour", "Last 6 hours", "Last 24 hours", "Last 3 days"],
        index=1
    )
    
    # Conviction filter
    min_conviction = st.sidebar.select_slider(
        "🎯 Min Conviction",
        options=["All", "Low+", "Moderate+", "High+", "Extreme"],
        value="All"
    )
    
    # Consensus filter
    min_consensus = st.sidebar.number_input(
        "👥 Min Users Agreeing",
        min_value=1,
        max_value=10,
        value=1,
        help="Show markets where at least N tracked users agree"
    )
    
    st.sidebar.markdown("---")
    
    # Tracked users display
    tracked_users = tracker.get_all_users()
    st.sidebar.markdown(f"### 👥 Tracked Traders ({len(tracked_users)})")
    for user in tracked_users:
        st.sidebar.markdown(f"• **{user['name']}**")
    
    st.sidebar.markdown("---")
    
    # Auto-refresh
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=True)
    
    if st.sidebar.button("🔄 Refresh Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Main content
    display_conviction_dashboard(
        time_window=time_window,
        min_conviction=min_conviction,
        min_consensus=min_consensus
    )
    
    # Auto-refresh logic
    if auto_refresh:
        import time
        time.sleep(30)
        st.rerun()


def display_conviction_dashboard(time_window: str, min_conviction: str, min_consensus: int):
    """Main dashboard view showing conviction-weighted markets."""
    
    st.markdown('<div class="main-header">🎯 High Conviction Signals</div>', unsafe_allow_html=True)
    
    tracked_users = tracker.get_all_users()
    if not tracked_users:
        st.warning("⚠️ No tracked users! Add traders to `tracked_users.csv`")
        return
    
    # Load and score trades
    with st.spinner("Analyzing tracked trader activity..."):
        trades = load_tracked_trades(time_window)
        
        if not trades:
            st.info("No recent activity from tracked users in this time window.")
            return
        
        # Score markets
        scorer = ConvictionScorer(tracker.get_wallet_addresses())
        scored_markets = scorer.score_markets(trades)
        
        # Apply filters
        conviction_thresholds = {
            "All": 0, "Low+": 5, "Moderate+": 10, "High+": 20, "Extreme": 50
        }
        min_score = conviction_thresholds.get(min_conviction, 0)
        
        filtered_markets = [
            m for m in scored_markets 
            if m['conviction_score'] >= min_score and m['consensus_count'] >= min_consensus
        ]
    
    # Filter out closed markets by checking market data
    open_markets = []
    for market in filtered_markets:
        market_data = get_market_data(market['slug'])
        if market_data is not None:  # None means market is closed/inactive
            open_markets.append(market)
    
    if not open_markets:
        st.info("No open markets found. All markets with activity are currently closed.")
        return
    
    # Table header
    st.markdown("### 📊 Markets by Conviction")
    header_col1, header_col2, header_col3, header_col4, header_col5, header_col6 = st.columns([3, 1, 1, 1, 1.5, 1.5])
    with header_col1:
        st.markdown("**Market**")
    with header_col2:
        st.markdown("**Conviction**")
    with header_col3:
        st.markdown("**Avg Entry**")
    with header_col4:
        st.markdown("**Last Price**")
    with header_col5:
        st.markdown("**YES Position**")
    with header_col6:
        st.markdown("**NO Position**")
    st.markdown('<div style="border-bottom: 2px solid #3498db; margin: 0.3rem 0 0.5rem 0;"></div>', unsafe_allow_html=True)
    
    for market in filtered_markets:
        display_market_card(market)


def calculate_entry_prices(market: Dict) -> Tuple[float, float]:
    """
    Calculate weighted average entry price and last execution price.
    
    Args:
        market: Market dictionary with trades and direction
        
    Returns:
        Tuple of (weighted_avg_entry_price, last_execution_price)
    """
    direction = market['direction']
    trades = market.get('trades', [])
    
    if not trades:
        return 0.0, 0.0
    
    # Filter trades for the dominant direction
    relevant_trades = []
    for trade in trades:
        side = trade.get('side', '').upper()
        outcome = trade.get('outcome', '').upper()
        
        is_bullish = (side == 'BUY' and 'YES' in outcome) or (side == 'SELL' and 'NO' in outcome)
        is_bearish = (side == 'BUY' and 'NO' in outcome) or (side == 'SELL' and 'YES' in outcome)
        
        if (direction == 'BULLISH' and is_bullish) or (direction == 'BEARISH' and is_bearish):
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



def display_market_card(market: Dict):
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
    
    # Fetch current market prices
    market_data = get_market_data(slug)
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
    
    # Calculate weighted average entry price and last execution price
    avg_entry, last_price = calculate_entry_prices(market)
    
    # Create compact row with container
    st.markdown('<div class="market-row">', unsafe_allow_html=True)
    col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1.5, 1.5])
    
    with col1:
        st.markdown(f"**[{slug[:80]}]({market_url})**")
        st.caption(f"👥 {users_display}")
    
    with col2:
        st.markdown(f"<span style='font-size: 0.85rem;'><strong>{level_name}</strong></span>", unsafe_allow_html=True)
        st.caption(f"Score: {score:.1f}")
    
    with col3:
        # Weighted average entry price
        if avg_entry > 0:
            entry_color = "#38ef7d" if direction == "BULLISH" else "#f45c43"
            st.markdown(f"<div style='text-align: center;'><span style='font-size: 0.95rem; font-weight: 600; color: {entry_color};'>{avg_entry:.1%}</span></div>", unsafe_allow_html=True)
            st.caption(f"👥 {market['consensus_count']} traders")
        else:
            st.markdown("—")
    
    with col4:
        # Last execution price
        if last_price > 0:
            st.markdown(f"<div style='text-align: center;'><span style='font-size: 0.95rem; font-weight: 600;'>{last_price:.1%}</span></div>", unsafe_allow_html=True)
            st.caption(f"{direction_emoji} {direction}")
        else:
            st.markdown("—")
    
    with col5:
        # YES position
        yes_bg = "rgba(56, 239, 125, 0.15)" if direction == "BULLISH" else "rgba(0,0,0,0.02)"
        st.markdown(f"""
        <div style="background: {yes_bg}; padding: 0.3rem; border-radius: 0.3rem; text-align: center;">
            <div style="font-size: 0.65rem; opacity: 0.7;">YES {yes_price:.0%}</div>
            <div style="font-size: 0.95rem; font-weight: 600; color: #38ef7d;">👥 {yes_traders}</div>
            <div style="font-size: 0.65rem; color: #7f8c8d;">${market['bullish_volume']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col6:
        # NO position
        no_bg = "rgba(244, 92, 67, 0.15)" if direction == "BEARISH" else "rgba(0,0,0,0.02)"
        st.markdown(f"""
        <div style="background: {no_bg}; padding: 0.3rem; border-radius: 0.3rem; text-align: center;">
            <div style="font-size: 0.65rem; opacity: 0.7;">NO {no_price:.0%}</div>
            <div style="font-size: 0.95rem; font-weight: 600; color: #f45c43;">👥 {no_traders}</div>
            <div style="font-size: 0.65rem; color: #7f8c8d;">${market['bearish_volume']:,.0f}</div>
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
    """Load trades for all tracked users."""
    
    minutes = parse_time_window(time_window)
    cutoff = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
    wallet_addresses = tracker.get_wallet_addresses()
    
    try:
        async def fetch():
            async with TradesClient() as client:
                all_trades = []
                for wallet in wallet_addresses:
                    trades = await client.get_user_trades(wallet, limit=200)
                    if trades:
                        for trade in trades:
                            if isinstance(trade, dict) and trade.get('timestamp', 0) >= cutoff:
                                all_trades.append(trade)
                return all_trades
        
        return asyncio.run(fetch())
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
                    return {
                        'yes_price': float(prices[0]) if prices else 0.5,
                        'no_price': float(prices[1]) if len(prices) > 1 else 0.5,
                        'volume': market.get('volume', 0),
                        'liquidity': market.get('liquidity', 0),
                        'active': is_active,
                        'closed': is_closed,
                    }
            return None
        
        return asyncio.run(fetch())
    except Exception as e:
        logger.debug(f"Could not fetch market data for {slug}: {e}")
        return None


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
