"""
Unit tests for the storage service.
"""

import json
import os
import tempfile
import pytest
from datetime import datetime
from unittest.mock import patch, mock_open

from src.storage import StorageService, NicknameEntry


class TestStorageService:
    """Test cases for StorageService class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Use a temporary file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        self.temp_file.close()
        self.storage = StorageService(self.temp_file.name)
    
    def teardown_method(self):
        """Clean up after each test method."""
        # Remove temporary file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def test_init_creates_data_directory(self):
        """Test that initialization creates the data directory if it doesn't exist."""
        # Test with a path that includes a directory
        test_path = os.path.join(tempfile.gettempdir(), 'test_storage', 'nicknames.json')
        storage = StorageService(test_path)
        
        # Directory should be created
        assert os.path.exists(os.path.dirname(test_path))
        
        # Clean up
        if os.path.exists(test_path):
            os.unlink(test_path)
        os.rmdir(os.path.dirname(test_path))
    
    def test_add_nickname_success(self):
        """Test successfully adding a nickname."""
        result = self.storage.add_nickname(
            group_id=-123456,
            user_id=789,
            username="testuser",
            nickname="TestNick"
        )
        
        assert result is True
        assert self.storage.has_nickname(-123456, 789)
        
        entry = self.storage.get_nickname(-123456, 789)
        assert entry is not None
        assert entry.user_id == 789
        assert entry.username == "testuser"
        assert entry.nickname == "TestNick"
        assert entry.added_at is not None
    
    def test_add_nickname_duplicate(self):
        """Test that adding a duplicate nickname returns False."""
        # Add first nickname
        self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        
        # Try to add another nickname for the same user
        result = self.storage.add_nickname(-123456, 789, "testuser", "AnotherNick")
        
        assert result is False
        # Original nickname should remain
        entry = self.storage.get_nickname(-123456, 789)
        assert entry.nickname == "TestNick"
    
    def test_get_nickname_not_found(self):
        """Test getting a nickname that doesn't exist."""
        result = self.storage.get_nickname(-123456, 999)
        assert result is None
    
    def test_get_all_nicknames_empty_group(self):
        """Test getting all nicknames from an empty group."""
        result = self.storage.get_all_nicknames(-123456)
        assert result == []
    
    def test_get_all_nicknames_with_data(self):
        """Test getting all nicknames from a group with data."""
        # Add multiple nicknames
        self.storage.add_nickname(-123456, 789, "user1", "Nick1")
        self.storage.add_nickname(-123456, 790, "user2", "Nick2")
        self.storage.add_nickname(-123456, 791, "user3", "Nick3")
        
        result = self.storage.get_all_nicknames(-123456)
        
        assert len(result) == 3
        # Should be ordered by addition time
        nicknames = [entry.nickname for entry in result]
        assert nicknames == ["Nick1", "Nick2", "Nick3"]
    
    def test_update_nickname_success(self):
        """Test successfully updating a nickname."""
        # Add initial nickname
        self.storage.add_nickname(-123456, 789, "testuser", "OldNick")
        
        # Update nickname
        result = self.storage.update_nickname(-123456, 789, "NewNick")
        
        assert result is True
        entry = self.storage.get_nickname(-123456, 789)
        assert entry.nickname == "NewNick"
        assert entry.username == "testuser"  # Other data preserved
    
    def test_update_nickname_not_found(self):
        """Test updating a nickname that doesn't exist."""
        result = self.storage.update_nickname(-123456, 999, "NewNick")
        assert result is False
    
    def test_remove_nickname_success(self):
        """Test successfully removing a nickname."""
        # Add nickname
        self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        
        # Remove nickname
        result = self.storage.remove_nickname(-123456, 789)
        
        assert result is True
        assert not self.storage.has_nickname(-123456, 789)
        assert self.storage.get_nickname(-123456, 789) is None
    
    def test_remove_nickname_not_found(self):
        """Test removing a nickname that doesn't exist."""
        result = self.storage.remove_nickname(-123456, 999)
        assert result is False
    
    def test_remove_nickname_cleans_empty_group(self):
        """Test that removing the last nickname cleans up empty group data."""
        # Add nickname
        self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        
        # Remove nickname
        self.storage.remove_nickname(-123456, 789)
        
        # Group should be cleaned up
        assert self.storage.get_group_count(-123456) == 0
    
    def test_has_nickname(self):
        """Test checking if a user has a nickname."""
        assert not self.storage.has_nickname(-123456, 789)
        
        self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        assert self.storage.has_nickname(-123456, 789)
        
        self.storage.remove_nickname(-123456, 789)
        assert not self.storage.has_nickname(-123456, 789)
    
    def test_get_group_count(self):
        """Test getting the count of nicknames in a group."""
        assert self.storage.get_group_count(-123456) == 0
        
        self.storage.add_nickname(-123456, 789, "user1", "Nick1")
        assert self.storage.get_group_count(-123456) == 1
        
        self.storage.add_nickname(-123456, 790, "user2", "Nick2")
        assert self.storage.get_group_count(-123456) == 2
        
        self.storage.remove_nickname(-123456, 789)
        assert self.storage.get_group_count(-123456) == 1
    
    def test_multiple_groups_isolation(self):
        """Test that data is properly isolated between different groups."""
        # Add nicknames to different groups
        self.storage.add_nickname(-111, 789, "user1", "Nick1")
        self.storage.add_nickname(-222, 789, "user1", "Nick2")
        
        # Each group should only see its own data
        assert self.storage.get_group_count(-111) == 1
        assert self.storage.get_group_count(-222) == 1
        
        entry1 = self.storage.get_nickname(-111, 789)
        entry2 = self.storage.get_nickname(-222, 789)
        
        assert entry1.nickname == "Nick1"
        assert entry2.nickname == "Nick2"
    
    def test_json_persistence_save_and_load(self):
        """Test that data is properly saved to and loaded from JSON file."""
        # Add some data
        self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        self.storage.add_nickname(-123456, 790, "user2", "Nick2")
        
        # Create new storage instance with same file
        new_storage = StorageService(self.temp_file.name)
        
        # Data should be loaded from file
        assert new_storage.has_nickname(-123456, 789)
        assert new_storage.has_nickname(-123456, 790)
        
        entry = new_storage.get_nickname(-123456, 789)
        assert entry.nickname == "TestNick"
        assert entry.username == "testuser"
    
    def test_json_load_corrupted_file(self):
        """Test handling of corrupted JSON file."""
        # Write invalid JSON to file
        with open(self.temp_file.name, 'w') as f:
            f.write("invalid json content")
        
        # Should handle gracefully and start with empty data
        storage = StorageService(self.temp_file.name)
        assert storage.get_group_count(-123456) == 0
    
    def test_json_load_nonexistent_file(self):
        """Test handling of nonexistent JSON file."""
        # Remove the temp file
        os.unlink(self.temp_file.name)
        
        # Should handle gracefully and start with empty data
        storage = StorageService(self.temp_file.name)
        assert storage.get_group_count(-123456) == 0
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_save_data_io_error(self, mock_open):
        """Test handling of IO errors during save."""
        # Add data
        self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        
        # Should handle IO error gracefully (data remains in memory)
        assert self.storage.has_nickname(-123456, 789)
    
    def test_add_nickname_invalid_parameters(self):
        """Test add_nickname with invalid parameters."""
        # Test invalid group_id type
        result = self.storage.add_nickname("invalid", 789, "testuser", "TestNick")
        assert result is False
        
        # Test invalid user_id type
        result = self.storage.add_nickname(-123456, "invalid", "testuser", "TestNick")
        assert result is False
        
        # Test invalid username
        result = self.storage.add_nickname(-123456, 789, None, "TestNick")
        assert result is False
        
        result = self.storage.add_nickname(-123456, 789, "", "TestNick")
        assert result is False
        
        # Test invalid nickname
        result = self.storage.add_nickname(-123456, 789, "testuser", None)
        assert result is False
        
        result = self.storage.add_nickname(-123456, 789, "testuser", "")
        assert result is False
    
    def test_update_nickname_invalid_parameters(self):
        """Test update_nickname with invalid parameters."""
        # Add a valid nickname first
        self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        
        # Test invalid group_id type
        result = self.storage.update_nickname("invalid", 789, "NewNick")
        assert result is False
        
        # Test invalid user_id type
        result = self.storage.update_nickname(-123456, "invalid", "NewNick")
        assert result is False
        
        # Test invalid new_nickname
        result = self.storage.update_nickname(-123456, 789, None)
        assert result is False
        
        result = self.storage.update_nickname(-123456, 789, "")
        assert result is False
    
    def test_remove_nickname_invalid_parameters(self):
        """Test remove_nickname with invalid parameters."""
        # Add a valid nickname first
        self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        
        # Test invalid group_id type
        result = self.storage.remove_nickname("invalid", 789)
        assert result is False
        
        # Test invalid user_id type
        result = self.storage.remove_nickname(-123456, "invalid")
        assert result is False
    
    def test_load_data_invalid_structure(self):
        """Test loading data with invalid JSON structure."""
        # Write invalid structure to file
        invalid_data = {
            "not_a_group_id": {
                "not_a_user_id": "not_an_object"
            }
        }
        
        with open(self.temp_file.name, 'w') as f:
            json.dump(invalid_data, f)
        
        # Should handle gracefully and skip invalid entries
        storage = StorageService(self.temp_file.name)
        assert storage.get_group_count(-123456) == 0
    
    def test_load_data_missing_fields(self):
        """Test loading data with missing required fields."""
        # Write data with missing fields
        invalid_data = {
            "-123456": {
                "789": {
                    "user_id": 789,
                    "username": "testuser",
                    # Missing nickname and added_at
                }
            }
        }
        
        with open(self.temp_file.name, 'w') as f:
            json.dump(invalid_data, f)
        
        # Should handle gracefully and skip invalid entries
        storage = StorageService(self.temp_file.name)
        assert storage.get_group_count(-123456) == 0
    
    def test_load_data_permission_error(self):
        """Test loading data with permission error."""
        # Create file and remove read permissions
        with open(self.temp_file.name, 'w') as f:
            json.dump({}, f)
        
        os.chmod(self.temp_file.name, 0o000)  # No permissions
        
        try:
            # Should handle gracefully and start with empty data
            storage = StorageService(self.temp_file.name)
            assert storage.get_group_count(-123456) == 0
        finally:
            # Restore permissions for cleanup
            os.chmod(self.temp_file.name, 0o644)
    
    @patch('src.storage.StorageService._save_data', side_effect=Exception("Save error"))
    def test_operations_with_save_failure(self, mock_save):
        """Test that operations continue even if save fails."""
        # Operations should succeed in memory even if save fails
        result = self.storage.add_nickname(-123456, 789, "testuser", "TestNick")
        assert result is True
        assert self.storage.has_nickname(-123456, 789)
        
        result = self.storage.update_nickname(-123456, 789, "NewNick")
        assert result is True
        
        entry = self.storage.get_nickname(-123456, 789)
        assert entry.nickname == "NewNick"
        
        result = self.storage.remove_nickname(-123456, 789)
        assert result is True
        assert not self.storage.has_nickname(-123456, 789)
    
    def test_nickname_entry_dataclass(self):
        """Test NicknameEntry dataclass functionality."""
        entry = NicknameEntry(
            user_id=789,
            username="testuser",
            nickname="TestNick",
            added_at="2023-01-01T12:00:00"
        )
        
        assert entry.user_id == 789
        assert entry.username == "testuser"
        assert entry.nickname == "TestNick"
        assert entry.added_at == "2023-01-01T12:00:00"
        
        # Test conversion to dict
        entry_dict = entry.__dict__
        assert entry_dict['user_id'] == 789
        assert entry_dict['nickname'] == "TestNick"


if __name__ == "__main__":
    pytest.main([__file__])