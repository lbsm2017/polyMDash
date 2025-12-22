"""
Momentum Terminal - Quick scanner for extreme markets near expiration
Shows markets >75% or <25% expiring within 3 days with strong 24h movement
"""

import asyncio
from datetime import datetime, timedelta, timezone
from colorama import Fore, Back, Style, init
from clients.gamma_client import GammaClient

# Initialize colorama for Windows support
init(autoreset=True)

# Market sources to scan
SOURCES = [
    "https://polymarket.com/breaking",
    "https://polymarket.com/politics",
    "https://polymarket.com/tech",
    "https://polymarket.com/trump",
    "https://polymarket.com/geopolitics"
]


async def scan_momentum_markets():
    """Scan for extreme momentum markets."""
    
    # Debug mode - set to True to see filtered out markets
    DEBUG_MODE = False
    
    print(f"\n{'='*100}")
    print(f"{Style.BRIGHT}{Fore.CYAN}🚀 MOMENTUM SCANNER - Extreme Markets Near Expiration{Style.RESET_ALL}")
    print(f"{'='*100}\n")
    
    print(f"{Fore.YELLOW}Sources:{Style.RESET_ALL}")
    for source in SOURCES:
        print(f"  • {Style.DIM}{source}{Style.RESET_ALL}")
    
    print(f"\n{Fore.YELLOW}Scanning for markets:{Style.RESET_ALL}")
    print(f"  • Probability: {Fore.GREEN}>75%{Style.RESET_ALL} or {Fore.RED}<25%{Style.RESET_ALL} (or {Fore.MAGENTA}>60%/<40% with high momentum{Style.RESET_ALL})")
    print(f"  • Momentum: {Fore.MAGENTA}≥15% move{Style.RESET_ALL} (24h or 1wk)")
    print(f"  • Expiration: {Fore.CYAN}3 days{Style.RESET_ALL} (or {Fore.CYAN}14 days{Style.RESET_ALL} if ≥30% momentum)")
    print(f"\n{Style.DIM}Fetching 500 markets...{Style.RESET_ALL}\n")
    
    async with GammaClient() as client:
        # Fetch markets
        markets = await client.get_markets(limit=500, active=True, closed=False, order_by="volume24hr")
        
        if not markets:
            print(f"{Fore.RED}No markets found!{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}✓ Fetched {len(markets)} markets{Style.RESET_ALL}")
        
        # Filter out only major crypto terms
        excluded_terms = {'bitcoin', 'btc', 'crypto', 'ethereum', 'eth', 'solana', 'xrp'}
        
        def is_excluded(market):
            slug = (market.get('slug', '') or '').lower()
            question = (market.get('question', '') or '').lower()
            return any(ex in slug or ex in question for ex in excluded_terms)
        
        filtered = [m for m in markets if not is_excluded(m)]
        print(f"{Fore.GREEN}✓ After crypto filter: {len(filtered)} markets{Style.RESET_ALL}")
        
        # Find extreme markets with momentum
        now = datetime.now(timezone.utc)
        
        # Filter thresholds
        max_hours_short = 72       # 3 days for standard extreme markets
        max_hours_momentum = 336   # 14 days for high momentum markets
        min_extremity = 0.25       # >75% or <25%
        min_momentum = 0.15        # 15% price change to qualify as momentum
        high_momentum = 0.30       # 30%+ is high momentum (extends time window)
        
        opportunities = []
        
        if DEBUG_MODE:
            print(f"\n{Style.BRIGHT}{'='*100}")
            print(f"🔍 DEBUG: Markets Filtered Out")
            print(f"{'='*100}{Style.RESET_ALL}\n")
        
        skipped_no_outcomes = 0
        skipped_price_error = 0
        processed_count = 0
        
        # Debug: Print first market's full structure
        if DEBUG_MODE and filtered:
            sample = filtered[0]
            print(f"{Style.BRIGHT}🔍 First market structure:{Style.RESET_ALL}")
            print(f"  Question: {sample.get('question', 'N/A')[:70]}")
            print(f"  Outcomes: {sample.get('outcomes')}")
            print(f"  lastTradePrice: {sample.get('lastTradePrice', 'NOT FOUND')}")
            print(f"  bestBid: {sample.get('bestBid', 'NOT FOUND')}")
            print(f"  bestAsk: {sample.get('bestAsk', 'NOT FOUND')}")
            print(f"  oneDayPriceChange: {sample.get('oneDayPriceChange', 'NOT FOUND')}")
            print()
        
        for market in filtered:
            # Get price from lastTradePrice field
            outcomes = market.get('outcomes', [])
            if not outcomes or len(outcomes) < 2:
                skipped_no_outcomes += 1
                if DEBUG_MODE and skipped_no_outcomes <= 3:
                    question = market.get('question', 'Unknown')[:70]
                    print(f"{Style.BRIGHT}SKIPPED: {question}{Style.RESET_ALL}")
                    print(f"  Reason: Missing or insufficient outcomes (need 2, got {len(outcomes)})")
                    print()
                continue
            
            # Extract price from lastTradePrice (or bestBid/bestAsk as fallback)
            try:
                yes_price = market.get('lastTradePrice')
                
                # If no lastTradePrice or it's 0, try bestBid/bestAsk average
                if yes_price is None or yes_price == 0:
                    best_bid = market.get('bestBid')
                    best_ask = market.get('bestAsk')
                    if best_bid is not None and best_ask is not None:
                        yes_price = (float(best_bid) + float(best_ask)) / 2
                    else:
                        # Skip if no price data available
                        skipped_price_error += 1
                        if DEBUG_MODE and skipped_price_error <= 3:
                            question = market.get('question', 'Unknown')[:70]
                            print(f"{Style.BRIGHT}SKIPPED: {question}{Style.RESET_ALL}")
                            print(f"  Reason: No price data (lastTradePrice={yes_price}, bestBid={best_bid}, bestAsk={best_ask})")
                            print()
                        continue
                
                yes_price = float(yes_price)
                
                if DEBUG_MODE and processed_count == 0:
                    print(f"{Style.BRIGHT}✓ First market parsed successfully:{Style.RESET_ALL}")
                    print(f"  Question: {market.get('question', 'Unknown')[:70]}")
                    print(f"  Outcomes: {outcomes}")
                    print(f"  Extracted price: {yes_price}")
                    print()
                processed_count += 1
            except (ValueError, TypeError, AttributeError) as e:
                skipped_price_error += 1
                if DEBUG_MODE and skipped_price_error <= 3:
                    question = market.get('question', 'Unknown')[:70]
                    print(f"{Style.BRIGHT}SKIPPED: {question}{Style.RESET_ALL}")
                    print(f"  Error extracting price: {e}")
                    print()
                continue
            
            # Check if extreme
            is_extreme_yes = yes_price >= (0.5 + min_extremity)
            is_extreme_no = yes_price <= (0.5 - min_extremity)
            
            # Get momentum data (price changes)
            one_day_change = abs(float(market.get('oneDayPriceChange') or 0))
            one_week_change = abs(float(market.get('oneWeekPriceChange') or 0))
            momentum = max(one_day_change, one_week_change)  # Best of 24h or 1w
            has_momentum = momentum >= min_momentum
            has_high_momentum = momentum >= high_momentum
            
            # Get expiration for debug
            end_date = market.get('endDate')
            hours_to_expiry = None
            
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    hours_to_expiry = (end_dt - now).total_seconds() / 3600
                except:
                    pass
            
            # Qualify if: extreme AND (has momentum OR near expiry)
            # OR: has high momentum AND somewhat extreme (>60% or <40%)
            is_somewhat_extreme = yes_price >= 0.60 or yes_price <= 0.40
            qualifies = (is_extreme_yes or is_extreme_no) or (has_high_momentum and is_somewhat_extreme)
            
            # Debug log for filtered markets
            if DEBUG_MODE and not qualifies:
                question = market.get('question', 'Unknown')[:70]
                time_str = f"{hours_to_expiry:.1f}h" if hours_to_expiry else "N/A"
                print(f"{Style.BRIGHT}FILTERED: {question}{Style.RESET_ALL}")
                print(f"  Probability: {yes_price:.1%} | Momentum: {momentum:.1%} | Time: {time_str}")
                print(f"  Reason: Not extreme enough and low momentum")
                print()
            
            if not qualifies:
                continue
            
            # Check expiration
            if not end_date:
                if DEBUG_MODE:
                    question = market.get('question', 'Unknown')[:70]
                    print(f"{Style.BRIGHT}FILTERED: {question}{Style.RESET_ALL}")
                    print(f"  Probability: {yes_price:.1%} | Time to expiry: N/A | Reason: No expiration date")
                    print()
                continue
            
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                hours_to_expiry = (end_dt - now).total_seconds() / 3600
                
                # High momentum markets get extended window (14 days), others 3 days
                effective_max_hours = max_hours_momentum if has_high_momentum else max_hours_short
                
                if hours_to_expiry <= 0 or hours_to_expiry > effective_max_hours:
                    if DEBUG_MODE:
                        question = market.get('question', 'Unknown')[:70]
                        time_str = f"{hours_to_expiry:.1f}h"
                        reason = "Already expired" if hours_to_expiry <= 0 else f"Too far (>{effective_max_hours}h)"
                        print(f"{Style.BRIGHT}FILTERED: {question}{Style.RESET_ALL}")
                        print(f"  Probability: {yes_price:.1%} | Momentum: {momentum:.1%} | Time: {time_str}")
                        print(f"  Reason: {reason}")
                        print()
                    continue
            except:
                if DEBUG_MODE:
                    question = market.get('question', 'Unknown')[:70]
                    print(f"{Style.BRIGHT}FILTERED: {question}{Style.RESET_ALL}")
                    print(f"  Probability: {yes_price:.1%} | Time to expiry: ERROR | Reason: Invalid date format")
                    print()
                continue
            
            # Get volume
            volume = float(market.get('volume') or 0)
            
            # Calculate score (momentum-weighted)
            distance_from_50 = abs(yes_price - 0.5)
            urgency_score = max(0, (max_hours_short - hours_to_expiry) / max_hours_short)  # Caps at 1.0
            volume_score = min(volume / 100000, 1.0)
            momentum_score = min(momentum / 0.5, 1.0)  # Caps at 50% change
            
            # Weight: 30% extremity, 25% urgency, 20% volume, 25% momentum
            score = (distance_from_50 * 30) + (urgency_score * 25) + (volume_score * 20) + (momentum_score * 25)
            
            # Calculate annualized yield
            # For YES: buying at yes_price, resolves to 1.0, profit = (1 - yes_price) / yes_price
            # For NO: buying NO at (1 - yes_price), resolves to 1.0, profit = yes_price / (1 - yes_price)
            direction = 'YES' if is_extreme_yes else 'NO'
            
            if direction == 'YES':
                entry_price = yes_price
                profit_if_win = (1.0 - yes_price) / yes_price if yes_price > 0 else 0
            else:
                entry_price = 1.0 - yes_price
                profit_if_win = yes_price / (1.0 - yes_price) if yes_price < 1.0 else 0
            
            # Annualize: (1 + return) ^ (8760 / hours) - 1
            # 8760 hours in a year
            hours_in_year = 8760
            if hours_to_expiry > 0:
                annualized_yield = ((1 + profit_if_win) ** (hours_in_year / hours_to_expiry)) - 1
            else:
                annualized_yield = 0
            
            opportunities.append({
                'question': market.get('question', 'Unknown'),
                'slug': market.get('slug', ''),
                'yes_price': yes_price,
                'hours_to_expiry': hours_to_expiry,
                'end_date': end_dt,
                'volume': volume,
                'momentum': momentum,
                'one_day_change': one_day_change,
                'score': score,
                'direction': direction,
                'entry_price': entry_price,
                'profit_if_win': profit_if_win,
                'annualized_yield': annualized_yield
            })
        
        # Sort by score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        if DEBUG_MODE:
            print(f"\n{Style.BRIGHT}{'='*100}")
            print(f"End of filtered markets debug log")
            print(f"{'='*100}{Style.RESET_ALL}")
            print(f"\nProcessing Summary:")
            print(f"  Total markets: {len(filtered)}")
            print(f"  Skipped (no outcomes): {skipped_no_outcomes}")
            print(f"  Skipped (price error): {skipped_price_error}")
            print(f"  Successfully processed: {processed_count}")
            print()
        
        print(f"{Fore.GREEN}✓ Found {len(opportunities)} extreme markets{Style.RESET_ALL}\n")
        
        if not opportunities:
            print(f"{Fore.YELLOW}No opportunities found. Try different filters.{Style.RESET_ALL}")
            return
        
        # Display results
        print(f"{'='*100}")
        print(f"{Style.BRIGHT}📊 OPPORTUNITIES (Top {min(len(opportunities), 30)}){Style.RESET_ALL}")
        print(f"{'='*100}\n")
        
        for i, opp in enumerate(opportunities[:30], 1):
            # Color based on direction
            if opp['direction'] == 'YES':
                dir_color = Fore.GREEN
                dir_symbol = "📈"
                prob_display = f"{opp['yes_price']:.1%}"
            else:
                dir_color = Fore.RED
                dir_symbol = "📉"
                prob_display = f"{opp['yes_price']:.1%}"
            
            # Color based on urgency
            hours = opp['hours_to_expiry']
            if hours < 24:
                time_color = Fore.RED
                time_str = f"{int(hours)}h"
            elif hours < 48:
                time_color = Fore.YELLOW
                time_str = f"{hours/24:.1f}d"
            else:
                time_color = Fore.CYAN
                time_str = f"{int(hours/24)}d"
            
            # Format expiration
            exp_date = opp['end_date'].strftime('%m/%d %H:%M')
            
            # Momentum color
            momentum = opp.get('momentum', 0)
            if momentum >= 0.30:
                mom_color = Fore.MAGENTA + Style.BRIGHT
                mom_str = f"🔥{momentum:+.0%}"
            elif momentum >= 0.15:
                mom_color = Fore.MAGENTA
                mom_str = f"↑{momentum:+.0%}"
            else:
                mom_color = Style.DIM
                mom_str = f"  {momentum:+.0%}"
            
            # Score color
            score = opp['score']
            if score >= 70:
                score_color = Fore.GREEN
                grade = "A"
            elif score >= 60:
                score_color = Fore.YELLOW
                grade = "B"
            else:
                score_color = Fore.CYAN
                grade = "C"
            
            # Annualized yield formatting
            ann_yield = opp.get('annualized_yield', 0)
            if ann_yield > 10:  # >1000%
                yield_color = Fore.GREEN + Style.BRIGHT
                yield_str = f"🚀{ann_yield:.0%}"
            elif ann_yield > 2:  # >200%
                yield_color = Fore.GREEN
                yield_str = f"📈{ann_yield:.0%}"
            elif ann_yield > 0.5:  # >50%
                yield_color = Fore.YELLOW
                yield_str = f"↗{ann_yield:.0%}"
            else:
                yield_color = Style.DIM
                yield_str = f"{ann_yield:.0%}"
            
            # Print opportunity
            print(f"{Style.BRIGHT}#{i:2d}{Style.RESET_ALL} "
                  f"{score_color}[{score:.0f} {grade}]{Style.RESET_ALL} "
                  f"{dir_color}{dir_symbol} {opp['direction']:3s} {prob_display:>6s}{Style.RESET_ALL} "
                  f"│ {mom_color}{mom_str:>7s}{Style.RESET_ALL} "
                  f"│ {time_color}⏰ {time_str:>6s}{Style.RESET_ALL} "
                  f"│ {yield_color}APY {yield_str:>8s}{Style.RESET_ALL} "
                  f"│ {Style.DIM}💰 ${opp['volume']:>8,.0f}{Style.RESET_ALL}")
            
            # Question on next line
            question = opp['question'][:85] + "..." if len(opp['question']) > 85 else opp['question']
            print(f"    {Style.DIM}{question}{Style.RESET_ALL}")
            print(f"    {Style.DIM}└─ polymarket.com/market/{opp['slug']}{Style.RESET_ALL}\n")


async def main():
    """Main entry point."""
    try:
        await scan_momentum_markets()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*100}")
        print(f"{Style.BRIGHT}Done!{Style.RESET_ALL}")
        print(f"{'='*100}\n")


if __name__ == "__main__":
    asyncio.run(main())
