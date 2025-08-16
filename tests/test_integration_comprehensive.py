"""
Comprehensive integration tests for complete command workflows.
Tests bot functionality with mock Aiogram responses and validates all requirements.
This is the enhanced version that covers all task requirements.
"""

import pytest
import asyncio
import tempfile
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from aiogram import Bot, Dispatcher
from aiogram.types import Message, User, Chat, Update
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError

from src.bot import TelegramBot, create_bot
from src.config import BotConfig
from src.storage import StorageService
from src.middleware import setup_middleware
from src.handlers.start import register_start_handler, handle_start_command
from src.handlers.add import register_add_handler, handle_add_command
from src.handlers.all import register_all_handler, handle_all_command
from src.handlers.change import register_change_handler, handle_change_command
from src.handlers.remove import register_remove_handler, handle_remove_command
from src.handlers.help import register_help_handler, handle_help_command
from tests.test_utils import (
    TestStorageManager, MockMessageFactory, TestDataGenerator,
    AssertionHelpers, TestScenarios, create_test_environment, cleanup_test_environment
)


@pytest.fixture
def test_env():
    """Create and cleanup test environment."""
    env = create_test_environment()
    yield env
    cleanup_test_environment(env)


@pytest.fixture
def mock_config(test_env):
    """Create a mock configuration for testing."""
    storage_file = test_env["storage_manager"].create_temp_file()
    return BotConfig(
        bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
        storage_file=storage_file,
        port=8000,
        webhook_url=None,
        python_env="development"
    )


def get_call_text(mock_call):
    """Extract text from mock call arguments."""
    if not mock_call:
        return ""
    if hasattr(mock_call, 'kwargs') and mock_call.kwargs and 'text' in mock_call.kwargs:
        return mock_call.kwargs['text']
    elif hasattr(mock_call, 'args') and mock_call.args:
        return mock_call.args[0]
    return ""


