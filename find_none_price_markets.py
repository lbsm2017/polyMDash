"""
Find the specific events that have movie/politics markets with None prices
"""
import asyncio
from clients.gamma_client import GammaClient

async def find_problematic_events():
    """Find events with movie/politics markets"""
    async with GammaClient() as client:
        # Fetch MORE events - breaking markets gets 100 events which could have 1000+ markets
        events = await client.get_events(limit=1500, archived=False)
        
        print(f"Fetched {len(events)} events\n")
        
        found_movie = False
        found_politics = False
        total_markets_checked = 0
        
        for event in events:
            markets = event.get('markets', [])
            total_markets_checked += len(markets)
            
            for m in markets:
                question = m.get('question', '').lower()
                
                # Look for movie markets
                if 'top grossing movie' in question and '2025' in question:
                    if not found_movie:
                        print("=" * 80)
                        print(f"FOUND MOVIE MARKET (Entertainment)")
                        print("=" * 80)
                        print(f"Event: {event.get('title')}")
                        print(f"Market question: {m.get('question')}")
                        print(f"Outcomes: {m.get('outcomes')}")
                        print(f"OutcomePrices: {m.get('outcomePrices')}")
                        print(f"OutcomePrices type: {type(m.get('outcomePrices'))}")
                        print(f"Tokens: {len(m.get('tokens', []))}")
                        print(f"\nAll market keys: {', '.join(sorted(m.keys()))}\n")
                        found_movie = True
                
                # Look for 2028 politics markets
                if '2028' in question and 'democratic' in question:
                    if not found_politics:
                        print("=" * 80)
                        print(f"FOUND POLITICS MARKET (2028 Dem nomination)")
                        print("=" * 80)
                        print(f"Event: {event.get('title')}")
                        print(f"Market question: {m.get('question')}")
                        print(f"Outcomes: {m.get('outcomes')}")
                        print(f"OutcomePrices: {m.get('outcomePrices')}")
                        print(f"OutcomePrices type: {type(m.get('outcomePrices'))}")
                        print(f"Tokens: {len(m.get('tokens', []))}")
                        print(f"\nAll market keys: {', '.join(sorted(m.keys()))}\n")
                        found_politics = True
                
                if found_movie and found_politics:
                    return
        
        print(f"Total markets checked: {total_markets_checked}")
        print(f"Found movie market: {found_movie}")
        print(f"Found politics market: {found_politics}")

if __name__ == "__main__":
    asyncio.run(find_problematic_events())
