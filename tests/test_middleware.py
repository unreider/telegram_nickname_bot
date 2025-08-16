"""
Unit tests for middleware functionality.
Tests group chat validation and command preprocessing.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, Chat, User
from aiogram.enums import ChatType

from src.middleware import GroupChatMiddleware, CommandValidationMiddleware, setup_middleware


class TestGroupChatMiddleware:
    """Test cases for GroupChatMiddleware."""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing."""
        return GroupChatMiddleware()
    
    @pytest.fixture
    def mock_handler(self):
        """Create mock handler for testing."""
        return AsyncMock()
    
    def create_mock_message(self, chat_type: ChatType, chat_id: int = -123456789, 
                           chat_title: str = "Test Group", text: str = "/start",
                           user_id: int = 12345, username: str = "testuser"):
        """Create a mock message for testing."""
        user = MagicMock(spec=User)
        user.id = user_id
        user.username = username
        user.full_name = "Test User"
        
        chat = MagicMock(spec=Chat)
        chat.id = chat_id
        chat.type = chat_type
        chat.title = chat_title
        
        message = MagicMock(spec=Message)
        message.chat = chat
        message.from_user = user
        message.text = text
        message.answer = AsyncMock()
        
        return message
    
    @pytest.mark.asyncio
    async def test_allows_group_chat(self, middleware, mock_handler):
        """Test that middleware allows messages from group chats."""
        message = self.create_mock_message(ChatType.GROUP)
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
        
        # Data should be populated with group information
        assert data["is_group_chat"] is True
        assert data["group_id"] == -123456789
        assert data["group_title"] == "Test Group"
    
    @pytest.mark.asyncio
    async def test_allows_supergroup_chat(self, middleware, mock_handler):
        """Test that middleware allows messages from supergroup chats."""
        message = self.create_mock_message(ChatType.SUPERGROUP)
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
        
        # Data should be populated with group information
        assert data["is_group_chat"] is True
        assert data["group_id"] == -123456789
    
    @pytest.mark.asyncio
    async def test_blocks_private_chat(self, middleware, mock_handler):
        """Test that middleware blocks messages from private chats."""
        message = self.create_mock_message(ChatType.PRIVATE)
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should not be called
        mock_handler.assert_not_called()
        
        # Should send explanation message
        message.answer.assert_called_once_with(
            "🤖 This bot only works in group chats. "
            "Please add me to a group to use nickname commands!"
        )
        
        # Result should be None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_blocks_channel_chat(self, middleware, mock_handler):
        """Test that middleware blocks messages from channels."""
        message = self.create_mock_message(ChatType.CHANNEL)
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should not be called
        mock_handler.assert_not_called()
        
        # Should send explanation message
        message.answer.assert_called_once()
        
        # Result should be None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_handles_non_message_events(self, middleware, mock_handler):
        """Test that middleware passes through non-message events."""
        non_message_event = MagicMock()  # Not a Message object
        data = {}
        
        result = await middleware(mock_handler, non_message_event, data)
        
        # Handler should be called with original event
        mock_handler.assert_called_once_with(non_message_event, data)
    
    @pytest.mark.asyncio
    async def test_handles_group_without_title(self, middleware, mock_handler):
        """Test handling of groups without titles."""
        message = self.create_mock_message(ChatType.GROUP, chat_title=None)
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
        
        # Should use default title
        assert data["group_title"] == "Unknown Group"


