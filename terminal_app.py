"""
Terminal Activity Viewer - Quick debug view of tracked user activities
Shows last 24h of BUY/SELL activities with colorized output
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

from colorama import Fore, Back, Style, init

from clients.trades_client import TradesClient
from utils.user_tracker import get_user_tracker
from utils.helpers import format_currency


# Initialize colorama for Windows support
init(autoreset=True)


def print_colored(text):
    """Print text with color support."""
    print(text)


def colorize_trade(side: str, outcome: str) -> tuple:
    """Return colored trade string and color code."""
    trade_type = f"{side} {outcome}"
    
    # BUY YES = green, SELL YES = blue, BUY NO = red, SELL NO = pink
    if side == "BUY" and outcome.upper() == "YES":
        return f"{Fore.GREEN}{Style.BRIGHT}{trade_type}{Style.RESET_ALL}", Fore.GREEN
    elif side == "SELL" and outcome.upper() == "YES":
        return f"{Fore.BLUE}{Style.BRIGHT}{trade_type}{Style.RESET_ALL}", Fore.BLUE
    elif side == "BUY" and outcome.upper() == "NO":
        return f"{Fore.RED}{Style.BRIGHT}{trade_type}{Style.RESET_ALL}", Fore.RED
    elif side == "SELL" and outcome.upper() == "NO":
        return f"{Fore.MAGENTA}{Style.BRIGHT}{trade_type}{Style.RESET_ALL}", Fore.MAGENTA
    else:
        # For other outcomes (Over, Under, team names, etc.)
        if side == "BUY":
            return f"{Fore.CYAN}{Style.BRIGHT}{trade_type}{Style.RESET_ALL}", Fore.CYAN
        else:
            return f"{Fore.YELLOW}{Style.BRIGHT}{trade_type}{Style.RESET_ALL}", Fore.YELLOW


async def fetch_recent_activities():
    """Fetch recent trading activities for tracked users."""
    # Load tracked users
    tracker = get_user_tracker()
    tracked_wallets = tracker.get_wallet_addresses()
    
    if not tracked_wallets:
        print(f"{Fore.YELLOW}No tracked users found in tracked_users.json{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}Tracking {len(tracked_wallets)} users:{Style.RESET_ALL}")
    for wallet in tracked_wallets:
        user_name = tracker.get_user_name(wallet)
        print(f"  • {Fore.YELLOW}{user_name}{Style.RESET_ALL} ({wallet[:8]}...)")
    
    print(f"\n{'='*80}")
    print(f"{Style.BRIGHT}Fetching last 24h activities...{Style.RESET_ALL}")
    print(f"{'='*80}\n")
    
    # Initialize trades client with session
    async with TradesClient() as client:
        # Calculate 24h ago timestamp
        time_24h_ago = int((datetime.now() - timedelta(hours=24)).timestamp())
        
        # Fetch trades for each tracked user
        all_trades = []
        
        for wallet in tracked_wallets:
            try:
                user_name = tracker.get_user_name(wallet)
                trades = await client.get_user_trades(wallet)
                
                # Handle None or empty response
                if not trades:
                    print(f"{Style.DIM}{user_name}: No trades found{Style.RESET_ALL}")
                    continue
                
                # Filter to last 24 hours
                recent_trades = [
                    t for t in trades 
                    if isinstance(t, dict) and t.get('timestamp', 0) >= time_24h_ago
                ]
                
                if recent_trades:
                    print(f"{Fore.YELLOW}{user_name}{Style.RESET_ALL}: {len(recent_trades)} trades in last 24h")
                    
                    # Add user info to trades
                    for trade in recent_trades:
                        trade['user_name'] = user_name
                        trade['user_wallet'] = wallet
                    
                    all_trades.extend(recent_trades)
                else:
                    print(f"{Style.DIM}{user_name}: No trades in last 24h{Style.RESET_ALL}")
                        
            except Exception as e:
                print(f"{Fore.RED}Error fetching trades for {wallet}: {e}{Style.RESET_ALL}")
        
        # Sort all trades by timestamp (most recent first)
        all_trades.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        if not all_trades:
            print(f"\n{Fore.YELLOW}No trades found in the last 24 hours{Style.RESET_ALL}")
            return
        
        # Display trades
        print(f"\n{'='*80}")
        print(f"{Style.BRIGHT}ACTIVITY FEED - {len(all_trades)} trades{Style.RESET_ALL}")
        print(f"{'='*80}\n")
        
        for trade in all_trades:
            # Extract trade details
            user_name = trade.get('user_name', 'Unknown')
            side = trade.get('side', 'UNKNOWN')
            outcome = trade.get('outcome', 'UNKNOWN')
            price = trade.get('price', 0)
            size = trade.get('size', 0)
            volume = price * size
            timestamp = trade.get('timestamp', 0)
            
            # Format timestamp
            trade_time = datetime.fromtimestamp(timestamp)
            time_str = trade_time.strftime("%H:%M:%S")
            
            # Calculate time ago
            time_diff = datetime.now() - trade_time
            if time_diff.seconds < 60:
                time_ago = "just now"
            elif time_diff.seconds < 3600:
                mins = time_diff.seconds // 60
                time_ago = f"{mins}m ago"
            elif time_diff.days == 0:
                hours = time_diff.seconds // 3600
                time_ago = f"{hours}h ago"
            else:
                time_ago = f"{time_diff.days}d ago"
            
            # Colorize trade
            trade_colored, _ = colorize_trade(side, outcome)
            
            # Build simple, colorful trade message
            print(
                f"[{Fore.CYAN}{time_ago:>10}{Style.RESET_ALL}] "
                f"{Fore.YELLOW}{user_name:>15}{Style.RESET_ALL} | "
                f"{trade_colored:>30} | "
                f"{Style.BRIGHT}{format_currency(volume):>12}{Style.RESET_ALL} "
                f"{Style.DIM}({size:.0f} @ ${price:.3f}){Style.RESET_ALL}"
            )


async def main():
    """Main entry point."""
    print(f"\n{'='*80}")
    print(f"{Style.BRIGHT}POLYMARKET ACTIVITY VIEWER{Style.RESET_ALL}")
    print(f"{'='*80}\n")
    
    try:
        await fetch_recent_activities()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Interrupted by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
    finally:
        print(f"\n{'='*80}")
        print(f"{Style.BRIGHT}Done!{Style.RESET_ALL}")
        print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
