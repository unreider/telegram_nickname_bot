"""
Simplified integration tests for complete command workflows.
Tests bot functionality by calling handlers directly with proper context.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType

from src.storage import StorageService
from tests.test_utils import TestStorageManager, MockMessageFactory, AssertionHelpers


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


@pytest.fixture
def assertions():
    """Fixture for assertion helpers."""
    return AssertionHelpers()


class TestIntegratedCommandWorkflows:
    """Integration tests for complete command workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_nickname_lifecycle(self, test_storage_manager, message_factory, assertions):
        """Test complete nickname lifecycle: add -> list -> change -> remove."""
        # Setup storage
        storage = test_storage_manager.create_storage_service()
        
        # Create message
        message = message_factory.create_group_message(text="/add TestNickname")
        
        # Import handlers
        from src.handlers.add import handle_add_command
        from src.handlers.all import handle_all_command
        from src.handlers.change import handle_change_command
        from src.handlers.remove import handle_remove_command
        
        # Test 1: Add nickname
        context = {
            "command_args": ["TestNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        # Verify nickname was added
        assert storage.has_nickname(-100123456789, 12345)
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "TestNickname"
        
        # Verify success message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_success_message(call_args)
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 2: List all nicknames
        context["command_args"] = []
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **context)
        
        # Verify list message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_nickname_in_list(call_args, "testuser", "TestNickname")
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 3: Change nickname
        context["command_args"] = ["NewNickname"]
        
        with patch('src.handlers.change.storage_service', storage):
            await handle_change_command(message, **context)
        
        # Verify nickname was changed
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "NewNickname"
        
        # Verify success message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_success_message(call_args)
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 4: Remove nickname
        context["command_args"] = []
        
        with patch('src.handlers.remove.storage_service', storage):
            await handle_remove_command(message, **context)
        
        # Verify nickname was removed
        assert not storage.has_nickname(-100123456789, 12345)
        
        # Verify success message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_success_message(call_args)
    
    @pytest.mark.asyncio
    async def test_multiple_users_workflow(self, test_storage_manager, message_factory, assertions):
        """Test workflow with multiple users in the same group."""
        storage = test_storage_manager.create_storage_service()
        
        from src.handlers.add import handle_add_command
        from src.handlers.all import handle_all_command
        
        # User 1 adds nickname
        message1 = message_factory.create_group_message(
            user_id=111, username="user1", text="/add Nick1"
        )
        context1 = {
            "command_args": ["Nick1"],
            "user_id": 111,
            "username": "user1",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message1, **context1)
        
        # User 2 adds nickname
        message2 = message_factory.create_group_message(
            user_id=222, username="user2", text="/add Nick2"
        )
        context2 = {
            "command_args": ["Nick2"],
            "user_id": 222,
            "username": "user2",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message2, **context2)
        
        # Verify both nicknames exist
        assert storage.has_nickname(-100123456789, 111)
        assert storage.has_nickname(-100123456789, 222)
        assert storage.get_group_count(-100123456789) == 2
        
        # List all nicknames
        list_context = {
            "command_args": [],
            "user_id": 111,
            "username": "user1",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message1, **list_context)
        
        # Verify list contains both users
        call_args = message1.answer.call_args[0][0]
        assertions.assert_nickname_in_list(call_args, "user1", "Nick1")
        assertions.assert_nickname_in_list(call_args, "user2", "Nick2")
    
    @pytest.mark.asyncio
    async def test_group_isolation_workflow(self, test_storage_manager, message_factory, assertions):
        """Test that groups are properly isolated from each other."""
        storage = test_storage_manager.create_storage_service()
        
        from src.handlers.add import handle_add_command
        from src.handlers.all import handle_all_command
        
        # Same user adds different nicknames in different groups
        message1 = message_factory.create_group_message(
            group_id=-100111111111, text="/add Group1Nick"
        )
        context1 = {
            "command_args": ["Group1Nick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100111111111
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message1, **context1)
        
        message2 = message_factory.create_group_message(
            group_id=-100222222222, text="/add Group2Nick"
        )
        context2 = {
            "command_args": ["Group2Nick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100222222222
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message2, **context2)
        
        # Verify nicknames are isolated by group
        entry1 = storage.get_nickname(-100111111111, 12345)
        entry2 = storage.get_nickname(-100222222222, 12345)
        
        assert entry1.nickname == "Group1Nick"
        assert entry2.nickname == "Group2Nick"
        
        # List nicknames in group 1
        list_context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100111111111
        }
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message1, **list_context)
        
        call_args = message1.answer.call_args[0][0]
        assert "Group1Nick" in call_args
        assert "Group2Nick" not in call_args
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, test_storage_manager, message_factory, assertions):
        """Test error handling throughout the workflow."""
        storage = test_storage_manager.create_storage_service()
        message = message_factory.create_group_message()
        
        from src.handlers.add import handle_add_command
        
        # Test missing parameter
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        # Verify error message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_info_message(call_args)
        assert "Missing" in call_args
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test storage failure
        context["command_args"] = ["TestNick"]
        
        with patch('src.handlers.add.storage_service', storage):
            with patch.object(storage, 'add_nickname', side_effect=Exception("Storage error")):
                await handle_add_command(message, **context)
        
        # Verify error message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_error_message(call_args)
    
    @pytest.mark.asyncio
    async def test_help_and_start_workflow(self, message_factory, assertions):
        """Test help and start command workflows."""
        message = message_factory.create_group_message()
        
        from src.handlers.start import handle_start_command
        from src.handlers.help import handle_help_command
        
        # Test start command
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        await handle_start_command(message, **context)
        
        # Verify start message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "Welcome" in call_args
        assert "/help" in call_args
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test help command
        await handle_help_command(message, **context)
        
        # Verify help message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "Available commands" in call_args
        assert "/add" in call_args
        assert "/all" in call_args


