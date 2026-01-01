"""
Check what default sort returns
"""
import asyncio
from clients.gamma_client import GammaClient

async def check_default_sort():
    """Check default sort markets"""
    async with GammaClient() as client:
        # Strategy 2: Default sort
        markets = await client.get_markets(
            limit=500,
            active=True,
            closed=False,
            order_by=""  # Default sort
        )
        
        print(f"Fetched {len(markets)} markets\n")
        
        # Find movie and politics markets
        for m in markets[:100]:  # Check first 100
            question = m.get('question', '').lower()
            
            if 'top grossing movie' in question and '2025' in question:
                print("=" * 80)
                print(f"FOUND MOVIE MARKET")
                print(f"Question: {m.get('question')}")
                print(f"Outcomes: {m.get('outcomes')}")
                print(f"OutcomePrices: {m.get('outcomePrices')}")
                print(f"OutcomePrices type: {type(m.get('outcomePrices'))}\n")
                break
            
            if '2028' in question and 'democratic' in question:
                print("=" * 80)
                print(f"FOUND POLITICS MARKET")
                print(f"Question: {m.get('question')}")
                print(f"Outcomes: {m.get('outcomes')}")
                print(f"OutcomePrices: {m.get('outcomePrices')}")
                print(f"OutcomePrices type: {type(m.get('outcomePrices'))}\n")
                break

if __name__ == "__main__":
    asyncio.run(check_default_sort())
