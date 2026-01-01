"""
Investigate market data structure to understand price fields.
"""

import asyncio
import logging
from clients.gamma_client import GammaClient
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def investigate_market_structure():
    """Fetch sample markets and examine their structure."""
    
    async with GammaClient() as client:
        # Get a diverse sample - use default sort to avoid crypto
        markets = await client.get_markets(limit=50, active=True, closed=False, order_by="")
        
        # Filter to non-crypto
        non_crypto = [m for m in markets if 'bitcoin' not in m.get('question', '').lower() 
                      and 'ethereum' not in m.get('question', '').lower()
                      and 'crypto' not in m.get('question', '').lower()
                      and 'btc' not in m.get('slug', '').lower()]
        
        print("\n" + "="*80)
        print("MARKET DATA STRUCTURE INVESTIGATION (NON-CRYPTO)")
        print("="*80 + "\n")
        
        for i, market in enumerate(non_crypto[:5], 1):
            question = market.get('question', 'Unknown')
            print(f"\n{i}. {question[:70]}")
            print("-" * 80)
            
            # Check outcome-related fields
            outcomes = market.get('outcomes', [])
            outcome_prices = market.get('outcomePrices', [])
            last_trade_price = market.get('lastTradePrice')
            price = market.get('price')
            tokens = market.get('tokens', [])
            best_bid = market.get('bestBid')
            best_ask = market.get('bestAsk')
            
            print(f"Outcomes (TYPE: {type(outcomes).__name__}, LEN: {len(outcomes)}): {outcomes if not isinstance(outcomes, str) else outcomes[:100]}")
            print(f"OutcomePrices (TYPE: {type(outcome_prices).__name__}, LEN: {len(outcome_prices) if outcome_prices else 0}): {outcome_prices}")
            print(f"lastTradePrice: {last_trade_price}")
            print(f"Price field: {price}")
            print(f"bestBid: {best_bid}, bestAsk: {best_ask}")
            print(f"Tokens ({len(tokens) if tokens else 0}): {len(tokens) if tokens else 'None'}")
            
            # Check for CLOBTokenIds
            clob_ids = market.get('clobTokenIds', [])
            print(f"CLOBTokenIds ({len(clob_ids) if clob_ids else 0}): {len(clob_ids) if clob_ids else 'None'}")
            
            # Check if it's a binary market
            is_binary = len(outcomes) == 2 and all(str(o).lower() in ['yes', 'no'] for o in outcomes)
            print(f"Is binary: {is_binary}")
            
            # Show price-related keys
            price_keys = [k for k in market.keys() if 'price' in k.lower() or 'bid' in k.lower() or 'ask' in k.lower()]
            print(f"\nPrice-related keys: {price_keys}")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(investigate_market_structure())
