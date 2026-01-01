"""
Debug script to inspect actual API response format
"""
import asyncio
import json
from clients.gamma_client import GammaClient

async def inspect_markets():
    async with GammaClient() as client:
        print("Fetching 10 markets...")
        markets = await client.get_markets(limit=10, active=True, closed=False)
        
        print(f"\n✅ Got {len(markets)} markets\n")
        
        for i, market in enumerate(markets[:3], 1):
            print(f"\n{'='*70}")
            print(f"MARKET {i}: {market.get('question', 'NO QUESTION')[:60]}")
            print(f"{'='*70}")
            
            # Check key fields
            print(f"✓ slug: {market.get('slug', 'MISSING')[:50]}")
            print(f"✓ outcomes type: {type(market.get('outcomes', 'MISSING'))}")
            print(f"✓ outcomes value: {market.get('outcomes', 'MISSING')}")
            
            # Critical: Check outcomePrices
            if 'outcomePrices' in market:
                prices = market.get('outcomePrices')
                print(f"✓ outcomePrices EXISTS")
                print(f"  - Type: {type(prices)}")
                print(f"  - Value: {prices}")
                
                # Try parsing
                if isinstance(prices, str):
                    print(f"  - Attempting JSON parse...")
                    try:
                        parsed = json.loads(prices)
                        print(f"  - ✅ Parsed to: {parsed}")
                        print(f"  - Parsed types: {[type(p).__name__ for p in parsed]}")
                    except Exception as e:
                        print(f"  - ❌ Parse failed: {e}")
            else:
                print(f"❌ outcomePrices MISSING")
            
            # Check other price fields
            print(f"\nOther price fields:")
            print(f"  - lastTradePrice: {market.get('lastTradePrice', 'MISSING')}")
            print(f"  - bestBid: {market.get('bestBid', 'MISSING')}")
            print(f"  - bestAsk: {market.get('bestAsk', 'MISSING')}")

asyncio.run(inspect_markets())
