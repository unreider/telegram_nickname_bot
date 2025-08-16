"""
Integration test runner that validates all requirements are met.
Simple test runner that verifies bot functionality works end-to-end.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType

from src.storage import StorageService
from tests.test_utils import TestStorageManager, MockMessageFactory


def get_call_text(mock_call):
    """Extract text from mock call arguments."""
    if not mock_call:
        return ""
    if hasattr(mock_call, 'kwargs') and mock_call.kwargs and 'text' in mock_call.kwargs:
        return mock_call.kwargs['text']
    elif hasattr(mock_call, 'args') and mock_call.args:
        return mock_call.args[0]
    return ""


@pytest.fixture
def test_storage_manager():
    """Fixture for test storage management."""
    manager = TestStorageManager()
    yield manager
    manager.cleanup()


@pytest.fixture
def message_factory():
    """Fixture for message factory."""
    return MockMessageFactory()


class TestIntegrationRunner:
    """Integration test runner for all bot functionality."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow_integration(self, test_storage_manager, message_factory):
        """Test complete workflow integration."""
        # Setup
        storage = test_storage_manager.create_storage_service()
        message = message_factory.create_group_message()
        
        # Import handlers
        from src.handlers.add import handle_add_command
        from src.handlers.all import handle_all_command
        from src.handlers.change import handle_change_command
        from src.handlers.remove import handle_remove_command
        from src.handlers.start import handle_start_command
        from src.handlers.help import handle_help_command
        
        # Test 1: Start command
        await handle_start_command(message)
        assert message.answer.called
        start_text = get_call_text(message.answer.call_args)
        assert "Welcome" in start_text
        message.answer.reset_mock()
        
        # Test 2: Help command
        await handle_help_command(message)
        assert message.answer.called
        help_text = get_call_text(message.answer.call_args)
        assert "Available Commands" in help_text or "Available commands" in help_text
        assert "/add" in help_text
        message.answer.reset_mock()
        
        # Test 3: Add nickname
        kwargs = {
            "command_args": ["TestNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **kwargs)
        
        # Verify nickname was added
        assert storage.has_nickname(-100123456789, 12345)
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "TestNickname"
        
        # Verify success message
        assert message.answer.called
        add_text = get_call_text(message.answer.call_args)
        assert "✅" in add_text or "success" in add_text.lower()
        message.answer.reset_mock()
        
        # Test 4: List nicknames
        kwargs["command_args"] = []
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **kwargs)
        
        assert message.answer.called
        list_text = get_call_text(message.answer.call_args)
        assert "testuser - TestNickname" in list_text
        message.answer.reset_mock()
        
        # Test 5: Change nickname
        kwargs["command_args"] = ["NewNickname"]
        
        with patch('src.handlers.change.storage_service', storage):
            await handle_change_command(message, **kwargs)
        
        # Verify nickname was changed
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "NewNickname"
        
        assert message.answer.called
        change_text = get_call_text(message.answer.call_args)
        assert "✅" in change_text or "success" in change_text.lower()
        message.answer.reset_mock()
        
        # Test 6: Remove nickname
        kwargs["command_args"] = []
        
        with patch('src.handlers.remove.storage_service', storage):
            await handle_remove_command(message, **kwargs)
        
        # Verify nickname was removed
        assert not storage.has_nickname(-100123456789, 12345)
        
        assert message.answer.called
        remove_text = get_call_text(message.answer.call_args)
        assert "✅" in remove_text or "success" in remove_text.lower()
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, test_storage_manager, message_factory):
        """Test error handling integration."""
        storage = test_storage_manager.create_storage_service()
        message = message_factory.create_group_message()
        
        from src.handlers.add import handle_add_command
        
        # Test missing parameter
        kwargs = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **kwargs)
        
        assert message.answer.called
        error_text = get_call_text(message.answer.call_args)
        assert "Missing" in error_text or "provide" in error_text.lower()
    
    @pytest.mark.asyncio
    async def test_multiple_users_integration(self, test_storage_manager, message_factory):
        """Test multiple users integration."""
        storage = test_storage_manager.create_storage_service()
        
        from src.handlers.add import handle_add_command
        from src.handlers.all import handle_all_command
        
        # User 1 adds nickname
        message1 = message_factory.create_group_message(user_id=111, username="user1")
        kwargs1 = {
            "command_args": ["Nick1"],
            "user_id": 111,
            "username": "user1",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message1, **kwargs1)
        
        # User 2 adds nickname
        message2 = message_factory.create_group_message(user_id=222, username="user2")
        kwargs2 = {
            "command_args": ["Nick2"],
            "user_id": 222,
            "username": "user2",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message2, **kwargs2)
        
        # Verify both nicknames exist
        assert storage.has_nickname(-100123456789, 111)
        assert storage.has_nickname(-100123456789, 222)
        assert storage.get_group_count(-100123456789) == 2
        
        # List all nicknames
        list_kwargs = {
            "command_args": [],
            "user_id": 111,
            "username": "user1",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message1, **list_kwargs)
        
        assert message1.answer.called
        list_text = get_call_text(message1.answer.call_args)
        assert "user1 - Nick1" in list_text
        assert "user2 - Nick2" in list_text
    
    @pytest.mark.asyncio
    async def test_group_isolation_integration(self, test_storage_manager, message_factory):
        """Test group isolation integration."""
        storage = test_storage_manager.create_storage_service()
        
        from src.handlers.add import handle_add_command
        
        # Same user in different groups
        message1 = message_factory.create_group_message(group_id=-100111111111)
        kwargs1 = {
            "command_args": ["Group1Nick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100111111111
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message1, **kwargs1)
        
        message2 = message_factory.create_group_message(group_id=-100222222222)
        kwargs2 = {
            "command_args": ["Group2Nick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100222222222
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message2, **kwargs2)
        
        # Verify nicknames are isolated by group
        entry1 = storage.get_nickname(-100111111111, 12345)
        entry2 = storage.get_nickname(-100222222222, 12345)
        
        assert entry1.nickname == "Group1Nick"
        assert entry2.nickname == "Group2Nick"
    
    def test_deployment_configuration(self):
        """Test deployment configuration requirements."""
        # Railway configuration
        assert os.path.exists("railway.json"), "Railway configuration file should exist"
        
        # Requirements file
        assert os.path.exists("requirements.txt"), "Requirements file should exist"
        
        # Configuration handling
        from src.config import BotConfig
        config = BotConfig(
            bot_token="test_token",
            storage_file="test.json",
            port=8000,
            webhook_url="https://example.com/webhook",
            python_env="production"
        )
        assert config.bot_token == "test_token"
        assert config.use_webhook() == True
    
    def test_version_control_setup(self):
        """Test version control setup requirements."""
        # .gitignore file
        assert os.path.exists(".gitignore"), ".gitignore file should exist"
        
        # Sensitive information excluded
        with open(".gitignore", "r") as f:
            gitignore_content = f.read()
            assert ".env" in gitignore_content
            assert "__pycache__" in gitignore_content
        
        # Documentation
        assert os.path.exists("README.md"), "README.md should exist"
    
    @pytest.mark.asyncio
    async def test_storage_persistence_integration(self, test_storage_manager, message_factory):
        """Test storage persistence across restarts."""
        # Create storage file
        storage_file = test_storage_manager.create_temp_file()
        
        # First instance - add data
        storage1 = StorageService(storage_file)
        storage1.add_nickname(-100123456789, 12345, "testuser", "PersistentNick")
        
        # Second instance - load existing data
        storage2 = StorageService(storage_file)
        
        # Verify data persisted
        assert storage2.has_nickname(-100123456789, 12345)
        entry = storage2.get_nickname(-100123456789, 12345)
        assert entry.nickname == "PersistentNick"
        assert entry.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_all_requirements_coverage(self, test_storage_manager, message_factory):
        """Test that all requirements are covered by the implementation."""
        storage = test_storage_manager.create_storage_service()
        message = message_factory.create_group_message()
        
        # Import all handlers
        from src.handlers.start import handle_start_command
        from src.handlers.add import handle_add_command
        from src.handlers.all import handle_all_command
        from src.handlers.change import handle_change_command
        from src.handlers.remove import handle_remove_command
        from src.handlers.help import handle_help_command
        
        # Requirement 1: Start command
        await handle_start_command(message)
        assert message.answer.called
        start_text = get_call_text(message.answer.call_args)
        assert "Welcome" in start_text or "Hello" in start_text
        assert "/help" in start_text or "commands" in start_text
        message.answer.reset_mock()
        
        # Requirement 2: Add command
        kwargs = {
            "command_args": ["TestNick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **kwargs)
        
        assert storage.has_nickname(-100123456789, 12345)
        assert message.answer.called
        message.answer.reset_mock()
        
        # Requirement 3: All command
        kwargs["command_args"] = []
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **kwargs)
        
        assert message.answer.called
        list_text = get_call_text(message.answer.call_args)
        assert "testuser - TestNick" in list_text
        message.answer.reset_mock()
        
        # Requirement 4: Change command
        kwargs["command_args"] = ["NewNick"]
        
        with patch('src.handlers.change.storage_service', storage):
            await handle_change_command(message, **kwargs)
        
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "NewNick"
        assert message.answer.called
        message.answer.reset_mock()
        
        # Requirement 5: Remove command
        kwargs["command_args"] = []
        
        with patch('src.handlers.remove.storage_service', storage):
            await handle_remove_command(message, **kwargs)
        
        assert not storage.has_nickname(-100123456789, 12345)
        assert message.answer.called
        message.answer.reset_mock()
        
        # Requirement 6: Help command
        await handle_help_command(message)
        assert message.answer.called
        help_text = get_call_text(message.answer.call_args)
        assert "/add" in help_text
        assert "/all" in help_text
        assert "/change" in help_text
        assert "/remove" in help_text
        
        # Requirements 7, 8, 9 are tested in other methods
        print("✅ All requirements validated successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])