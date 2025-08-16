"""
Test utilities for data management and cleanup.
Provides common utilities for integration and unit tests.
"""

import os
import tempfile
import json
import shutil
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, AsyncMock
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType

from src.storage import StorageService, NicknameEntry


class TestStorageManager:
    """Manages test storage files and cleanup."""
    __test__ = False  # Prevent pytest from collecting this as a test class
    
    def __init__(self):
        """Initialize the test storage manager."""
        self.temp_files: List[str] = []
        self.temp_dirs: List[str] = []
        self.storage_services: List[StorageService] = []
    
    def create_temp_file(self, suffix: str = '.json', content: Optional[str] = None) -> str:
        """
        Create a temporary file for testing.
        
        Args:
            suffix: File suffix (default: .json)
            content: Optional content to write to file
            
        Returns:
            Path to the temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        
        if content:
            temp_file.write(content.encode())
        
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def create_temp_dir(self) -> str:
        """
        Create a temporary directory for testing.
        
        Returns:
            Path to the temporary directory
        """
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def create_storage_service(self, file_path: Optional[str] = None) -> StorageService:
        """
        Create a storage service for testing.
        
        Args:
            file_path: Optional path to storage file
            
        Returns:
            StorageService instance
        """
        if not file_path:
            file_path = self.create_temp_file()
        
        storage = StorageService(file_path)
        self.storage_services.append(storage)
        return storage
    
    def create_storage_with_data(self, data: Dict[str, Dict[str, Dict[str, Any]]]) -> StorageService:
        """
        Create a storage service with predefined data.
        
        Args:
            data: Storage data in the format {group_id: {user_id: entry_data}}
            
        Returns:
            StorageService instance with data
        """
        file_path = self.create_temp_file()
        
        # Write data to file
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        return self.create_storage_service(file_path)
    
    def cleanup(self):
        """Clean up all temporary files and directories."""
        # Clean up temporary files
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception:
                pass  # Ignore cleanup errors
        
        # Clean up temporary directories
        for dir_path in self.temp_dirs:
            try:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
            except Exception:
                pass  # Ignore cleanup errors
        
        # Clear lists
        self.temp_files.clear()
        self.temp_dirs.clear()
        self.storage_services.clear()


class MockMessageFactory:
    """Factory for creating mock Telegram messages."""
    __test__ = False  # Prevent pytest from collecting this as a test class
    
    @staticmethod
    def create_group_message(
        user_id: int = 12345,
        username: str = "testuser",
        group_id: int = -100123456789,
        group_title: str = "Test Group",
        text: str = "/test"
    ) -> MagicMock:
        """
        Create a mock group message.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            group_id: Telegram group ID
            group_title: Group title
            text: Message text
            
        Returns:
            Mock Message object
        """
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        message.text = text
        message.from_user = User(
            id=user_id,
            is_bot=False,
            first_name="Test",
            username=username
        )
        message.chat = Chat(
            id=group_id,
            type=ChatType.GROUP,
            title=group_title
        )
        return message
    
    @staticmethod
    def create_private_message(
        user_id: int = 12345,
        username: str = "testuser",
        text: str = "/test"
    ) -> MagicMock:
        """
        Create a mock private message.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            text: Message text
            
        Returns:
            Mock Message object
        """
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        message.text = text
        message.from_user = User(
            id=user_id,
            is_bot=False,
            first_name="Test",
            username=username
        )
        message.chat = Chat(
            id=user_id,
            type=ChatType.PRIVATE,
            title=None
        )
        return message
    
    @staticmethod
    def create_supergroup_message(
        user_id: int = 12345,
        username: str = "testuser",
        group_id: int = -1001234567890,
        group_title: str = "Test Supergroup",
        text: str = "/test"
    ) -> MagicMock:
        """
        Create a mock supergroup message.
        
        Args:
            user_id: Telegram user ID
            username: Telegram username
            group_id: Telegram supergroup ID
            group_title: Supergroup title
            text: Message text
            
        Returns:
            Mock Message object
        """
        message = MagicMock(spec=Message)
        message.answer = AsyncMock()
        message.text = text
        message.from_user = User(
            id=user_id,
            is_bot=False,
            first_name="Test",
            username=username
        )
        message.chat = Chat(
            id=group_id,
            type=ChatType.SUPERGROUP,
            title=group_title
        )
        return message


class TestDataGenerator:
    """Generates test data for various scenarios."""
    __test__ = False  # Prevent pytest from collecting this as a test class
    
    @staticmethod
    def create_nickname_entry(
        user_id: int = 12345,
        username: str = "testuser",
        nickname: str = "TestNick",
        added_at: str = "2024-01-01T12:00:00"
    ) -> NicknameEntry:
        """
        Create a nickname entry for testing.
        
        Args:
            user_id: User ID
            username: Username
            nickname: Nickname
            added_at: Timestamp
            
        Returns:
            NicknameEntry instance
        """
        return NicknameEntry(
            user_id=user_id,
            username=username,
            nickname=nickname,
            added_at=added_at
        )
    
    @staticmethod
    def create_storage_data(num_groups: int = 1, users_per_group: int = 3) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Create storage data for testing.
        
        Args:
            num_groups: Number of groups to create
            users_per_group: Number of users per group
            
        Returns:
            Storage data dictionary
        """
        data = {}
        
        for group_idx in range(num_groups):
            group_id = str(-100000000000 - group_idx)
            data[group_id] = {}
            
            for user_idx in range(users_per_group):
                user_id = str(10000 + user_idx)
                username = f"user{user_idx + 1}"
                nickname = f"Nick{user_idx + 1}"
                
                data[group_id][user_id] = {
                    "user_id": int(user_id),
                    "username": username,
                    "nickname": nickname,
                    "added_at": f"2024-01-{user_idx + 1:02d}T12:00:00"
                }
        
        return data
    
    @staticmethod
    def create_corrupted_storage_data() -> str:
        """
        Create corrupted storage data for testing error handling.
        
        Returns:
            Corrupted JSON string
        """
        return '{"invalid": json, "missing": quotes}'
    
    @staticmethod
    def create_invalid_storage_structure() -> Dict[str, Any]:
        """
        Create invalid storage structure for testing.
        
        Returns:
            Invalid storage data
        """
        return {
            "not_a_group_id": {
                "not_a_user_id": "not_an_object"
            },
            "-123456": {
                "789": {
                    "user_id": 789,
                    "username": "testuser",
                    # Missing required fields: nickname, added_at
                }
            }
        }


