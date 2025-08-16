"""
Unit tests for the add command handler.
Tests all scenarios for /add command functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType

from src.handlers.add import handle_add_command, register_add_handler
from src.storage import StorageService, NicknameEntry


class TestAddCommandHandler:
    """Test cases for the add command handler."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage service."""
        return MagicMock(spec=StorageService)
    
    @pytest.fixture
    def mock_message(self):
        """Create a mock message object."""
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
    def valid_context(self):
        """Create valid context data from middleware."""
        return {
            "command_args": ["TestNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
    
    @pytest.mark.asyncio
    async def test_add_nickname_success(self, mock_message, mock_storage, valid_context):
        """Test successful nickname addition."""
        # Setup
        mock_storage.has_nickname.return_value = False
        mock_storage.add_nickname.return_value = True
        
        with patch('src.handlers.add.storage_service', mock_storage):
            # Execute
            await handle_add_command(mock_message, **valid_context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.add_nickname.assert_called_once_with(
            group_id=-100123456789,
            user_id=12345,
            username="testuser",
            nickname="TestNickname"
        )
        
        # Verify success message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "✅" in call_args
        assert "Nickname added successfully" in call_args
        assert "TestNickname" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_already_exists(self, mock_message, mock_storage, valid_context):
        """Test adding nickname when user already has one."""
        # Setup
        existing_entry = NicknameEntry(
            user_id=12345,
            username="testuser",
            nickname="ExistingNickname",
            added_at="2024-01-01T00:00:00"
        )
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_entry
        
        with patch('src.handlers.add.storage_service', mock_storage):
            # Execute
            await handle_add_command(mock_message, **valid_context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.get_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.add_nickname.assert_not_called()
        
        # Verify warning message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "⚠️" in call_args
        assert "already have a nickname" in call_args
        assert "ExistingNickname" in call_args
        assert "/change" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_missing_parameter(self, mock_message, mock_storage):
        """Test adding nickname without providing nickname parameter."""
        # Setup context without command_args
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', mock_storage):
            # Execute
            await handle_add_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.has_nickname.assert_not_called()
        mock_storage.add_nickname.assert_not_called()
        
        # Verify prompt message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "📝" in call_args
        assert "Missing required parameter" in call_args
        assert "/add <your_nickname>" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_multiple_words(self, mock_message, mock_storage):
        """Test adding nickname with multiple words."""
        # Setup context with multi-word nickname
        context = {
            "command_args": ["Cool", "User", "123"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        mock_storage.has_nickname.return_value = False
        mock_storage.add_nickname.return_value = True
        
        with patch('src.handlers.add.storage_service', mock_storage):
            # Execute
            await handle_add_command(mock_message, **context)
        
        # Verify nickname was joined correctly
        mock_storage.add_nickname.assert_called_once_with(
            group_id=-100123456789,
            user_id=12345,
            username="testuser",
            nickname="Cool User 123"
        )
    
    @pytest.mark.asyncio
    async def test_add_nickname_invalid_nickname(self, mock_message, mock_storage, valid_context):
        """Test adding invalid nickname."""
        # Setup context with invalid nickname (too long)
        context = valid_context.copy()
        context["command_args"] = ["a" * 51]  # 51 characters, exceeds limit
        
        with patch('src.handlers.add.storage_service', mock_storage):
            # Execute
            await handle_add_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.has_nickname.assert_not_called()
        mock_storage.add_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "too long" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_missing_context(self, mock_message, mock_storage):
        """Test handling missing context data from middleware."""
        # Setup incomplete context
        context = {
            "command_args": ["TestNickname"],
            "user_id": None,  # Missing user_id
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', mock_storage):
            # Execute
            await handle_add_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.has_nickname.assert_not_called()
        mock_storage.add_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Invalid input" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_storage_unavailable(self, mock_message, valid_context):
        """Test handling when storage service is unavailable."""
        with patch('src.handlers.add.storage_service', None):
            # Execute
            await handle_add_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Service temporarily unavailable" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_storage_failure(self, mock_message, mock_storage, valid_context):
        """Test handling storage operation failure."""
        # Setup
        mock_storage.has_nickname.return_value = False
        mock_storage.add_nickname.return_value = False  # Simulate failure
        
        with patch('src.handlers.add.storage_service', mock_storage):
            # Execute
            await handle_add_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Unable to save your data" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_exception_handling(self, mock_message, mock_storage, valid_context):
        """Test exception handling in add command."""
        # Setup
        mock_storage.has_nickname.side_effect = Exception("Database error")
        
        with patch('src.handlers.add.storage_service', mock_storage):
            # Execute
            await handle_add_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_validation_error(self, mock_message, mock_storage):
        """Test add command with validation errors."""
        # Test with invalid nickname (too long)
        context = {
            "command_args": ["a" * 51],  # Too long
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', mock_storage):
            await handle_add_command(mock_message, **context)
        
        # Verify validation error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_suspicious_input(self, mock_message, mock_storage):
        """Test add command with suspicious input."""
        context = {
            "command_args": ["<script>alert('xss')</script>"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', mock_storage):
            await handle_add_command(mock_message, **context)
        
        # Verify validation error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_invalid_context(self, mock_message, mock_storage):
        """Test add command with invalid context data."""
        # Test with invalid user_id
        context = {
            "command_args": ["TestNickname"],
            "user_id": "invalid",  # Should be int
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.add.storage_service', mock_storage):
            await handle_add_command(mock_message, **context)
        
        # Verify validation error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_storage_check_error(self, mock_message, mock_storage, valid_context):
        """Test add command when storage check fails."""
        mock_storage.has_nickname.side_effect = Exception("Storage error")
        
        with patch('src.handlers.add.storage_service', mock_storage):
            await handle_add_command(mock_message, **valid_context)
        
        # Verify storage error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args
    
    @pytest.mark.asyncio
    async def test_add_nickname_storage_add_error(self, mock_message, mock_storage, valid_context):
        """Test add command when storage add operation fails."""
        mock_storage.has_nickname.return_value = False
        mock_storage.add_nickname.side_effect = Exception("Storage error")
        
        with patch('src.handlers.add.storage_service', mock_storage):
            await handle_add_command(mock_message, **valid_context)
        
        # Verify storage error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args


# Removed TestNicknameValidation class - validation is now tested in test_validation.py


class TestHandlerRegistration:
    """Test cases for handler registration."""
    
    def test_register_add_handler(self):
        """Test registering the add handler with dispatcher."""
        # Setup
        mock_dispatcher = MagicMock()
        mock_storage = MagicMock(spec=StorageService)
        
        # Execute
        register_add_handler(mock_dispatcher, mock_storage)
        
        # Verify dispatcher was called
        mock_dispatcher.include_router.assert_called_once()