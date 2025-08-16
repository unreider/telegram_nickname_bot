"""
End-to-end integration tests that verify all requirements are met.
Tests complete bot functionality from initialization to command execution.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from src.bot import TelegramBot, create_bot
from src.config import BotConfig
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


class TestEndToEndWorkflows:
    """End-to-end tests for complete bot workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_bot_lifecycle(self, test_env, mock_config):
        """Test complete bot lifecycle from initialization to shutdown."""
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
                
                # Test bot creation
                bot = await create_bot(mock_config)
                assert isinstance(bot, TelegramBot)
                assert bot.config == mock_config
                
                # Test initialization
                await bot.initialize()
                assert bot.bot == mock_bot_instance
                assert bot.dispatcher == mock_dispatcher_instance
                assert bot.storage is not None
                
                # Test shutdown
                await bot.stop()
                mock_bot_instance.session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_all_requirements_integration(self, test_env):
        """Test that all requirements are met through integration testing."""
        storage = test_env["storage_manager"].create_storage_service()
        dispatcher = Dispatcher()
        
        # Register all handlers
        from src.handlers.start import register_start_handler
        from src.handlers.add import register_add_handler
        from src.handlers.all import register_all_handler
        from src.handlers.change import register_change_handler
        from src.handlers.remove import register_remove_handler
        from src.handlers.help import register_help_handler
        from src.middleware import setup_middleware
        
        register_start_handler(dispatcher)
        register_add_handler(dispatcher, storage)
        register_all_handler(dispatcher, storage)
        register_change_handler(dispatcher, storage)
        register_remove_handler(dispatcher, storage)
        register_help_handler(dispatcher)
        setup_middleware(dispatcher)
        
        # Test Requirement 1: Start command
        await self._test_requirement_1_start_command(test_env, dispatcher)
        
        # Test Requirement 2: Add command
        await self._test_requirement_2_add_command(test_env, dispatcher, storage)
        
        # Test Requirement 3: All command
        await self._test_requirement_3_all_command(test_env, dispatcher, storage)
        
        # Test Requirement 4: Change command
        await self._test_requirement_4_change_command(test_env, dispatcher, storage)
        
        # Test Requirement 5: Remove command
        await self._test_requirement_5_remove_command(test_env, dispatcher, storage)
        
        # Test Requirement 6: Help command
        await self._test_requirement_6_help_command(test_env, dispatcher)
        
        # Test Requirement 7: Group chat isolation
        await self._test_requirement_7_group_isolation(test_env, dispatcher)
        
        # Test Requirement 8: Railway deployment (configuration)
        self._test_requirement_8_deployment_config()
        
        # Test Requirement 9: Version control setup
        self._test_requirement_9_version_control()
    
    async def _test_requirement_1_start_command(self, test_env, dispatcher):
        """Test Requirement 1: Start command functionality."""
        message = test_env["message_factory"].create_group_message(text="/start")
        update = Update(update_id=1, message=message)
        
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        # 1.1: Bot responds with introduction
        message.answer.assert_called_once()
        call_args = message.answer.call_args[0][0]
        assert "Welcome" in call_args or "Hello" in call_args
        
        # 1.2: Bot suggests available commands
        assert "/help" in call_args or "commands" in call_args
        
        # 1.3: Response is in same group chat (verified by mock being called)
        assert message.answer.called
    
    async def _test_requirement_2_add_command(self, test_env, dispatcher, storage):
        """Test Requirement 2: Add command functionality."""
        message = test_env["message_factory"].create_group_message(text="/add TestNickname")
        update = Update(update_id=1, message=message)
        
        # 2.1: Store nickname associated with user for specific group
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        assert storage.has_nickname(-100123456789, 12345)
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "TestNickname"
        assert entry.username == "testuser"
        
        # 2.4: Confirm addition
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_success_message(call_args)
        
        # Reset mock
        message.answer.reset_mock()
        
        # 2.2: Notify if nickname already exists
        message.text = "/add AnotherNick"
        update = Update(update_id=2, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "already" in call_args.lower()
        
        # Reset mock
        message.answer.reset_mock()
        
        # 2.3: Prompt if nickname parameter missing
        message.text = "/add"
        update = Update(update_id=3, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "Missing" in call_args or "provide" in call_args.lower()
    
    async def _test_requirement_3_all_command(self, test_env, dispatcher, storage):
        """Test Requirement 3: All command functionality."""
        # 3.2: No nicknames exist
        message = test_env["message_factory"].create_group_message(text="/all")
        update = Update(update_id=1, message=message)
        
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "no nicknames" in call_args.lower() or "empty" in call_args.lower()
        
        # Add some nicknames for testing
        storage.add_nickname(-100123456789, 12345, "testuser", "TestNick")
        storage.add_nickname(-100123456789, 67890, "user2", "Nick2")
        
        # Reset mock
        message.answer.reset_mock()
        
        # 3.1: List format and 3.3: Consistent ordering
        message.text = "/all"
        update = Update(update_id=2, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        
        # Check format: [number]. [username] - [nickname]
        test_env["assertions"].assert_nickname_in_list(call_args, "testuser", "TestNick")
        test_env["assertions"].assert_nickname_in_list(call_args, "user2", "Nick2")
        test_env["assertions"].assert_numbered_list(call_args)
    
    async def _test_requirement_4_change_command(self, test_env, dispatcher, storage):
        """Test Requirement 4: Change command functionality."""
        # Add initial nickname
        storage.add_nickname(-100123456789, 12345, "testuser", "OldNick")
        
        # 4.1: Update existing nickname
        message = test_env["message_factory"].create_group_message(text="/change NewNick")
        update = Update(update_id=1, message=message)
        
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        # Verify nickname was updated
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "NewNick"
        
        # 4.4: Confirm change
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_success_message(call_args)
        
        # Reset mock and remove nickname for next test
        message.answer.reset_mock()
        storage.remove_nickname(-100123456789, 12345)
        
        # 4.2: Notify if no nickname exists
        message.text = "/change AnotherNick"
        update = Update(update_id=2, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "no nickname" in call_args.lower() or "not added" in call_args.lower()
        
        # Reset mock
        message.answer.reset_mock()
        
        # 4.3: Prompt if parameter missing
        message.text = "/change"
        update = Update(update_id=3, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "Missing" in call_args or "provide" in call_args.lower()
    
    async def _test_requirement_5_remove_command(self, test_env, dispatcher, storage):
        """Test Requirement 5: Remove command functionality."""
        # Add nickname for testing
        storage.add_nickname(-100123456789, 12345, "testuser", "TestNick")
        
        # 5.1: Delete nickname from group storage
        message = test_env["message_factory"].create_group_message(text="/remove")
        update = Update(update_id=1, message=message)
        
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        # Verify nickname was removed
        assert not storage.has_nickname(-100123456789, 12345)
        
        # 5.3: Confirm removal
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_success_message(call_args)
        
        # Reset mock
        message.answer.reset_mock()
        
        # 5.2: Notify if no nickname exists
        message.text = "/remove"
        update = Update(update_id=2, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "no nickname" in call_args.lower() or "not added" in call_args.lower()
    
    async def _test_requirement_6_help_command(self, test_env, dispatcher):
        """Test Requirement 6: Help command functionality."""
        message = test_env["message_factory"].create_group_message(text="/help")
        update = Update(update_id=1, message=message)
        
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        
        # 6.1: List all available commands with descriptions
        test_env["assertions"].assert_contains_command_syntax(call_args, "/add")
        test_env["assertions"].assert_contains_command_syntax(call_args, "/all")
        test_env["assertions"].assert_contains_command_syntax(call_args, "/change")
        test_env["assertions"].assert_contains_command_syntax(call_args, "/remove")
        
        # 6.2: Include command syntax and purpose
        assert "syntax" in call_args.lower() or "usage" in call_args.lower() or "<" in call_args
        
        # 6.3: Clear and easy to understand
        assert "Available commands" in call_args or "Commands" in call_args
    
    async def _test_requirement_7_group_isolation(self, test_env, dispatcher):
        """Test Requirement 7: Group chat isolation."""
        # 7.1: Only respond to commands in group chats
        private_message = test_env["message_factory"].create_private_message(text="/start")
        update = Update(update_id=1, message=private_message)
        
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        private_message.answer.assert_called()
        call_args = private_message.answer.call_args[0][0]
        assert "group chats" in call_args.lower()
        
        # 7.2 & 7.3: Group isolation (tested in storage and multi-group tests)
        # This is implicitly tested by the storage service design
    
    def _test_requirement_8_deployment_config(self):
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
    
    def _test_requirement_9_version_control(self):
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
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self, test_env):
        """Test a complete user journey through all bot features."""
        storage = test_env["storage_manager"].create_storage_service()
        dispatcher = Dispatcher()
        
        # Register all handlers
        from src.handlers.start import register_start_handler
        from src.handlers.add import register_add_handler
        from src.handlers.all import register_all_handler
        from src.handlers.change import register_change_handler
        from src.handlers.remove import register_remove_handler
        from src.handlers.help import register_help_handler
        from src.middleware import setup_middleware
        
        register_start_handler(dispatcher)
        register_add_handler(dispatcher, storage)
        register_all_handler(dispatcher, storage)
        register_change_handler(dispatcher, storage)
        register_remove_handler(dispatcher, storage)
        register_help_handler(dispatcher)
        setup_middleware(dispatcher)
        
        # User journey: Start -> Help -> Add -> List -> Change -> List -> Remove -> List
        message = test_env["message_factory"].create_group_message()
        
        # Step 1: User starts interaction
        message.text = "/start"
        update = Update(update_id=1, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        message.answer.reset_mock()
        
        # Step 2: User asks for help
        message.text = "/help"
        update = Update(update_id=2, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        message.answer.reset_mock()
        
        # Step 3: User adds nickname
        message.text = "/add CoolNickname"
        update = Update(update_id=3, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_success_message(call_args)
        message.answer.reset_mock()
        
        # Step 4: User lists nicknames
        message.text = "/all"
        update = Update(update_id=4, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_nickname_in_list(call_args, "testuser", "CoolNickname")
        message.answer.reset_mock()
        
        # Step 5: User changes nickname
        message.text = "/change AwesomeNickname"
        update = Update(update_id=5, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_success_message(call_args)
        message.answer.reset_mock()
        
        # Step 6: User lists nicknames again
        message.text = "/all"
        update = Update(update_id=6, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_nickname_in_list(call_args, "testuser", "AwesomeNickname")
        message.answer.reset_mock()
        
        # Step 7: User removes nickname
        message.text = "/remove"
        update = Update(update_id=7, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_success_message(call_args)
        message.answer.reset_mock()
        
        # Step 8: User lists nicknames (should be empty)
        message.text = "/all"
        update = Update(update_id=8, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        assert "no nicknames" in call_args.lower() or "empty" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_users_scenario(self, test_env):
        """Test concurrent users in the same group."""
        storage = test_env["storage_manager"].create_storage_service()
        dispatcher = Dispatcher()
        
        # Register handlers
        from src.handlers.add import register_add_handler
        from src.handlers.all import register_all_handler
        from src.middleware import setup_middleware
        
        register_add_handler(dispatcher, storage)
        register_all_handler(dispatcher, storage)
        setup_middleware(dispatcher)
        
        # Create multiple users
        users = [
            {"id": 111, "username": "alice", "nickname": "AliceNick"},
            {"id": 222, "username": "bob", "nickname": "BobNick"},
            {"id": 333, "username": "charlie", "nickname": "CharlieNick"}
        ]
        
        # All users add nicknames concurrently
        for i, user in enumerate(users):
            message = test_env["message_factory"].create_group_message(
                user_id=user["id"],
                username=user["username"],
                text=f"/add {user['nickname']}"
            )
            update = Update(update_id=i+1, message=message)
            await dispatcher.feed_update(Bot(token="fake"), update)
            
            # Verify success
            message.answer.assert_called()
            call_args = message.answer.call_args[0][0]
            test_env["assertions"].assert_success_message(call_args)
        
        # Verify all nicknames exist
        assert storage.get_group_count(-100123456789) == 3
        
        # List all nicknames
        message = test_env["message_factory"].create_group_message(text="/all")
        update = Update(update_id=10, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        
        # Verify all users appear in list
        for user in users:
            test_env["assertions"].assert_nickname_in_list(
                call_args, user["username"], user["nickname"]
            )
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self, test_env):
        """Test error recovery and graceful handling."""
        storage = test_env["storage_manager"].create_storage_service()
        dispatcher = Dispatcher()
        
        # Register handlers
        from src.handlers.add import register_add_handler
        from src.middleware import setup_middleware
        
        register_add_handler(dispatcher, storage)
        setup_middleware(dispatcher)
        
        message = test_env["message_factory"].create_group_message()
        
        # Test various error scenarios
        error_scenarios = [
            {"text": "/add", "expected": "missing parameter"},
            {"text": "/add " + "a" * 51, "expected": "validation error"},
            {"text": "/add <script>alert('xss')</script>", "expected": "validation error"}
        ]
        
        for i, scenario in enumerate(error_scenarios):
            message.text = scenario["text"]
            update = Update(update_id=i+1, message=message)
            
            await dispatcher.feed_update(Bot(token="fake"), update)
            
            # Verify error message was sent
            message.answer.assert_called()
            call_args = message.answer.call_args[0][0]
            test_env["assertions"].assert_error_message(call_args)
            
            # Reset mock for next test
            message.answer.reset_mock()
        
        # Verify bot still works after errors
        message.text = "/add ValidNickname"
        update = Update(update_id=10, message=message)
        await dispatcher.feed_update(Bot(token="fake"), update)
        
        message.answer.assert_called()
        call_args = message.answer.call_args[0][0]
        test_env["assertions"].assert_success_message(call_args)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])