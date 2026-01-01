"""
Investigate why Politics/Entertainment markets have no prices.
Compare data structure between Sports and Politics markets.
"""

import asyncio
import logging
from clients.gamma_client import GammaClient
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def compare_market_structures():
    """Compare Sports vs Politics market data structures."""
    
    async with GammaClient() as client:
        # Get diverse markets
        markets = await client.get_markets(limit=200, active=True, closed=False, order_by="")
        
        # Categorize
        sports = []
        politics = []
        entertainment = []
        
        for m in markets:
            q = m.get('question', '').lower()
            if any(w in q for w in ['nfl', 'nba', 'championship', 'playoff', 'seahawks', 'rams']):
                sports.append(m)
            elif any(w in q for w in ['trump', 'biden', 'election', 'president']):
                politics.append(m)
            elif any(w in q for w in ['movie', 'film', 'avatar', 'superman']):
                entertainment.append(m)
        
        print("\n" + "="*80)
        print(f"Found {len(sports)} Sports, {len(politics)} Politics, {len(entertainment)} Entertainment")
        print("="*80)
        
        # Compare first market of each type
        for category, markets_list in [("SPORTS", sports[:2]), ("POLITICS", politics[:2]), ("ENTERTAINMENT", entertainment[:2])]:
            print(f"\n{'='*80}")
            print(f"{category} MARKETS")
            print("="*80)
            
            for i, m in enumerate(markets_list, 1):
                if not m:
                    continue
                    
                question = m.get('question', 'Unknown')
                print(f"\n{i}. {question[:70]}")
                print("-" * 80)
                
                outcomes = m.get('outcomes', [])
                outcome_prices = m.get('outcomePrices', [])
                
                print(f"Outcomes (raw): {type(outcomes).__name__} = {outcomes}")
                print(f"OutcomePrices (raw): {type(outcome_prices).__name__} = {outcome_prices}")
                
                # Try parsing
                if isinstance(outcomes, str):
                    try:
                        outcomes_parsed = json.loads(outcomes)
                        print(f"Outcomes (parsed): {outcomes_parsed}")
                    except:
                        print(f"Outcomes (parse failed)")
                
                if isinstance(outcome_prices, str):
                    try:
                        prices_parsed = json.loads(outcome_prices)
                        print(f"OutcomePrices (parsed): {prices_parsed}")
                        if prices_parsed:
                            prices_float = [float(p) for p in prices_parsed]
                            print(f"OutcomePrices (as float): {prices_float}")
                    except Exception as e:
                        print(f"OutcomePrices (parse failed): {e}")
                
                # Check other price fields
                print(f"\nOther price fields:")
                print(f"  lastTradePrice: {m.get('lastTradePrice')}")
                print(f"  bestBid: {m.get('bestBid')}")
                print(f"  bestAsk: {m.get('bestAsk')}")
                print(f"  clobTokenIds: {len(m.get('clobTokenIds', []))} items")
                print(f"  volume: {m.get('volume')}")


if __name__ == "__main__":
    asyncio.run(compare_market_structures())
