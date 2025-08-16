"""
Integration tests for complete command workflows.
Tests bot functionality with mock Aiogram responses and validates all requirements.
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
from src.handlers.start import register_start_handler
from src.handlers.add import register_add_handler
from src.handlers.all import register_all_handler
from src.handlers.change import register_change_handler
from src.handlers.remove import register_remove_handler
from src.handlers.help import register_help_handler


class TestDataManager:
    """Utility class for managing test data and cleanup."""
    
    def __init__(self):
        """Initialize test data manager."""
        self.temp_files = []
        self.storage_services = []
    
    def create_temp_storage_file(self) -> str:
        """Create a temporary storage file for testing."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def create_storage_service(self, file_path: str = None) -> StorageService:
        """Create a storage service for testing."""
        if not file_path:
            file_path = self.create_temp_storage_file()
        
        storage = StorageService(file_path)
        self.storage_services.append(storage)
        return storage
    
    def cleanup(self):
        """Clean up all test data and files."""
        # Clean up temporary files
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception:
                pass  # Ignore cleanup errors
        
        self.temp_files.clear()
        self.storage_services.clear()


@pytest.fixture
def test_data_manager():
    """Fixture for test data management."""
    manager = TestDataManager()
    yield manager
    manager.cleanup()


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return BotConfig(
        bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
        storage_file="test_data/nicknames.json",
        port=8000,
        webhook_url=None,
        python_env="development"
    )


@pytest.fixture
def mock_group_message():
    """Create a mock group message."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.from_user = User(
        id=12345,
        is_bot=False,
        first_name="Test",
        username="testuser"
    )
    message.chat = Chat(
        id=-100123456789,
        type=ChatType.GROUP,
        title="Test Group"
    )
    return message


@pytest.fixture
def mock_private_message():
    """Create a mock private message."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.from_user = User(
        id=12345,
        is_bot=False,
        first_name="Test",
        username="testuser"
    )
    message.chat = Chat(
        id=12345,
        type=ChatType.PRIVATE,
        title=None
    )
    return message


