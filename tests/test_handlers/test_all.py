"""
Unit tests for the all command handler.
Tests all scenarios for /all command functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType

from src.handlers.all import handle_all_command, register_all_handler
from src.storage import StorageService, NicknameEntry


class TestAllCommandHandler:
    """Test cases for the all command handler."""
    
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
            "group_id": -100123456789
        }
    
    @pytest.fixture
    def sample_nicknames(self):
        """Create sample nickname entries for testing."""
        return [
            NicknameEntry(
                user_id=12345,
                username="alice",
                nickname="Alice Wonder",
                added_at="2024-01-01T10:00:00"
            ),
            NicknameEntry(
                user_id=67890,
                username="bob",
                nickname="Bob Builder",
                added_at="2024-01-01T11:00:00"
            ),
            NicknameEntry(
                user_id=11111,
                username="charlie",
                nickname="Charlie Chocolate",
                added_at="2024-01-01T12:00:00"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_all_command_with_nicknames(self, mock_message, mock_storage, valid_context, sample_nicknames):
        """Test /all command when nicknames exist."""
        # Setup
        mock_storage.get_all_nicknames.return_value = sample_nicknames
        
        with patch('src.handlers.all.storage_service', mock_storage):
            # Execute
            await handle_all_command(mock_message, **valid_context)
        
        # Verify storage call
        mock_storage.get_all_nicknames.assert_called_once_with(-100123456789)
        
        # Verify response message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        response_text = call_args[1]["text"]  # keyword argument
        parse_mode = call_args[1]["parse_mode"]
        
        # Check message format and content
        assert "📋" in response_text
        assert "All Nicknames in This Group (3 nicknames)" in response_text
        assert "1. @alice - Alice Wonder" in response_text
        assert "2. @bob - Bob Builder" in response_text
        assert "3. @charlie - Charlie Chocolate" in response_text
        assert parse_mode == "Markdown"
    
    @pytest.mark.asyncio
    async def test_all_command_single_nickname(self, mock_message, mock_storage, valid_context):
        """Test /all command with single nickname (singular form)."""
        # Setup
        single_nickname = [
            NicknameEntry(
                user_id=12345,
                username="alice",
                nickname="Alice Wonder",
                added_at="2024-01-01T10:00:00"
            )
        ]
        mock_storage.get_all_nicknames.return_value = single_nickname
        
        with patch('src.handlers.all.storage_service', mock_storage):
            # Execute
            await handle_all_command(mock_message, **valid_context)
        
        # Verify response uses singular form
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        response_text = call_args[1]["text"]
        
        assert "All Nicknames in This Group (1 nickname)" in response_text
        assert "1. @alice - Alice Wonder" in response_text
    
    @pytest.mark.asyncio
    async def test_all_command_empty_list(self, mock_message, mock_storage, valid_context):
        """Test /all command when no nicknames exist."""
        # Setup
        mock_storage.get_all_nicknames.return_value = []
        
        with patch('src.handlers.all.storage_service', mock_storage):
            # Execute
            await handle_all_command(mock_message, **valid_context)
        
        # Verify storage call
        mock_storage.get_all_nicknames.assert_called_once_with(-100123456789)
        
        # Verify empty list message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "📝" in call_args
        assert "No nicknames added yet" in call_args
        assert "/add <your_nickname>" in call_args
    
    @pytest.mark.asyncio
    async def test_all_command_consistent_ordering(self, mock_message, mock_storage, valid_context):
        """Test that /all command maintains consistent ordering."""
        # Setup nicknames in specific order (storage should return them ordered by added_at)
        ordered_nicknames = [
            NicknameEntry(
                user_id=67890,
                username="bob",
                nickname="Bob Builder",
                added_at="2024-01-01T09:00:00"  # Earlier time
            ),
            NicknameEntry(
                user_id=12345,
                username="alice",
                nickname="Alice Wonder",
                added_at="2024-01-01T10:00:00"  # Later time
            )
        ]
        mock_storage.get_all_nicknames.return_value = ordered_nicknames
        
        with patch('src.handlers.all.storage_service', mock_storage):
            # Execute
            await handle_all_command(mock_message, **valid_context)
        
        # Verify response maintains order
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        response_text = call_args[1]["text"]
        
        # Bob should be #1 (added first), Alice should be #2 (added second)
        assert "1. @bob - Bob Builder" in response_text
        assert "2. @alice - Alice Wonder" in response_text
        
        # Verify order in the text
        bob_index = response_text.find("1. @bob")
        alice_index = response_text.find("2. @alice")
        assert bob_index < alice_index
    
    @pytest.mark.asyncio
    async def test_all_command_special_characters_in_nicknames(self, mock_message, mock_storage, valid_context):
        """Test /all command with nicknames containing special characters."""
        # Setup
        special_nicknames = [
            NicknameEntry(
                user_id=12345,
                username="user1",
                nickname="User@123",
                added_at="2024-01-01T10:00:00"
            ),
            NicknameEntry(
                user_id=67890,
                username="user2",
                nickname="Cool User #1",
                added_at="2024-01-01T11:00:00"
            )
        ]
        mock_storage.get_all_nicknames.return_value = special_nicknames
        
        with patch('src.handlers.all.storage_service', mock_storage):
            # Execute
            await handle_all_command(mock_message, **valid_context)
        
        # Verify special characters are preserved
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        response_text = call_args[1]["text"]
        
        assert "1. @user1 - User@123" in response_text
        assert "2. @user2 - Cool User #1" in response_text
    
    @pytest.mark.asyncio
    async def test_all_command_missing_group_id(self, mock_message, mock_storage):
        """Test handling missing group_id from middleware."""
        # Setup context without group_id
        context = {}
        
        with patch('src.handlers.all.storage_service', mock_storage):
            # Execute
            await handle_all_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.get_all_nicknames.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Unable to process command" in call_args
    
    @pytest.mark.asyncio
    async def test_all_command_storage_unavailable(self, mock_message, valid_context):
        """Test handling when storage service is unavailable."""
        with patch('src.handlers.all.storage_service', None):
            # Execute
            await handle_all_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Service temporarily unavailable" in call_args
    
    @pytest.mark.asyncio
    async def test_all_command_storage_exception(self, mock_message, mock_storage, valid_context):
        """Test exception handling in all command."""
        # Setup
        mock_storage.get_all_nicknames.side_effect = Exception("Database error")
        
        with patch('src.handlers.all.storage_service', mock_storage):
            # Execute
            await handle_all_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "unexpected error occurred" in call_args
    
    @pytest.mark.asyncio
    async def test_all_command_large_list(self, mock_message, mock_storage, valid_context):
        """Test /all command with a large number of nicknames."""
        # Setup large list of nicknames
        large_nickname_list = []
        for i in range(20):
            large_nickname_list.append(
                NicknameEntry(
                    user_id=10000 + i,
                    username=f"user{i}",
                    nickname=f"User Number {i}",
                    added_at=f"2024-01-01T{10 + i:02d}:00:00"
                )
            )
        
        mock_storage.get_all_nicknames.return_value = large_nickname_list
        
        with patch('src.handlers.all.storage_service', mock_storage):
            # Execute
            await handle_all_command(mock_message, **valid_context)
        
        # Verify response contains all entries
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        response_text = call_args[1]["text"]
        
        # Check that all 20 entries are present
        assert "All Nicknames in This Group (20 nicknames)" in response_text
        assert "1. @user0 - User Number 0" in response_text
        assert "20. @user19 - User Number 19" in response_text
        
        # Verify numbering is correct
        for i in range(20):
            expected_entry = f"{i + 1}. @user{i} - User Number {i}"
            assert expected_entry in response_text


class TestHandlerRegistration:
    """Test cases for handler registration."""
    
    def test_register_all_handler(self):
        """Test registering the all handler with dispatcher."""
        # Setup
        mock_dispatcher = MagicMock()
        mock_storage = MagicMock(spec=StorageService)
        
        # Execute
        register_all_handler(mock_dispatcher, mock_storage)
        
        # Verify dispatcher was called
        mock_dispatcher.include_router.assert_called_once()