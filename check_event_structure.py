"""
Simple test to see what event markets look like
"""
import asyncio
from clients.gamma_client import GammaClient

async def check_event_markets():
    """Check structure of markets from events endpoint"""
    async with GammaClient() as client:
        events = await client.get_events(limit=20, archived=False)
        
        print(f"Fetched {len(events)} events\n")
        
        for i, event in enumerate(events[:5]):  # Check first 5 events
            print("=" * 80)
            print(f"EVENT #{i+1}: {event.get('title', 'No title')}")
            print(f"  Slug: {event.get('slug')}")
            print(f"  Markets count: {len(event.get('markets', []))}")
            
            # Check first market from this event
            markets = event.get('markets', [])
            if markets:
                m = markets[0]
                print(f"\n  FIRST MARKET:")
                print(f"    Question: {m.get('question', 'No question')[:70]}")
                print(f"    Outcomes: {m.get('outcomes')}")
                print(f"    OutcomePrices: {m.get('outcomePrices')}")
                print(f"    Tokens: {len(m.get('tokens', []))}")
                print(f"    GroupItemID: {m.get('groupItemId')}")
                print(f"    EventSlug: {m.get('eventSlug')}")
                
                # Show all keys
                print(f"\n    Available fields: {', '.join(sorted(m.keys()))}")

if __name__ == "__main__":
    asyncio.run(check_event_markets())