class TestCommandValidationMiddleware:
    """Test cases for CommandValidationMiddleware."""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance for testing."""
        return CommandValidationMiddleware()
    
    @pytest.fixture
    def mock_handler(self):
        """Create mock handler for testing."""
        return AsyncMock()
    
    def create_mock_message(self, text: str, user_id: int = 12345, 
                           username: str = "testuser"):
        """Create a mock message for testing."""
        user = MagicMock(spec=User)
        user.id = user_id
        user.username = username
        user.full_name = "Test User"
        
        message = MagicMock(spec=Message)
        message.text = text
        message.from_user = user
        message.answer = AsyncMock()
        
        return message
    
    @pytest.mark.asyncio
    async def test_processes_valid_command(self, middleware, mock_handler):
        """Test processing of valid bot commands."""
        message = self.create_mock_message("/start")
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
        
        # Data should be populated with command information
        assert data["command"] == "/start"
        assert data["command_args"] == []
        assert data["raw_command_text"] == "/start"
        assert data["user_id"] == 12345
        assert data["username"] == "testuser"
        assert data["user_full_name"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_processes_command_with_arguments(self, middleware, mock_handler):
        """Test processing of commands with arguments."""
        message = self.create_mock_message("/add mynickname")
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
        
        # Data should include command arguments
        assert data["command"] == "/add"
        assert data["command_args"] == ["mynickname"]
        assert data["raw_command_text"] == "/add mynickname"
    
    @pytest.mark.asyncio
    async def test_processes_command_with_multiple_arguments(self, middleware, mock_handler):
        """Test processing of commands with multiple arguments."""
        message = self.create_mock_message("/change my new nickname")
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
        
        # Data should include all arguments
        assert data["command"] == "/change"
        assert data["command_args"] == ["my", "new", "nickname"]
    
    @pytest.mark.asyncio
    async def test_handles_command_with_bot_username(self, middleware, mock_handler):
        """Test handling of commands with bot username."""
        message = self.create_mock_message("/start@nickname_bot")
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
        
        # Command should be cleaned of bot username
        assert data["command"] == "/start"
    
    @pytest.mark.asyncio
    async def test_ignores_unknown_commands(self, middleware, mock_handler):
        """Test that unknown commands are passed through."""
        message = self.create_mock_message("/unknown_command")
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should still be called (let other handlers process it)
        mock_handler.assert_called_once_with(message, data)
    
    @pytest.mark.asyncio
    async def test_ignores_non_command_messages(self, middleware, mock_handler):
        """Test that non-command messages are passed through."""
        message = self.create_mock_message("Hello, this is not a command")
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
    
    @pytest.mark.asyncio
    async def test_handles_message_without_user(self, middleware, mock_handler):
        """Test handling of messages without user information."""
        message = MagicMock(spec=Message)
        message.text = "/start"
        message.from_user = None
        message.answer = AsyncMock()
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should not be called
        mock_handler.assert_not_called()
        
        # Should send error message
        message.answer.assert_called_once_with(
            "❌ Unable to identify user. Please try again."
        )
        
        # Result should be None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_handles_user_without_username(self, middleware, mock_handler):
        """Test handling of users without usernames."""
        message = self.create_mock_message("/start", username=None)
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called
        mock_handler.assert_called_once_with(message, data)
        
        # Should use fallback username
        assert data["username"] == "user_12345"
    
    @pytest.mark.asyncio
    async def test_handles_non_message_events(self, middleware, mock_handler):
        """Test that middleware passes through non-message events."""
        non_message_event = MagicMock()  # Not a Message object
        data = {}
        
        result = await middleware(mock_handler, non_message_event, data)
        
        # Handler should be called with original event
        mock_handler.assert_called_once_with(non_message_event, data)
    
    @pytest.mark.asyncio
    async def test_handles_empty_message(self, middleware, mock_handler):
        """Test handling of messages without text."""
        message = MagicMock(spec=Message)
        message.text = None
        data = {}
        
        result = await middleware(mock_handler, message, data)
        
        # Handler should be called (not a command)
        mock_handler.assert_called_once_with(message, data)


class TestMiddlewareSetup:
    """Test cases for middleware setup function."""
    
    def test_setup_middleware(self):
        """Test that middleware setup registers middleware correctly."""
        mock_dispatcher = MagicMock()
        mock_message_middleware = MagicMock()
        mock_dispatcher.message.middleware = mock_message_middleware
        
        setup_middleware(mock_dispatcher)
        
        # Should register both middleware instances
        assert mock_message_middleware.call_count == 2
        
        # Check that the middleware instances are of correct types
        calls = mock_message_middleware.call_args_list
        assert isinstance(calls[0][0][0], GroupChatMiddleware)
        assert isinstance(calls[1][0][0], CommandValidationMiddleware)