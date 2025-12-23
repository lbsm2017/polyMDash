"""
Validation script to debug Cardano ETF market data from API feed
"""
import asyncio
import logging
import json
from clients.gamma_client import GammaClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def validate_cardano_market():
    """Fetch and validate Cardano ETF market data"""
    
    market_slug = "cardano-etf-in-2025"
    
    async with GammaClient() as client:
        logger.info(f"Fetching market: {market_slug}")
        logger.info("=" * 80)
        
        # Try multiple search strategies
        all_markets = []
        
        # Strategy 1: Fetch with different sorting
        for order_by in ["", "volume", "liquidity"]:
            try:
                logger.info(f"Fetching with order_by='{order_by}'...")
                markets = await client.get_markets(limit=1000, active=True, closed=False, order_by=order_by)
                all_markets.extend(markets)
                logger.info(f"  Got {len(markets)} markets")
            except Exception as e:
                logger.warning(f"  Failed: {e}")
        
        # Deduplicate
        seen = set()
        markets = []
        for m in all_markets:
            slug = m.get('slug', '')
            if slug and slug not in seen:
                seen.add(slug)
                markets.append(m)
        
        logger.info(f"\nTotal unique markets: {len(markets)}")
        
        # Search for Cardano
        cardano_market = None
        for market in markets:
            slug = market.get('slug', '')
            question = market.get('question', '').lower()
            
            # Check slug match
            if slug == market_slug or 'cardano' in slug.lower():
                logger.info(f"✓ Found by slug: {slug}")
                cardano_market = market
                break
            
            # Check question match
            if 'cardano' in question and 'etf' in question:
                logger.info(f"✓ Found by question: {market.get('question')}")
                logger.info(f"  Slug: {slug}")
                cardano_market = market
                break
        
        if not cardano_market:
            logger.error(f"❌ Market not found! Showing all markets with 'cardano' or 'ada':")
            for market in markets:
                question = market.get('question', '').lower()
                slug = market.get('slug', '').lower()
                if 'cardano' in question or 'cardano' in slug or 'ada' in question or ' ada ' in question:
                    logger.info(f"  - {market.get('question')} | slug: {market.get('slug')}")
            
            logger.error("No Cardano ETF market found in any form!")
            return
        
        # Print ALL fields
        logger.info("\n" + "=" * 80)
        logger.info("📊 FULL MARKET DATA")
        logger.info("=" * 80)
        for key, value in cardano_market.items():
            logger.info(f"{key}: {value}")
        
        # Parse and validate key fields
        logger.info("\n" + "=" * 80)
        logger.info("🔍 PARSED FIELDS")
        logger.info("=" * 80)
        
        # Question
        question = cardano_market.get('question', 'Unknown')
        logger.info(f"Question: {question}")
        
        # Slug
        slug = cardano_market.get('slug', '')
        logger.info(f"Slug: {slug}")
        
        # Outcomes
        outcomes = cardano_market.get('outcomes', [])
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        logger.info(f"Outcomes (raw): {cardano_market.get('outcomes')}")
        logger.info(f"Outcomes (parsed): {outcomes}")
        logger.info(f"Number of outcomes: {len(outcomes)}")
        
        # Outcome Prices
        outcome_prices = cardano_market.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            outcome_prices = json.loads(outcome_prices)
        logger.info(f"OutcomePrices (raw): {cardano_market.get('outcomePrices')}")
        logger.info(f"OutcomePrices (parsed): {outcome_prices}")
        logger.info(f"Number of prices: {len(outcome_prices)}")
        
        # Bid/Ask
        best_bid = cardano_market.get('bestBid')
        best_ask = cardano_market.get('bestAsk')
        logger.info(f"BestBid: {best_bid} (type: {type(best_bid)})")
        logger.info(f"BestAsk: {best_ask} (type: {type(best_ask)})")
        
        # Volume
        volume = cardano_market.get('volume')
        logger.info(f"Volume: {volume}")
        
        # Liquidity
        liquidity = cardano_market.get('liquidity')
        logger.info(f"Liquidity: {liquidity}")
        
        # Price changes
        one_day_change = cardano_market.get('oneDayPriceChange')
        one_week_change = cardano_market.get('oneWeekPriceChange')
        logger.info(f"OneDayPriceChange: {one_day_change}")
        logger.info(f"OneWeekPriceChange: {one_week_change}")
        
        # Check binary market logic
        logger.info("\n" + "=" * 80)
        logger.info("🎯 BINARY MARKET ANALYSIS")
        logger.info("=" * 80)
        
        is_binary = len(outcomes) == 2 and all(
            o.lower() in ['yes', 'no'] for o in outcomes
        )
        logger.info(f"Is Binary Market: {is_binary}")
        
        if is_binary:
            logger.info(f"✅ This is a binary market (Yes/No)")
            logger.info(f"   Outcome 0 (YES): {outcomes[0]} = {outcome_prices[0] if len(outcome_prices) > 0 else 'N/A'}")
            logger.info(f"   Outcome 1 (NO):  {outcomes[1]} = {outcome_prices[1] if len(outcome_prices) > 1 else 'N/A'}")
            
            # Show what we should process
            outcome_indices = [0]  # Only YES for binary
            logger.info(f"\n   Processing indices: {outcome_indices}")
            
            for idx in outcome_indices:
                price = float(outcome_prices[idx]) if idx < len(outcome_prices) else None
                logger.info(f"   → Would display: {outcomes[idx]} at {price:.4f} ({price*100:.2f}%)")
                
                # Determine direction
                if price is not None:
                    direction = 'YES' if price >= 0.5 else 'NO'
                    logger.info(f"   → Direction: {direction}")
                    logger.info(f"   → Is extreme YES (>85%): {price >= 0.85}")
                    logger.info(f"   → Is extreme NO (<15%): {price <= 0.15}")
        else:
            logger.info(f"❌ This is NOT a binary market")
            logger.info(f"   Would process all {len(outcomes)} outcomes")
        
        # Validate against Polymarket website
        logger.info("\n" + "=" * 80)
        logger.info("🌐 COMPARISON WITH POLYMARKET.COM")
        logger.info("=" * 80)
        logger.info("Expected from website: YES = 6% (0.06)")
        if len(outcome_prices) > 0:
            yes_price = float(outcome_prices[0])
            logger.info(f"Actual from API:      YES = {yes_price*100:.1f}% ({yes_price:.4f})")
            
            if abs(yes_price - 0.06) < 0.01:
                logger.info("✅ MATCH! API data is correct.")
            else:
                logger.error(f"❌ MISMATCH! Expected ~0.06, got {yes_price:.4f}")
                logger.error("   This indicates an API data issue or parsing problem.")
        
        logger.info("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(validate_cardano_market())
