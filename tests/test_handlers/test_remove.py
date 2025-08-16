"""
Unit tests for the remove command handler.
Tests all scenarios for /remove command functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType

from src.handlers.remove import handle_remove_command, register_remove_handler
from src.storage import StorageService, NicknameEntry


class TestRemoveCommandHandler:
    """Test cases for the remove command handler."""
    
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
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
    
    @pytest.fixture
    def existing_nickname_entry(self):
        """Create an existing nickname entry for testing."""
        return NicknameEntry(
            user_id=12345,
            username="testuser",
            nickname="TestNickname",
            added_at="2024-01-01T00:00:00"
        )
    
    @pytest.mark.asyncio
    async def test_remove_nickname_success(self, mock_message, mock_storage, valid_context, existing_nickname_entry):
        """Test successful nickname removal."""
        # Setup
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_nickname_entry
        mock_storage.remove_nickname.return_value = True
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **valid_context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.get_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.remove_nickname.assert_called_once_with(-100123456789, 12345)
        
        # Verify success message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "✅" in call_args
        assert "Nickname removed successfully" in call_args
        assert "TestNickname" in call_args
        assert "@testuser" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_no_existing_nickname(self, mock_message, mock_storage, valid_context):
        """Test removing nickname when user has no nickname."""
        # Setup
        mock_storage.has_nickname.return_value = False
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **valid_context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.get_nickname.assert_not_called()
        mock_storage.remove_nickname.assert_not_called()
        
        # Verify warning message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "⚠️" in call_args
        assert "don't have a nickname set" in call_args
        assert "/add" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_missing_context(self, mock_message, mock_storage):
        """Test handling missing context data from middleware."""
        # Setup incomplete context
        context = {
            "user_id": None,  # Missing user_id
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.has_nickname.assert_not_called()
        mock_storage.get_nickname.assert_not_called()
        mock_storage.remove_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Unable to process command" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_storage_unavailable(self, mock_message, valid_context):
        """Test handling when storage service is unavailable."""
        with patch('src.handlers.remove.storage_service', None):
            # Execute
            await handle_remove_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Service temporarily unavailable" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_get_nickname_returns_none(self, mock_message, mock_storage, valid_context):
        """Test handling when get_nickname returns None despite has_nickname being True."""
        # Setup - this is an edge case that shouldn't normally happen
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = None
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **valid_context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.get_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.remove_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Unable to find your nickname" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_storage_failure(self, mock_message, mock_storage, valid_context, existing_nickname_entry):
        """Test handling storage operation failure."""
        # Setup
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_nickname_entry
        mock_storage.remove_nickname.return_value = False  # Simulate failure
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **valid_context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.get_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.remove_nickname.assert_called_once_with(-100123456789, 12345)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Failed to remove nickname" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_exception_handling(self, mock_message, mock_storage, valid_context):
        """Test exception handling in remove command."""
        # Setup
        mock_storage.has_nickname.side_effect = Exception("Database error")
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "unexpected error occurred" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_missing_user_id(self, mock_message, mock_storage):
        """Test handling missing user_id in context."""
        context = {
            "user_id": None,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.has_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args
        assert "Unable to process command" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_missing_username(self, mock_message, mock_storage):
        """Test handling missing username in context."""
        context = {
            "user_id": 12345,
            "username": None,
            "group_id": -100123456789
        }
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.has_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args
        assert "Unable to process command" in call_args
    
    @pytest.mark.asyncio
    async def test_remove_nickname_missing_group_id(self, mock_message, mock_storage):
        """Test handling missing group_id in context."""
        context = {
            "user_id": 12345,
            "username": "testuser",
            "group_id": None
        }
        
        with patch('src.handlers.remove.storage_service', mock_storage):
            # Execute
            await handle_remove_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.has_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "❌" in call_args
        assert "Unable to process command" in call_args


class TestHandlerRegistration:
    """Test cases for handler registration."""
    
    def test_register_remove_handler(self):
        """Test registering the remove handler with dispatcher."""
        # Setup
        mock_dispatcher = MagicMock()
        mock_storage = MagicMock(spec=StorageService)
        
        # Execute
        register_remove_handler(mock_dispatcher, mock_storage)
        
        # Verify dispatcher was called
        mock_dispatcher.include_router.assert_called_once()
        
        # Verify storage service was set (indirectly by checking no exceptions)
        # The actual storage service setting is tested through the command handler tests
        assert True  # If we get here without exceptions, registration worked