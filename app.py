"""
Polymarket Dashboard - Conviction-Weighted Tracker
Surfaces high-conviction trades from tracked users with consensus signals.
"""

import streamlit as st
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional
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
        font-size: 2.2rem;
        font-weight: bold;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .market-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .market-card.bullish {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .market-card.bearish {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
    }
    .conviction-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-weight: bold;
        font-size: 0.9rem;
        background: rgba(255,255,255,0.2);
    }
    .consensus-indicator {
        font-size: 1.5rem;
        font-weight: bold;
    }
    .price-box {
        background: rgba(255,255,255,0.15);
        padding: 0.75rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .user-chip {
        display: inline-block;
        background: rgba(255,255,255,0.25);
        padding: 0.2rem 0.6rem;
        border-radius: 1rem;
        margin: 0.2rem;
        font-size: 0.85rem;
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
    
    if st.sidebar.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Main content
    display_conviction_dashboard(
        time_window=time_window,
        min_conviction=min_conviction,
        min_consensus=min_consensus
    )


def display_conviction_dashboard(time_window: str, min_conviction: str, min_consensus: int):
    """Main dashboard view showing conviction-weighted markets."""
    
    st.markdown('<h1 class="main-header">🎯 High Conviction Signals</h1>', unsafe_allow_html=True)
    
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
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 Signals", len(filtered_markets))
    with col2:
        bullish = sum(1 for m in filtered_markets if m['direction'] == 'BULLISH')
        st.metric("📈 Bullish", bullish)
    with col3:
        bearish = sum(1 for m in filtered_markets if m['direction'] == 'BEARISH')
        st.metric("📉 Bearish", bearish)
    with col4:
        total_vol = sum(m['bullish_volume'] + m['bearish_volume'] for m in filtered_markets)
        st.metric("💰 Total Volume", f"${total_vol:,.0f}")
    
    st.markdown("---")
    
    # Display markets
    if not filtered_markets:
        st.info("No markets match your filters. Try lowering conviction threshold or expanding time window.")
        return
    
    for market in filtered_markets:
        display_market_card(market)


def display_market_card(market: Dict):
    """Display a single market conviction card."""
    
    direction = market['direction']
    score = market['conviction_score']
    slug = market['slug']
    
    # Get conviction level
    scorer = ConvictionScorer([])
    level_name, emoji = scorer.get_conviction_level(score)
    
    # Card styling
    card_class = "bullish" if direction == "BULLISH" else "bearish"
    direction_emoji = "📈" if direction == "BULLISH" else "📉"
    
    # Fetch current market prices
    market_data = get_market_data(slug)
    yes_price = market_data.get('yes_price', 0.5) if market_data else 0.5
    no_price = market_data.get('no_price', 0.5) if market_data else 0.5
    
    with st.container():
        # Header row
        col1, col2, col3 = st.columns([4, 1, 1])
        
        with col1:
            st.markdown(f"### {direction_emoji} {slug[:100]}")
            
            # Consensus users
            user_chips = ""
            for wallet in market['consensus_users'][:5]:
                name = tracker.get_user_name(wallet)
                user_chips += f'<span class="user-chip">👤 {name}</span> '
            
            st.markdown(f"""
            <div>
                <span class="conviction-badge">{level_name}</span>
                <span style="margin-left: 1rem;">
                    👥 <strong>{market['consensus_count']}</strong> traders agree
                </span>
            </div>
            <div style="margin-top: 0.5rem">{user_chips}</div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="price-box">
                <div style="font-size: 0.8rem; opacity: 0.8;">YES</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{yes_price:.0%}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="price-box">
                <div style="font-size: 0.8rem; opacity: 0.8;">NO</div>
                <div style="font-size: 1.5rem; font-weight: bold;">{no_price:.0%}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Volume breakdown
        st.markdown(f"""
        **Volume:** 📈 ${market['bullish_volume']:,.0f} bullish · 
        📉 ${market['bearish_volume']:,.0f} bearish · 
        🔄 {market['total_trades']} trades
        """)
        
        # Recent trades expandable
        with st.expander(f"📋 View {market['total_trades']} trades"):
            trades_sorted = sorted(
                market['trades'], 
                key=lambda x: x.get('timestamp', 0), 
                reverse=True
            )
            for trade in trades_sorted[:10]:
                display_trade_row(trade)
        
        st.markdown("---")


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
                    prices = market.get('outcomePrices', [0.5, 0.5])
                    if isinstance(prices, str):
                        import json
                        prices = json.loads(prices)
                    return {
                        'yes_price': float(prices[0]) if prices else 0.5,
                        'no_price': float(prices[1]) if len(prices) > 1 else 0.5,
                        'volume': market.get('volume', 0),
                        'liquidity': market.get('liquidity', 0),
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