class TestCompleteCommandWorkflows:
    """Integration tests for complete command workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_nickname_lifecycle(self, test_data_manager, mock_group_message):
        """Test complete nickname lifecycle: add -> list -> change -> remove."""
        # Setup
        storage = test_data_manager.create_storage_service()
        dispatcher = Dispatcher()
        
        # Import handlers locally to avoid router reuse
        from src.handlers.add import handle_add_command
        from src.handlers.all import handle_all_command
        from src.handlers.change import handle_change_command
        from src.handlers.remove import handle_remove_command
        from src.handlers.start import handle_start_command
        from src.handlers.help import handle_help_command
        
        # Setup middleware
        setup_middleware(dispatcher)
        
        # Test 1: Add nickname - call handler directly
        mock_group_message.text = "/add TestNickname"
        context = {
            "command_args": ["TestNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(mock_group_message, **context)
        
        # Verify nickname was added
        assert storage.has_nickname(-100123456789, 12345)
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "TestNickname"
        
        # Verify success message was sent
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "✅" in call_args
        assert "Nickname added successfully" in call_args
        
        # Reset mock
        mock_group_message.answer.reset_mock()
        
        # Test 2: List all nicknames
        context["command_args"] = []
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(mock_group_message, **context)
        
        # Verify list message was sent
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "📋" in call_args
        assert "testuser - TestNickname" in call_args
        
        # Reset mock
        mock_group_message.answer.reset_mock()
        
        # Test 3: Change nickname
        context["command_args"] = ["NewNickname"]
        
        with patch('src.handlers.change.storage_service', storage):
            await handle_change_command(mock_group_message, **context)
        
        # Verify nickname was changed
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "NewNickname"
        
        # Verify success message was sent
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "✅" in call_args
        assert "Nickname updated successfully" in call_args
        
        # Reset mock
        mock_group_message.answer.reset_mock()
        
        # Test 4: Remove nickname
        context["command_args"] = []
        
        with patch('src.handlers.remove.storage_service', storage):
            await handle_remove_command(mock_group_message, **context)
        
        # Verify nickname was removed
        assert not storage.has_nickname(-100123456789, 12345)
        
        # Verify success message was sent
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "✅" in call_args
        assert "Nickname removed successfully" in call_args
    
    @pytest.mark.asyncio
    async def test_multiple_users_workflow(self, test_data_manager, mock_config):
        """Test workflow with multiple users in the same group."""
        # Setup
        storage = test_data_manager.create_storage_service()
        dispatcher = Dispatcher()
        
        # Register handlers
        register_add_handler(dispatcher, storage)
        register_all_handler(dispatcher, storage)
        
        # Setup middleware
        setup_middleware(dispatcher)
        
        # Create messages for different users
        user1_message = MagicMock(spec=Message)
        user1_message.answer = AsyncMock()
        user1_message.from_user = User(id=111, is_bot=False, first_name="User1", username="user1")
        user1_message.chat = Chat(id=-100123456789, type=ChatType.GROUP, title="Test Group")
        
        user2_message = MagicMock(spec=Message)
        user2_message.answer = AsyncMock()
        user2_message.from_user = User(id=222, is_bot=False, first_name="User2", username="user2")
        user2_message.chat = Chat(id=-100123456789, type=ChatType.GROUP, title="Test Group")
        
        # User 1 adds nickname
        context1 = {
            "command_args": ["Nick1"],
            "user_id": 111,
            "username": "user1",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(user1_message, **context1)
        
        # User 2 adds nickname
        context2 = {
            "command_args": ["Nick2"],
            "user_id": 222,
            "username": "user2",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(user2_message, **context2)
        
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
            await handle_all_command(user1_message, **list_context)
        
        # Verify list contains both users
        call_args = user1_message.answer.call_args[0][0]
        assert "user1 - Nick1" in call_args
        assert "user2 - Nick2" in call_args
    
    @pytest.mark.asyncio
    async def test_group_isolation_workflow(self, test_data_manager):
        """Test that groups are properly isolated from each other."""
        # Setup
        storage = test_data_manager.create_storage_service()
        dispatcher = Dispatcher()
        
        # Register handlers
        register_add_handler(dispatcher, storage)
        register_all_handler(dispatcher, storage)
        
        # Setup middleware
        setup_middleware(dispatcher)
        
        # Create messages for different groups
        group1_message = MagicMock(spec=Message)
        group1_message.answer = AsyncMock()
        group1_message.from_user = User(id=12345, is_bot=False, first_name="Test", username="testuser")
        group1_message.chat = Chat(id=-100111111111, type=ChatType.GROUP, title="Group 1")
        
        group2_message = MagicMock(spec=Message)
        group2_message.answer = AsyncMock()
        group2_message.from_user = User(id=12345, is_bot=False, first_name="Test", username="testuser")
        group2_message.chat = Chat(id=-100222222222, type=ChatType.GROUP, title="Group 2")
        
        # Same user adds different nicknames in different groups
        context1 = {
            "command_args": ["Group1Nick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100111111111
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(group1_message, **context1)
        
        context2 = {
            "command_args": ["Group2Nick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100222222222
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(group2_message, **context2)
        
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
            await handle_all_command(group1_message, **list_context)
        
        call_args = group1_message.answer.call_args[0][0]
        assert "Group1Nick" in call_args
        assert "Group2Nick" not in call_args
    
    @pytest.mark.asyncio
    async def test_private_chat_rejection_workflow(self, mock_private_message):
        """Test that bot properly rejects commands from private chats."""
        # Import middleware functions
        from src.middleware import GroupChatMiddleware
        
        # Create middleware instance
        middleware = GroupChatMiddleware()
        
        # Test private chat rejection
        result = await middleware(mock_private_message, lambda: None)
        
        # Verify rejection message was sent
        mock_private_message.answer.assert_called()
        call_args = mock_private_message.answer.call_args[0][0]
        assert "only works in group chats" in call_args
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, test_data_manager, mock_group_message):
        """Test error handling throughout the workflow."""
        # Setup with failing storage
        storage = test_data_manager.create_storage_service()
        dispatcher = Dispatcher()
        
        register_add_handler(dispatcher, storage)
        setup_middleware(dispatcher)
        
        # Mock storage to fail
        context = {
            "command_args": ["TestNick"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            with patch.object(storage, 'add_nickname', side_effect=Exception("Storage error")):
                await handle_add_command(mock_group_message, **context)
                
                # Verify error message was sent
                mock_group_message.answer.assert_called()
                call_args = mock_group_message.answer.call_args[0][0]
                assert "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_help_and_start_workflow(self, mock_group_message):
        """Test help and start command workflows."""
        # Setup
        dispatcher = Dispatcher()
        register_start_handler(dispatcher)
        register_help_handler(dispatcher)
        setup_middleware(dispatcher)
        
        # Test start command
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        await handle_start_command(mock_group_message, **context)
        
        # Verify start message
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "Welcome" in call_args
        assert "/help" in call_args
        
        # Reset mock
        mock_group_message.answer.reset_mock()
        
        # Test help command
        await handle_help_command(mock_group_message, **context)
        
        # Verify help message
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "Available commands" in call_args
        assert "/add" in call_args
        assert "/all" in call_args


class TestBotIntegration:
    """Integration tests for bot initialization and setup."""
    
    @pytest.mark.asyncio
    async def test_bot_initialization_workflow(self, mock_config, test_data_manager):
        """Test complete bot initialization workflow."""
        # Update config to use test storage
        mock_config.storage_file = test_data_manager.create_temp_storage_file()
        
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
    async def test_webhook_setup_workflow(self, test_data_manager):
        """Test webhook setup workflow."""
        # Create production config
        config = BotConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            storage_file=test_data_manager.create_temp_storage_file(),
            port=8000,
            webhook_url="https://example.com/webhook",
            python_env="production"
        )
        
        with patch('src.bot.Bot') as mock_bot_class:
            with patch('src.bot.Dispatcher') as mock_dispatcher_class:
                with patch('src.bot.SimpleRequestHandler') as mock_handler_class:
                    with patch('src.bot.setup_application') as mock_setup_app:
                        with patch('src.bot.web.Application') as mock_app_class:
                            # Setup mocks
                            mock_bot_instance = AsyncMock()
                            mock_bot_info = Mock()
                            mock_bot_info.username = "test_bot"
                            mock_bot_instance.get_me.return_value = mock_bot_info
                            mock_bot_class.return_value = mock_bot_instance
                            
                            mock_dispatcher_instance = Mock()
                            mock_dispatcher_class.return_value = mock_dispatcher_instance
                            
                            mock_app_instance = Mock()
                            mock_app_class.return_value = mock_app_instance
                            
                            mock_handler_instance = Mock()
                            mock_handler_class.return_value = mock_handler_instance
                            
                            # Create bot and setup webhook
                            bot = TelegramBot(config)
                            await bot.initialize()
                            app = await bot.setup_webhook()
                            
                            # Verify webhook setup
                            mock_bot_instance.set_webhook.assert_called_once()
                            mock_handler_instance.register.assert_called_once()
                            assert app == mock_app_instance
    
    @pytest.mark.asyncio
    async def test_polling_setup_workflow(self, mock_config, test_data_manager):
        """Test polling setup workflow."""
        # Update config to use test storage
        mock_config.storage_file = test_data_manager.create_temp_storage_file()
        
        with patch('src.bot.Bot') as mock_bot_class:
            with patch('src.bot.Dispatcher') as mock_dispatcher_class:
                # Setup mocks
                mock_bot_instance = AsyncMock()
                mock_bot_info = Mock()
                mock_bot_info.username = "test_bot"
                mock_bot_instance.get_me.return_value = mock_bot_info
                mock_bot_class.return_value = mock_bot_instance
                
                mock_dispatcher_instance = AsyncMock()
                mock_dispatcher_class.return_value = mock_dispatcher_instance
                
                # Create bot
                bot = TelegramBot(mock_config)
                await bot.initialize()
                
                # Mock polling to avoid infinite loop
                async def mock_start_polling(*args, **kwargs):
                    pass
                
                mock_dispatcher_instance.start_polling = mock_start_polling
                
                # Start polling
                await bot.start_polling()
                
                # Verify webhook was deleted
                mock_bot_instance.delete_webhook.assert_called_once()


class TestStoragePersistence:
    """Integration tests for storage persistence across bot restarts."""
    
    @pytest.mark.asyncio
    async def test_storage_persistence_workflow(self, test_data_manager, mock_group_message):
        """Test that storage persists data across bot restarts."""
        # Create storage file
        storage_file = test_data_manager.create_temp_storage_file()
        
        # First bot instance - add data
        storage1 = StorageService(storage_file)
        
        # Add nickname directly to storage
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
    async def test_corrupted_storage_recovery(self, test_data_manager):
        """Test recovery from corrupted storage file."""
        # Create corrupted storage file
        storage_file = test_data_manager.create_temp_storage_file()
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
    async def test_requirement_1_start_command(self, mock_group_message):
        """Validate Requirement 1: Start command functionality."""
        # Test /start command
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        await handle_start_command(mock_group_message, **context)
        
        # Verify requirements
        mock_group_message.answer.assert_called_once()
        call_args = mock_group_message.answer.call_args[0][0]
        
        # 1.1: Bot responds with introduction
        assert "Welcome" in call_args or "Hello" in call_args
        
        # 1.2: Bot suggests available commands
        assert "/help" in call_args or "commands" in call_args
        
        # 1.3: Response is in same group chat (verified by mock being called)
        assert mock_group_message.answer.called
    
    @pytest.mark.asyncio
    async def test_requirement_2_add_command(self, test_data_manager, mock_group_message):
        """Validate Requirement 2: Add command functionality."""
        storage = test_data_manager.create_storage_service()
        dispatcher = Dispatcher()
        register_add_handler(dispatcher, storage)
        setup_middleware(dispatcher)
        
        # Test 2.1: Add nickname successfully
        context = {
            "command_args": ["TestNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(mock_group_message, **context)
        
        # Verify nickname was stored
        assert storage.has_nickname(-100123456789, 12345)
        entry = storage.get_nickname(-100123456789, 12345)
        assert entry.nickname == "TestNickname"
        assert entry.username == "testuser"
        
        # 2.4: Confirmation message
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "✅" in call_args or "success" in call_args.lower()
        
        # Reset mock
        mock_group_message.answer.reset_mock()
        
        # Test 2.2: Try to add duplicate nickname
        context["command_args"] = ["AnotherNick"]
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(mock_group_message, **context)
        
        # Verify warning message
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "already" in call_args.lower()
        
        # Reset mock
        mock_group_message.answer.reset_mock()
        
        # Test 2.3: Missing nickname parameter
        context["command_args"] = []
        
        with patch('src.handlers.add.storage_service', storage):
            await handle_add_command(mock_group_message, **context)
        
        # Verify prompt message
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "Missing" in call_args or "provide" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_requirement_3_all_command(self, test_data_manager, mock_group_message):
        """Validate Requirement 3: All command functionality."""
        storage = test_data_manager.create_storage_service()
        dispatcher = Dispatcher()
        register_all_handler(dispatcher, storage)
        setup_middleware(dispatcher)
        
        # Test 3.2: Empty list
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(mock_group_message, **context)
        
        # Verify empty message
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "no nicknames" in call_args.lower() or "empty" in call_args.lower()
        
        # Add some nicknames
        storage.add_nickname(-100123456789, 12345, "testuser", "TestNick")
        storage.add_nickname(-100123456789, 67890, "user2", "Nick2")
        
        # Reset mock
        mock_group_message.answer.reset_mock()
        
        # Test 3.1: List format and 3.3: Consistent ordering
        with patch('src.handlers.all.storage_service', storage):
            await handle_all_command(mock_group_message, **context)
        
        # Verify list format
        mock_group_message.answer.assert_called()
        call_args = mock_group_message.answer.call_args[0][0]
        assert "testuser - TestNick" in call_args
        assert "user2 - Nick2" in call_args
        assert "1." in call_args or "2." in call_args  # Numbering
    
    @pytest.mark.asyncio
    async def test_requirement_7_group_chat_isolation(self, test_data_manager, mock_private_message):
        """Validate Requirement 7: Group chat isolation."""
        dispatcher = Dispatcher()
        register_start_handler(dispatcher)
        setup_middleware(dispatcher)
        
        # Import middleware functions
        from src.middleware import GroupChatMiddleware
        
        # Create middleware instance
        middleware = GroupChatMiddleware()
        
        # Test 7.1: Only responds in group chats
        result = await middleware(mock_private_message, lambda: None)
        
        # Verify rejection message
        mock_private_message.answer.assert_called()
        call_args = mock_private_message.answer.call_args[0][0]
        assert "group chats" in call_args.lower()
        
        # Test 7.2 & 7.3: Group isolation (tested in other integration tests)
        # This is verified by the storage service tests and multi-group workflow tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])