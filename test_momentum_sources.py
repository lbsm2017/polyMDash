"""
Quick integration test for new momentum hunter data sources.
Tests all 8 strategies to ensure they're working correctly.
"""

import asyncio
import logging
from clients.gamma_client import GammaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_all_sources():
    """Test all market sourcing strategies."""
    
    results = {}
    
    async with GammaClient() as client:
        # Strategy 1: Liquidity
        try:
            markets = await client.get_markets(limit=10, active=True, closed=False, order_by="liquidity")
            results['liquidity'] = len(markets)
            logger.info(f"✅ Strategy 1 (Liquidity): {len(markets)} markets")
        except Exception as e:
            results['liquidity'] = 0
            logger.error(f"❌ Strategy 1 (Liquidity) failed: {e}")
        
        # Strategy 2: Default
        try:
            markets = await client.get_markets(limit=10, active=True, closed=False, order_by="")
            results['default'] = len(markets)
            logger.info(f"✅ Strategy 2 (Default): {len(markets)} markets")
        except Exception as e:
            results['default'] = 0
            logger.error(f"❌ Strategy 2 (Default) failed: {e}")
        
        # Strategy 3: Volume with offset
        try:
            markets = await client.get_markets(limit=10, offset=100, active=True, closed=False, order_by="volume24hr")
            results['volume_offset'] = len(markets)
            logger.info(f"✅ Strategy 3 (Volume+Offset): {len(markets)} markets")
        except Exception as e:
            results['volume_offset'] = 0
            logger.error(f"❌ Strategy 3 (Volume+Offset) failed: {e}")
        
        # Strategy 4: Hot markets
        try:
            markets = await client.get_hot_markets(limit=10)
            results['hot'] = len(markets)
            logger.info(f"✅ Strategy 4 (Hot Markets): {len(markets)} markets")
        except Exception as e:
            results['hot'] = 0
            logger.error(f"❌ Strategy 4 (Hot Markets) failed: {e}")
        
        # Strategy 5: Breaking markets
        try:
            markets = await client.get_breaking_markets(limit=10)
            # Handle events endpoint
            if markets and isinstance(markets, list) and markets and 'markets' in markets[0]:
                extracted = []
                for event in markets:
                    extracted.extend(event.get('markets', []))
                markets = extracted
            results['breaking'] = len(markets)
            logger.info(f"✅ Strategy 5 (Breaking): {len(markets)} markets")
        except Exception as e:
            results['breaking'] = 0
            logger.error(f"❌ Strategy 5 (Breaking) failed: {e}")
        
        # Strategy 6: Events
        try:
            events = await client.get_events(limit=5, archived=False)
            market_count = 0
            for event in events:
                market_count += len(event.get('markets', []))
            results['events'] = market_count
            logger.info(f"✅ Strategy 6 (Events): {market_count} markets from {len(events)} events")
        except Exception as e:
            results['events'] = 0
            logger.error(f"❌ Strategy 6 (Events) failed: {e}")
        
        # Strategy 7: Newest
        try:
            markets = await client.get_markets(limit=10, active=True, closed=False, order_by="createdAt")
            results['newest'] = len(markets)
            logger.info(f"✅ Strategy 7 (Newest): {len(markets)} markets")
        except Exception as e:
            results['newest'] = 0
            logger.error(f"❌ Strategy 7 (Newest) failed: {e}")
        
        # Strategy 8: Categories
        categories = ['politics', 'tech', 'finance', 'world']
        category_results = {}
        for category in categories:
            try:
                markets = await client.get_markets(limit=10, active=True, closed=False, category=category)
                category_results[category] = len(markets)
                logger.info(f"✅ Strategy 8 ({category}): {len(markets)} markets")
            except Exception as e:
                category_results[category] = 0
                logger.error(f"❌ Strategy 8 ({category}) failed: {e}")
        
        results['categories'] = category_results
    
    # Summary
    print("\n" + "="*60)
    print("MOMENTUM HUNTER SOURCE TEST SUMMARY")
    print("="*60)
    
    total_sources = 7 + len(categories)
    passed = sum(1 for v in results.values() if (isinstance(v, int) and v > 0))
    passed += sum(1 for v in results.get('categories', {}).values() if v > 0)
    
    print(f"\n✅ Passed: {passed}/{total_sources} sources")
    print(f"❌ Failed: {total_sources - passed}/{total_sources} sources")
    
    print("\nDetailed Results:")
    for key, value in results.items():
        if key == 'categories':
            print(f"  Categories:")
            for cat, count in value.items():
                status = "✅" if count > 0 else "❌"
                print(f"    {status} {cat}: {count} markets")
        else:
            status = "✅" if value > 0 else "❌"
            print(f"  {status} {key}: {value} markets")
    
    print("\n" + "="*60)
    
    if passed == total_sources:
        print("🎉 ALL SOURCES WORKING PERFECTLY!")
        return True
    else:
        print(f"⚠️  {total_sources - passed} source(s) need attention")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_all_sources())
    exit(0 if success else 1)
