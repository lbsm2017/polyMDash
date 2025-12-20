"""
User tracking utilities for managing followed traders.
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class UserTracker:
    """Manage tracked users/traders."""
    
    def __init__(self, config_file: str = "tracked_users.json"):
        """
        Initialize user tracker.
        
        Args:
            config_file: Path to tracked users JSON file
        """
        self.config_file = config_file
        self._users = []
        self._load_users()
        
    def _load_users(self):
        """Load tracked users from JSON file."""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self._users = data.get('tracked_users', [])
                logger.info(f"Loaded {len(self._users)} tracked users")
            else:
                logger.warning(f"Tracked users file not found: {self.config_file}")
                self._users = []
        except Exception as e:
            logger.error(f"Error loading tracked users: {e}")
            self._users = []
            
    def _save_users(self):
        """Save tracked users to JSON file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'tracked_users': self._users}, f, indent=2)
            logger.info(f"Saved {len(self._users)} tracked users")
        except Exception as e:
            logger.error(f"Error saving tracked users: {e}")
            
    def get_all_users(self) -> List[Dict]:
        """
        Get all tracked users.
        
        Returns:
            List of user dictionaries with 'name' and 'wallet' keys
        """
        return self._users.copy()
        
    def get_wallet_addresses(self) -> List[str]:
        """
        Get list of all tracked wallet addresses.
        
        Returns:
            List of wallet address strings
        """
        return [user['wallet'] for user in self._users]
        
    def get_user_by_wallet(self, wallet: str) -> Optional[Dict]:
        """
        Get user info by wallet address.
        
        Args:
            wallet: Wallet address
            
        Returns:
            User dictionary or None
        """
        for user in self._users:
            if user['wallet'].lower() == wallet.lower():
                return user
        return None
        
    def get_user_name(self, wallet: str) -> str:
        """
        Get user name by wallet address, or return shortened address.
        
        Args:
            wallet: Wallet address
            
        Returns:
            User name or formatted address
        """
        user = self.get_user_by_wallet(wallet)
        if user:
            return user['name']
        # Return shortened address if not found
        return f"{wallet[:6]}...{wallet[-4:]}" if len(wallet) > 10 else wallet
        
    def add_user(self, name: str, wallet: str) -> bool:
        """
        Add a new tracked user.
        
        Args:
            name: User display name
            wallet: Wallet address
            
        Returns:
            True if added, False if already exists
        """
        # Check if wallet already exists
        if self.get_user_by_wallet(wallet):
            logger.warning(f"User with wallet {wallet} already exists")
            return False
            
        self._users.append({
            'name': name,
            'wallet': wallet
        })
        self._save_users()
        return True
        
    def remove_user(self, wallet: str) -> bool:
        """
        Remove a tracked user.
        
        Args:
            wallet: Wallet address to remove
            
        Returns:
            True if removed, False if not found
        """
        for i, user in enumerate(self._users):
            if user['wallet'].lower() == wallet.lower():
                self._users.pop(i)
                self._save_users()
                return True
        return False
        
    def update_user_name(self, wallet: str, new_name: str) -> bool:
        """
        Update a user's display name.
        
        Args:
            wallet: Wallet address
            new_name: New display name
            
        Returns:
            True if updated, False if not found
        """
        user = self.get_user_by_wallet(wallet)
        if user:
            user['name'] = new_name
            self._save_users()
            return True
        return False
        
    def is_tracked(self, wallet: str) -> bool:
        """
        Check if a wallet is being tracked.
        
        Args:
            wallet: Wallet address
            
        Returns:
            True if tracked, False otherwise
        """
        return self.get_user_by_wallet(wallet) is not None
        
    def count(self) -> int:
        """
        Get number of tracked users.
        
        Returns:
            Count of tracked users
        """
        return len(self._users)


# Global instance
_tracker_instance: Optional[UserTracker] = None


def get_user_tracker(config_file: str = "tracked_users.json") -> UserTracker:
    """
    Get or create the global UserTracker instance.
    
    Args:
        config_file: Path to tracked users JSON file
        
    Returns:
        UserTracker instance
    """
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = UserTracker(config_file)
    return _tracker_instance


if __name__ == "__main__":
    # Test the tracker
    tracker = UserTracker("tracked_users.json")
    
    print(f"Loaded {tracker.count()} tracked users:")
    for user in tracker.get_all_users():
        print(f"  - {user['name']}: {user['wallet']}")