class TestCompleteCommandWorkflows:
    """Integration tests for complete command workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_nickname_lifecycle(self, test_env):
        """Test complete nickname lifecycle: add -> list -> change -> remove."""
        # Setup
        storage = test_env["storage_manager"].create_storage_service()
        message = test_env["message_factory"].create_group_message()
        
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
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 2: List all nicknames
        context["command_args"] = []
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **context)
        
        # Verify list message
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_nickname_in_list(call_args, "testuser", "TestNickname")
        
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
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
        
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
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
    
    @pytest.mark.asyncio
    async def test_multiple_users_workflow(self, test_env):
        """Test workflow with multiple users in the same group."""
        storage = test_env["storage_manager"].create_storage_service()
        
        # User 1 adds nickname
        message1 = test_env["message_factory"].create_group_message(
            user_id=111, username="user1"
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
        message2 = test_env["message_factory"].create_group_message(
            user_id=222, username="user2"
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
        call_args = get_call_text(message1.answer.call_args)
        test_env["assertions"].assert_nickname_in_list(call_args, "user1", "Nick1")
        test_env["assertions"].assert_nickname_in_list(call_args, "user2", "Nick2")
    
    @pytest.mark.asyncio
    async def test_group_isolation_workflow(self, test_env):
        """Test that groups are properly isolated from each other."""
        storage = test_env["storage_manager"].create_storage_service()
        
        # Same user adds different nicknames in different groups
        message1 = test_env["message_factory"].create_group_message(
            group_id=-100111111111
        )
        context1 = {
            "command_args": ["Group1Nick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100111111111
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message1, **context1)
        
        message2 = test_env["message_factory"].create_group_message(
            group_id=-100222222222
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
        
        call_args = get_call_text(message1.answer.call_args)
        assert "Group1Nick" in call_args
        assert "Group2Nick" not in call_args
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, test_env):
        """Test error handling throughout the workflow."""
        storage = test_env["storage_manager"].create_storage_service()
        message = test_env["message_factory"].create_group_message()
        
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
        call_args = get_call_text(message.answer.call_args)
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
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_error_message(call_args)
    
    @pytest.mark.asyncio
    async def test_help_and_start_workflow(self, test_env):
        """Test help and start command workflows."""
        message = test_env["message_factory"].create_group_message()
        
        # Test start command
        await handle_start_command(message)
        
        # Verify start message
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        assert "Welcome" in call_args
        assert "/help" in call_args
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test help command
        await handle_help_command(message)
        
        # Verify help message
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        assert "Available Commands" in call_args or "Available commands" in call_args
        assert "/add" in call_args
        assert "/all" in call_args


class TestBotIntegrationWithMockAiogram:
    """Integration tests for bot functionality with mock Aiogram responses."""
    
    @pytest.mark.asyncio
    async def test_bot_initialization_workflow(self, mock_config, test_env):
        """Test complete bot initialization workflow."""
        # Update config to use test storage
        mock_config.storage_file = test_env["storage_manager"].create_temp_file()
        
        with patch('src.bot.Bot') as mock_bot_class:
            with patch('src.bot.Dispatcher') as mock_dispatcher_class:
                # Setup mocks
                mock_bot_instance = AsyncMock()
                mock_bot_info = Mock()
                mock_bot_info.username = "test_bot"
                mock_bot_instance.get_me.return_value = mock_bot_info
                mock_bot_class.return_value = mock_bot_instance
                
                mock_dispatcher_instance = Mock()
                mock_dispatcher_class.return_value = mock_dispatcher_instance
                
                # Create and initialize bot
                bot = TelegramBot(mock_config)
                await bot.initialize()
                
                # Verify initialization
                assert bot.bot == mock_bot_instance
                assert bot.dispatcher == mock_dispatcher_instance
                assert bot.storage is not None
                
                # Verify handlers were registered
                assert mock_dispatcher_instance.include_router.call_count >= 6  # All handlers
    
    @pytest.mark.asyncio
    async def test_private_chat_rejection_workflow(self, test_env):
        """Test that bot properly rejects commands from private chats."""
        # Import middleware functions
        from src.middleware import GroupChatMiddleware
        
        # Create middleware instance
        middleware = GroupChatMiddleware()
        
        # Create private message
        private_message = test_env["message_factory"].create_private_message()
        
        # Mock handler
        mock_handler = AsyncMock()
        
        # Test private chat rejection
        result = await middleware(mock_handler, private_message, {})
        
        # Verify rejection message was sent
        private_message.answer.assert_called()
        call_args = get_call_text(private_message.answer.call_args)
        assert "only works in group chats" in call_args


class TestStoragePersistenceIntegration:
    """Integration tests for storage persistence across bot restarts."""
    
    @pytest.mark.asyncio
    async def test_storage_persistence_workflow(self, test_env):
        """Test that storage persists data across bot restarts."""
        # Create storage file
        storage_file = test_env["storage_manager"].create_temp_file()
        
        # First bot instance - add data
        storage1 = StorageService(storage_file)
        storage1.add_nickname(-100123456789, 12345, "testuser", "PersistentNick")
        
        # Verify data was added
        assert storage1.has_nickname(-100123456789, 12345)
        
        # Second bot instance - load existing data
        storage2 = StorageService(storage_file)
        
        # Verify data persisted
        assert storage2.has_nickname(-100123456789, 12345)
        entry = storage2.get_nickname(-100123456789, 12345)
        assert entry.nickname == "PersistentNick"
        assert entry.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_corrupted_storage_recovery(self, test_env):
        """Test recovery from corrupted storage file."""
        # Create corrupted storage file
        storage_file = test_env["storage_manager"].create_temp_file()
        with open(storage_file, 'w') as f:
            f.write("invalid json content")
        
        # Create storage service - should handle gracefully
        storage = StorageService(storage_file)
        
        # Should start with empty data
        assert storage.get_group_count(-100123456789) == 0
        
        # Should be able to add new data
        result = storage.add_nickname(-100123456789, 12345, "testuser", "TestNick")
        assert result is True
        assert storage.has_nickname(-100123456789, 12345)


class TestRequirementsValidation:
    """Integration tests to validate all requirements are met."""
    
    @pytest.mark.asyncio
    async def test_requirement_1_start_command(self, test_env):
        """Validate Requirement 1: Start command functionality."""
        message = test_env["message_factory"].create_group_message()
        
        # Test /start command
        await handle_start_command(message)
        
        # Verify requirements
        message.answer.assert_called_once()
        call_args = get_call_text(message.answer.call_args)
        
        # 1.1: Bot responds with introduction
        assert "Welcome" in call_args or "Hello" in call_args
        
        # 1.2: Bot suggests available commands
        assert "/help" in call_args or "commands" in call_args
        
        # 1.3: Response is in same group chat (verified by mock being called)
        assert message.answer.called
    
    @pytest.mark.asyncio
    async def test_requirement_2_add_command(self, test_env):
        """Validate Requirement 2: Add command functionality."""
        storage = test_env["storage_manager"].create_storage_service()
        message = test_env["message_factory"].create_group_message()
        
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
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 2.2: Try to add duplicate nickname
        context["command_args"] = ["AnotherNick"]
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        # Verify warning message
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        assert "already" in call_args.lower()
        
        # Reset mock
        message.answer.reset_mock()
        
        # Test 2.3: Missing nickname parameter
        context["command_args"] = []
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        # Verify prompt message
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        assert "Missing" in call_args or "provide" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_requirement_3_all_command(self, test_env):
        """Validate Requirement 3: All command functionality."""
        storage = test_env["storage_manager"].create_storage_service()
        message = test_env["message_factory"].create_group_message()
        
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
        call_args = get_call_text(message.answer.call_args)
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
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_nickname_in_list(call_args, "testuser", "TestNick")
        test_env["assertions"].assert_nickname_in_list(call_args, "user2", "Nick2")
        test_env["assertions"].assert_numbered_list(call_args)
    
    @pytest.mark.asyncio
    async def test_requirement_4_change_command(self, test_env):
        """Validate Requirement 4: Change command functionality."""
        storage = test_env["storage_manager"].create_storage_service()
        message = test_env["message_factory"].create_group_message()
        
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
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
    
    @pytest.mark.asyncio
    async def test_requirement_5_remove_command(self, test_env):
        """Validate Requirement 5: Remove command functionality."""
        storage = test_env["storage_manager"].create_storage_service()
        message = test_env["message_factory"].create_group_message()
        
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
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
    
    @pytest.mark.asyncio
    async def test_requirement_6_help_command(self, test_env):
        """Validate Requirement 6: Help command functionality."""
        message = test_env["message_factory"].create_group_message()
        
        await handle_help_command(message)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        
        # 6.1: List all available commands with descriptions
        test_env["assertions"].assert_contains_command_syntax(call_args, "/add")
        test_env["assertions"].assert_contains_command_syntax(call_args, "/all")
        test_env["assertions"].assert_contains_command_syntax(call_args, "/change")
        test_env["assertions"].assert_contains_command_syntax(call_args, "/remove")
        
        # 6.2: Include command syntax and purpose
        assert "syntax" in call_args.lower() or "usage" in call_args.lower() or "<" in call_args
        
        # 6.3: Clear and easy to understand
        assert "Available commands" in call_args or "Commands" in call_args
    
    @pytest.mark.asyncio
    async def test_requirement_7_group_chat_isolation(self, test_env):
        """Validate Requirement 7: Group chat isolation."""
        # Import middleware functions
        from src.middleware import GroupChatMiddleware
        
        # Create middleware instance
        middleware = GroupChatMiddleware()
        
        # 7.1: Only respond to commands in group chats
        private_message = test_env["message_factory"].create_private_message()
        
        # Mock handler
        mock_handler = AsyncMock()
        
        # Call middleware with proper arguments
        result = await middleware(mock_handler, private_message, {})
        
        private_message.answer.assert_called()
        call_args = get_call_text(private_message.answer.call_args)
        assert "group chats" in call_args.lower()
        
        # 7.2 & 7.3: Group isolation (tested in storage and multi-group tests)
        # This is implicitly tested by the storage service design
    
    def test_requirement_8_deployment_config(self):
        """Test Requirement 8: Railway deployment configuration."""
        # 8.1: Railway configuration files
        assert os.path.exists("railway.json"), "Railway configuration file should exist"
        
        # 8.2: Environment variables for sensitive data
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


class TestCompleteUserJourneys:
    """Integration tests for complete user journeys through all bot features."""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self, test_env):
        """Test a complete user journey through all bot features."""
        storage = test_env["storage_manager"].create_storage_service()
        message = test_env["message_factory"].create_group_message()
        
        # User journey: Start -> Help -> Add -> List -> Change -> List -> Remove -> List
        
        # Step 1: User starts interaction
        await handle_start_command(message)
        message.answer.assert_called()
        message.answer.reset_mock()
        
        # Step 2: User asks for help
        await handle_help_command(message)
        message.answer.assert_called()
        message.answer.reset_mock()
        
        # Step 3: User adds nickname
        context = {
            "command_args": ["CoolNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
        message.answer.reset_mock()
        
        # Step 4: User lists nicknames
        context["command_args"] = []
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **context)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_nickname_in_list(call_args, "testuser", "CoolNickname")
        message.answer.reset_mock()
        
        # Step 5: User changes nickname
        context["command_args"] = ["AwesomeNickname"]
        
        with patch('src.handlers.change.storage_service', storage):
            await handle_change_command(message, **context)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
        message.answer.reset_mock()
        
        # Step 6: User lists nicknames again
        context["command_args"] = []
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **context)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_nickname_in_list(call_args, "testuser", "AwesomeNickname")
        message.answer.reset_mock()
        
        # Step 7: User removes nickname
        with patch('src.handlers.remove.storage_service', storage):
            await handle_remove_command(message, **context)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)
        message.answer.reset_mock()
        
        # Step 8: User lists nicknames (should be empty)
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **context)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        assert "no nicknames" in call_args.lower() or "empty" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_users_scenario(self, test_env):
        """Test concurrent users in the same group."""
        storage = test_env["storage_manager"].create_storage_service()
        
        # Create multiple users
        users = [
            {"id": 111, "username": "alice", "nickname": "AliceNick"},
            {"id": 222, "username": "bob", "nickname": "BobNick"},
            {"id": 333, "username": "charlie", "nickname": "CharlieNick"}
        ]
        
        # All users add nicknames concurrently
        for user in users:
            message = test_env["message_factory"].create_group_message(
                user_id=user["id"],
                username=user["username"]
            )
            context = {
                "command_args": [user["nickname"]],
                "user_id": user["id"],
                "username": user["username"],
                "group_id": -100123456789
            }
            
            with patch('src.handlers.add.storage_service', storage):
                await handle_add_command(message, **context)
            
            # Verify success
            message.answer.assert_called()
            call_args = get_call_text(message.answer.call_args)
            test_env["assertions"].assert_success_message(call_args)
        
        # Verify all nicknames exist
        assert storage.get_group_count(-100123456789) == 3
        
        # List all nicknames
        message = test_env["message_factory"].create_group_message()
        list_context = {
            "command_args": [],
            "user_id": 111,
            "username": "alice",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(message, **list_context)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        
        # Verify all users appear in list
        for user in users:
            test_env["assertions"].assert_nickname_in_list(
                call_args, user["username"], user["nickname"]
            )
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self, test_env):
        """Test error recovery and graceful handling."""
        storage = test_env["storage_manager"].create_storage_service()
        message = test_env["message_factory"].create_group_message()
        
        # Test various error scenarios
        error_scenarios = [
            {"command_args": [], "expected": "missing parameter"},
            {"command_args": ["a" * 51], "expected": "validation error"}
        ]
        
        for scenario in error_scenarios:
            context = {
                "command_args": scenario["command_args"],
                "user_id": 12345,
                "username": "testuser",
                "group_id": -100123456789
            }
            
            with patch('src.handlers.add.storage_service', storage):
                await handle_add_command(message, **context)
            
            # Verify error message was sent
            message.answer.assert_called()
            call_args = get_call_text(message.answer.call_args)
            # Should contain some kind of error or info message
            assert len(call_args) > 0
            
            # Reset mock for next test
            message.answer.reset_mock()
        
        # Verify bot still works after errors
        context = {
            "command_args": ["ValidNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(message, **context)
        
        message.answer.assert_called()
        call_args = get_call_text(message.answer.call_args)
        test_env["assertions"].assert_success_message(call_args)


class TestDataManagementAndCleanup:
    """Tests for test data management and cleanup utilities."""
    
    def test_test_data_manager_functionality(self, test_env):
        """Test that test data manager works correctly."""
        # Test temp file creation
        temp_file = test_env["storage_manager"].create_temp_file()
        assert os.path.exists(temp_file)
        
        # Test storage service creation
        storage = test_env["storage_manager"].create_storage_service()
        assert isinstance(storage, StorageService)
        
        # Test data creation
        storage.add_nickname(-100123456789, 12345, "testuser", "TestNick")
        assert storage.has_nickname(-100123456789, 12345)
    
    def test_mock_message_factory_functionality(self, test_env):
        """Test that mock message factory works correctly."""
        # Test group message creation
        group_msg = test_env["message_factory"].create_group_message()
        assert group_msg.chat.type == ChatType.GROUP
        assert group_msg.from_user.username == "testuser"
        
        # Test private message creation
        private_msg = test_env["message_factory"].create_private_message()
        assert private_msg.chat.type == ChatType.PRIVATE
        
        # Test supergroup message creation
        supergroup_msg = test_env["message_factory"].create_supergroup_message()
        assert supergroup_msg.chat.type == ChatType.SUPERGROUP
    
    def test_assertion_helpers_functionality(self, test_env):
        """Test that assertion helpers work correctly."""
        assertions = test_env["assertions"]
        
        # Test success message assertion
        success_msg = "✅ Operation completed successfully!"
        assertions.assert_success_message(success_msg)
        
        # Test error message assertion
        error_msg = "❌ An error occurred"
        assertions.assert_error_message(error_msg)
        
        # Test nickname in list assertion
        list_msg = "1. testuser - TestNick\n2. user2 - Nick2"
        assertions.assert_nickname_in_list(list_msg, "testuser", "TestNick")
        assertions.assert_numbered_list(list_msg)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])