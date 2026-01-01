"""Debug script to check market expiration dates."""
import asyncio
from datetime import datetime, timezone
from clients.gamma_client import GammaClient

async def main():
    print(f"Current time (UTC): {datetime.now(timezone.utc)}")
    print()
    
    async with GammaClient() as client:
        # Fetch some markets
        markets = await client.get_markets(limit=10, active=True, closed=False)
        
        print(f"Got {len(markets)} markets\n")
        
        for i, market in enumerate(markets[:5], 1):
            print(f"{'='*70}")
            print(f"MARKET {i}: {market.get('question', 'N/A')}")
            print(f"  slug: {market.get('slug', 'N/A')}")
            
            # Check all possible date fields
            for field in ['endDate', 'end_date_iso', 'end_date', 'closeTime', 'expirationDate']:
                value = market.get(field)
                if value:
                    print(f"  ✓ {field}: {value}")
                    try:
                        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        hours = (dt - now).total_seconds() / 3600
                        print(f"    → Parsed: {dt}")
                        print(f"    → Hours until expiry: {hours:.2f}")
                    except Exception as e:
                        print(f"    → Parse error: {e}")
            
            # Check if no date fields found
            all_fields = ['endDate', 'end_date_iso', 'end_date', 'closeTime', 'expirationDate']
            if not any(market.get(field) for field in all_fields):
                print(f"  ❌ NO DATE FIELDS FOUND")
                print(f"  Available fields: {list(market.keys())[:20]}")
            
            print()

if __name__ == "__main__":
    asyncio.run(main())