class AssertionHelpers:
    """Helper methods for common test assertions."""
    __test__ = False  # Prevent pytest from collecting this as a test class
    
    @staticmethod
    def assert_success_message(call_args: str):
        """Assert that a message indicates success."""
        assert "✅" in call_args or "success" in call_args.lower()
    
    @staticmethod
    def assert_error_message(call_args: str):
        """Assert that a message indicates an error."""
        assert "❌" in call_args or "error" in call_args.lower()
    
    @staticmethod
    def assert_warning_message(call_args: str):
        """Assert that a message indicates a warning."""
        assert "⚠️" in call_args or "warning" in call_args.lower()
    
    @staticmethod
    def assert_info_message(call_args: str):
        """Assert that a message is informational."""
        assert "📝" in call_args or "ℹ️" in call_args or "info" in call_args.lower()
    
    @staticmethod
    def assert_list_message(call_args: str):
        """Assert that a message is a list."""
        assert "📋" in call_args or "list" in call_args.lower()
    
    @staticmethod
    def assert_contains_command_syntax(call_args: str, command: str):
        """Assert that a message contains command syntax."""
        assert command in call_args
    
    @staticmethod
    def assert_nickname_in_list(call_args: str, username: str, nickname: str):
        """Assert that a nickname appears in a list message."""
        expected_format = f"{username} - {nickname}"
        assert expected_format in call_args
    
    @staticmethod
    def assert_numbered_list(call_args: str):
        """Assert that a message contains a numbered list."""
        assert "1." in call_args or "2." in call_args


class TestScenarios:
    """Predefined test scenarios for common use cases."""
    __test__ = False  # Prevent pytest from collecting this as a test class
    
    @staticmethod
    def get_complete_workflow_scenario():
        """Get a complete workflow test scenario."""
        return {
            "description": "Complete nickname lifecycle",
            "steps": [
                {"command": "/add TestNick", "expected": "success"},
                {"command": "/all", "expected": "list with TestNick"},
                {"command": "/change NewNick", "expected": "success"},
                {"command": "/all", "expected": "list with NewNick"},
                {"command": "/remove", "expected": "success"},
                {"command": "/all", "expected": "empty list"}
            ]
        }
    
    @staticmethod
    def get_error_handling_scenario():
        """Get an error handling test scenario."""
        return {
            "description": "Error handling workflow",
            "steps": [
                {"command": "/add", "expected": "missing parameter error"},
                {"command": "/change NewNick", "expected": "no nickname error"},
                {"command": "/remove", "expected": "no nickname error"},
                {"command": "/add " + "a" * 51, "expected": "validation error"}
            ]
        }
    
    @staticmethod
    def get_multi_user_scenario():
        """Get a multi-user test scenario."""
        return {
            "description": "Multiple users in same group",
            "users": [
                {"id": 111, "username": "user1", "nickname": "Nick1"},
                {"id": 222, "username": "user2", "nickname": "Nick2"},
                {"id": 333, "username": "user3", "nickname": "Nick3"}
            ]
        }
    
    @staticmethod
    def get_group_isolation_scenario():
        """Get a group isolation test scenario."""
        return {
            "description": "Group isolation testing",
            "groups": [
                {"id": -100111111111, "title": "Group 1", "nickname": "Group1Nick"},
                {"id": -100222222222, "title": "Group 2", "nickname": "Group2Nick"}
            ]
        }


def create_test_environment():
    """
    Create a complete test environment with all utilities.
    
    Returns:
        Dictionary containing all test utilities
    """
    return {
        "storage_manager": TestStorageManager(),
        "message_factory": MockMessageFactory(),
        "data_generator": TestDataGenerator(),
        "assertions": AssertionHelpers(),
        "scenarios": TestScenarios()
    }


def cleanup_test_environment(env: Dict[str, Any]):
    """
    Clean up a test environment.
    
    Args:
        env: Test environment dictionary
    """
    if "storage_manager" in env:
        env["storage_manager"].cleanup()