class TestRequirementsValidation:
    """Integration tests to validate all requirements are met."""
    
    @pytest.mark.asyncio
    async def test_requirement_1_start_command(self, message_factory, assertions):
        """Validate Requirement 1: Start command functionality."""
        message = message_factory.create_group_message(text="/start")
        
        from src.handlers.start import handle_start_command
        
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        await handle_start_command(message, **context)
        
        # Verify requirements
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        
        # 1.1: Bot responds with introduction
        assert "Welcome" in call_args or "Hello" in call_args
        
        # 1.2: Bot suggests available commands
        assert "/help" in call_args or "commands" in call_args
        
        # 1.3: Response is in same group chat (verified by mock being called)
        assert message.answer.called
    
    @pytest.mark.asyncio
    async def test_requirement_2_add_command(self, test_storage_manager, message_factory, assertions):
        """Validate Requirement 2: Add command functionality."""
        storage = test_storage_manager.create_storage_service()
        message = message_factory.create_group_message(text="/add TestNickname")
        
        from src.handlers.add import handle_add_command
        
        # Test 2.1: Add nickname successfully
        context = {
            "command_args": ["TestNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        # Verify nickname was stored
        assert storage.has_nickname(-100123456789, 12345)
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "TestNickname"
        assert entry.username == "testuser"
        
        # 2.4: Confirmation message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_success_message(call_args)
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 2.2: Try to add duplicate nickname
        context["command_args"] = ["AnotherNick"]
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        # Verify warning message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "already" in call_args.lower()
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 2.3: Missing nickname parameter
        context["command_args"] = []
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        # Verify prompt message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "Missing" in call_args or "provide" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_requirement_3_all_command(self, test_storage_manager, message_factory, assertions):
        """Validate Requirement 3: All command functionality."""
        storage = test_storage_manager.create_storage_service()
        message = message_factory.create_group_message(text="/all")
        
        from src.handlers.all import handle_all_command
        
        # Test 3.2: Empty list
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **context)
        
        # Verify empty message
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "no nicknames" in call_args.lower() or "empty" in call_args.lower()
        
        # Add some nicknames for testing
        storage.add_nickname(-100123456789, 12345, "testuser", "TestNick")
        storage.add_nickname(-100123456789, 67890, "user2", "Nick2")
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 3.1: List format and 3.3: Consistent ordering
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **context)
        
        # Verify list format
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_nickname_in_list(call_args, "testuser", "TestNick")
        assertions.assert_nickname_in_list(call_args, "user2", "Nick2")
        assertions.assert_numbered_list(call_args)
    
    @pytest.mark.asyncio
    async def test_requirement_4_change_command(self, test_storage_manager, message_factory, assertions):
        """Validate Requirement 4: Change command functionality."""
        storage = test_storage_manager.create_storage_service()
        message = message_factory.create_group_message(text="/change NewNick")
        
        from src.handlers.change import handle_change_command
        
        # Add initial nickname
        storage.add_nickname(-100123456789, 12345, "testuser", "OldNick")
        
        # 4.1: Update existing nickname
        context = {
            "command_args": ["NewNick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.change.storage_service', storage):
            await handle_change_command(message, **context)
        
        # Verify nickname was updated
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "NewNick"
        
        # 4.4: Confirm change
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_success_message(call_args)
    
    @pytest.mark.asyncio
    async def test_requirement_5_remove_command(self, test_storage_manager, message_factory, assertions):
        """Validate Requirement 5: Remove command functionality."""
        storage = test_storage_manager.create_storage_service()
        message = message_factory.create_group_message(text="/remove")
        
        from src.handlers.remove import handle_remove_command
        
        # Add nickname for testing
        storage.add_nickname(-100123456789, 12345, "testuser", "TestNick")
        
        # 5.1: Delete nickname from group storage
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.remove.storage_service', storage):
            await handle_remove_command(message, **context)
        
        # Verify nickname was removed
        assert not storage.has_nickname(-100123456789, 12345)
        
        # 5.3: Confirm removal
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assertions.assert_success_message(call_args)
    
    @pytest.mark.asyncio
    async def test_requirement_6_help_command(self, message_factory, assertions):
        """Validate Requirement 6: Help command functionality."""
        message = message_factory.create_group_message(text="/help")
        
        from src.handlers.help import handle_help_command
        
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        await handle_help_command(message, **context)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        
        # 6.1: List all available commands with descriptions
        assertions.assert_contains_command_syntax(call_args, "/add")
        assertions.assert_contains_command_syntax(call_args, "/all")
        assertions.assert_contains_command_syntax(call_args, "/change")
        assertions.assert_contains_command_syntax(call_args, "/remove")
        
        # 6.2: Include command syntax and purpose
        assert "syntax" in call_args.lower() or "usage" in call_args.lower() or "<" in call_args
        
        # 6.3: Clear and easy to understand
        assert "Available commands" in call_args or "Commands" in call_args
    
    def test_requirement_8_deployment_config(self):
        """Test Requirement 8: Railway deployment configuration."""
        # 8.1: Railway configuration files
        assert os.path.exists("railway.json"), "Railway configuration file should exist"
        
        # 8.2: Environment variables for sensitive data
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
        
        # 8.3: Railway deployment requirements
        assert os.path.exists("requirements.txt"), "Requirements file should exist"
    
    def test_requirement_9_version_control(self):
        """Test Requirement 9: Version control setup."""
        # 9.1: .gitignore file
        assert os.path.exists(".gitignore"), ".gitignore file should exist"
        
        # 9.2: Sensitive information excluded
        with open(".gitignore", "r") as f:
            gitignore_content = f.read()
            assert ".env" in gitignore_content
            assert "__pycache__" in gitignore_content
        
        # 9.3: Documentation
        assert os.path.exists("README.md"), "README.md should exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])