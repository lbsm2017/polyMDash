"""
Investigation: Understand grouped/nested market structure
Check if markets without outcomePrices are part of multi-outcome parents
"""
import asyncio
import aiohttp
import json

async def investigate_grouped_markets():
    """Compare standalone vs grouped market structures"""
    
    async with aiohttp.ClientSession() as session:
        # Fetch breaking markets (where the None prices are coming from)
        print("=" * 80)
        print("FETCHING BREAKING MARKETS (source of None prices)")
        print("=" * 80)
        
        url = "https://gamma-api.polymarket.com/markets/breaking"
        params = {'limit': 100}
        
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            print(f"Response type: {type(data)}")
            print(f"Response keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
            
            # Breaking markets endpoint returns different structure
            if isinstance(data, dict):
                markets = data.get('data', [])
            elif isinstance(data, list):
                markets = data
            else:
                print("Unexpected response format")
                return
                
            print(f"Total markets fetched: {len(markets)}")
            
            # Find movies and politics markets
            movie_markets = []
            politics_markets = []
            
            for m in markets:
                if not isinstance(m, dict):
                    print(f"Skipping non-dict item: {type(m)}")
                    continue
                question = m.get('question', '').lower()
                if 'movie' in question and '2025' in question:
                    movie_markets.append(m)
                if '2028' in question and 'democratic' in question:
                    politics_markets.append(m)
            
            print(f"\nFound {len(movie_markets)} movie markets")
            print(f"Found {len(politics_markets)} 2028 politics markets")
            
            # Examine first movie market in detail
            if movie_markets:
                print("\n" + "=" * 80)
                print("MOVIE MARKET EXAMPLE (Entertainment with None prices)")
                print("=" * 80)
                m = movie_markets[0]
                print(f"Question: {m.get('question')}")
                print(f"Slug: {m.get('slug')}")
                print(f"Outcomes: {m.get('outcomes')}")
                print(f"OutcomePrices: {m.get('outcomePrices')}")
                print(f"GroupItemID: {m.get('groupItemId')}")
                print(f"GroupItemThreshold: {m.get('groupItemThreshold')}")
                print(f"EventSlug: {m.get('eventSlug')}")
                print(f"MarketSlug: {m.get('marketSlug')}")
                print(f"Tokens: {len(m.get('tokens', []))}")
                
                # Check if it has tokens with prices
                if m.get('tokens'):
                    print(f"\nTokens structure:")
                    for token in m.get('tokens', []):
                        print(f"  - {token}")
                
                # Print ALL keys to see what we're missing
                print(f"\nAll available fields:")
                for key in sorted(m.keys()):
                    value = m[key]
                    if isinstance(value, (list, dict)) and len(str(value)) > 100:
                        print(f"  {key}: <{type(value).__name__} len={len(value)}>")
                    else:
                        print(f"  {key}: {value}")
            
            # Examine first politics market
            if politics_markets:
                print("\n" + "=" * 80)
                print("POLITICS MARKET EXAMPLE (Politics with None prices)")
                print("=" * 80)
                m = politics_markets[0]
                print(f"Question: {m.get('question')}")
                print(f"Slug: {m.get('slug')}")
                print(f"Outcomes: {m.get('outcomes')}")
                print(f"OutcomePrices: {m.get('outcomePrices')}")
                print(f"GroupItemID: {m.get('groupItemId')}")
                print(f"EventSlug: {m.get('eventSlug')}")
                
                # If it's part of a group, try fetching the parent
                group_id = m.get('groupItemId')
                event_slug = m.get('eventSlug')
                
                if event_slug:
                    print(f"\n>>> This market is part of event: {event_slug}")
                    print(">>> Attempting to fetch parent event market data...")
                    
                    # Try fetching via event endpoint
                    event_url = f"https://gamma-api.polymarket.com/events/{event_slug}"
                    try:
                        async with session.get(event_url) as event_resp:
                            event_data = await event_resp.json()
                            print(f"\nEvent data retrieved:")
                            print(f"  Title: {event_data.get('title')}")
                            print(f"  Markets: {len(event_data.get('markets', []))}")
                            
                            if event_data.get('markets'):
                                parent = event_data['markets'][0]
                                print(f"\n  Parent market outcomes: {parent.get('outcomes')}")
                                print(f"  Parent outcomePrices: {parent.get('outcomePrices')}")
                    except Exception as e:
                        print(f"  Failed to fetch event: {e}")

if __name__ == "__main__":
    asyncio.run(investigate_grouped_markets())
