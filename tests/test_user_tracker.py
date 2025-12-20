"""
Tests for user tracking functionality.
"""

import pytest
import csv
import tempfile
from pathlib import Path
from utils.user_tracker import UserTracker, get_user_tracker


class TestUserTracker:
    """Test suite for UserTracker class."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary CSV config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'address'])
            writer.writeheader()
            writer.writerow({'name': 'Test User 1', 'address': '0x1111111111111111111111111111111111111111'})
            writer.writerow({'name': 'Test User 2', 'address': '0x2222222222222222222222222222222222222222'})
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def tracker(self, temp_config_file):
        """Create a UserTracker instance with test data."""
        return UserTracker(temp_config_file)
    
    def test_load_users(self, tracker):
        """Test loading users from config file."""
        users = tracker.get_all_users()
        assert len(users) == 2
        assert users[0]['name'] == "Test User 1"
        assert users[1]['name'] == "Test User 2"
    
    def test_get_wallet_addresses(self, tracker):
        """Test getting list of wallet addresses."""
        addresses = tracker.get_wallet_addresses()
        assert len(addresses) == 2
        assert "0x1111111111111111111111111111111111111111" in addresses
        assert "0x2222222222222222222222222222222222222222" in addresses
    
    def test_get_user_by_wallet(self, tracker):
        """Test retrieving user by wallet address."""
        user = tracker.get_user_by_wallet("0x1111111111111111111111111111111111111111")
        assert user is not None
        assert user['name'] == "Test User 1"
        
        # Test case insensitive
        user = tracker.get_user_by_wallet("0X1111111111111111111111111111111111111111")
        assert user is not None
        
        # Test non-existent wallet
        user = tracker.get_user_by_wallet("0x9999999999999999999999999999999999999999")
        assert user is None
    
    def test_get_user_name(self, tracker):
        """Test getting user name by wallet."""
        name = tracker.get_user_name("0x1111111111111111111111111111111111111111")
        assert name == "Test User 1"
        
        # Test unknown wallet returns shortened address
        name = tracker.get_user_name("0x9999999999999999999999999999999999999999")
        assert "0x9999" in name
        assert "9999" in name
    
    def test_add_user(self, tracker):
        """Test adding a new user."""
        result = tracker.add_user("Test User 3", "0x3333333333333333333333333333333333333333")
        assert result is True
        assert tracker.count() == 3
        
        # Test adding duplicate
        result = tracker.add_user("Test User 3 Duplicate", "0x3333333333333333333333333333333333333333")
        assert result is False
        assert tracker.count() == 3
    
    def test_remove_user(self, tracker):
        """Test removing a user."""
        result = tracker.remove_user("0x1111111111111111111111111111111111111111")
        assert result is True
        assert tracker.count() == 1
        
        # Test removing non-existent user
        result = tracker.remove_user("0x9999999999999999999999999999999999999999")
        assert result is False
    
    def test_update_user_name(self, tracker):
        """Test updating user's display name."""
        result = tracker.update_user_name("0x1111111111111111111111111111111111111111", "Updated Name")
        assert result is True
        
        user = tracker.get_user_by_wallet("0x1111111111111111111111111111111111111111")
        assert user['name'] == "Updated Name"
        
        # Test updating non-existent user
        result = tracker.update_user_name("0x9999999999999999999999999999999999999999", "New Name")
        assert result is False
    
    def test_is_tracked(self, tracker):
        """Test checking if wallet is tracked."""
        assert tracker.is_tracked("0x1111111111111111111111111111111111111111") is True
        assert tracker.is_tracked("0x9999999999999999999999999999999999999999") is False
    
    def test_count(self, tracker):
        """Test counting tracked users."""
        assert tracker.count() == 2
        
        tracker.add_user("Test User 3", "0x3333333333333333333333333333333333333333")
        assert tracker.count() == 3
        
        tracker.remove_user("0x3333333333333333333333333333333333333333")
        assert tracker.count() == 2
    
    def test_empty_config_file(self):
        """Test handling of non-existent config file."""
        tracker = UserTracker("nonexistent.csv")
        assert tracker.count() == 0
        assert tracker.get_all_users() == []
    
    def test_csv_persistence(self, temp_config_file):
        """Test that changes are persisted to CSV file."""
        tracker1 = UserTracker(temp_config_file)
        tracker1.add_user("Test User 3", "0x3333333333333333333333333333333333333333")
        
        # Create new tracker instance to verify persistence
        tracker2 = UserTracker(temp_config_file)
        assert tracker2.count() == 3
        user = tracker2.get_user_by_wallet("0x3333333333333333333333333333333333333333")
        assert user is not None
        assert user['name'] == "Test User 3"
    
    def test_csv_format(self, temp_config_file):
        """Test that CSV file has correct format."""
        with open(temp_config_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
            assert len(rows) == 2
            assert 'name' in rows[0]
            assert 'address' in rows[0]
            assert rows[0]['name'] == 'Test User 1'
            assert rows[0]['address'] == '0x1111111111111111111111111111111111111111'
