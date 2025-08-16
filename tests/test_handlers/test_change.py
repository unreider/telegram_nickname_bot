"""
Unit tests for the change command handler.
Tests all scenarios for /change command functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from aiogram.enums import ChatType

from src.handlers.change import handle_change_command, register_change_handler
from src.validation import validate_nickname
from src.storage import StorageService, NicknameEntry


class TestChangeCommandHandler:
    """Test cases for the change command handler."""
    
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
            "command_args": ["NewNickname"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
    
    @pytest.fixture
    def existing_entry(self):
        """Create an existing nickname entry."""
        return NicknameEntry(
            user_id=12345,
            username="testuser",
            nickname="OldNickname",
            added_at="2024-01-01T00:00:00"
        )
    
    @pytest.mark.asyncio
    async def test_change_nickname_success(self, mock_message, mock_storage, valid_context, existing_entry):
        """Test successful nickname change."""
        # Setup
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_entry
        mock_storage.update_nickname.return_value = True
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **valid_context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.get_nickname.assert_called_with(-100123456789, 12345)
        mock_storage.update_nickname.assert_called_once_with(
            group_id=-100123456789,
            user_id=12345,
            new_nickname="NewNickname"
        )
        
        # Verify success message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "✅" in call_args
        assert "Nickname changed successfully" in call_args
        assert "OldNickname" in call_args
        assert "NewNickname" in call_args
    
    @pytest.mark.asyncio
    async def test_change_nickname_no_existing_nickname(self, mock_message, mock_storage, valid_context):
        """Test changing nickname when user has no existing nickname."""
        # Setup
        mock_storage.has_nickname.return_value = False
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **valid_context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.get_nickname.assert_not_called()
        mock_storage.update_nickname.assert_not_called()
        
        # Verify warning message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "⚠️" in call_args
        assert "don't have a nickname set" in call_args
        assert "/add" in call_args
    
    @pytest.mark.asyncio
    async def test_change_nickname_missing_parameter(self, mock_message, mock_storage, existing_entry):
        """Test changing nickname without providing new nickname parameter."""
        # Setup context without command_args
        context = {
            "command_args": [],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_entry
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **context)
        
        # Verify storage calls
        mock_storage.has_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.get_nickname.assert_called_once_with(-100123456789, 12345)
        mock_storage.update_nickname.assert_not_called()
        
        # Verify prompt message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "📝" in call_args
        assert "Please provide a new nickname" in call_args
        assert "/change <new_nickname>" in call_args
        assert "OldNickname" in call_args  # Shows current nickname
    
    @pytest.mark.asyncio
    async def test_change_nickname_multiple_words(self, mock_message, mock_storage, existing_entry):
        """Test changing nickname with multiple words."""
        # Setup context with multi-word nickname
        context = {
            "command_args": ["New", "Cool", "User"],
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_entry
        mock_storage.update_nickname.return_value = True
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **context)
        
        # Verify nickname was joined correctly
        mock_storage.update_nickname.assert_called_once_with(
            group_id=-100123456789,
            user_id=12345,
            new_nickname="New Cool User"
        )
    
    @pytest.mark.asyncio
    async def test_change_nickname_same_as_current(self, mock_message, mock_storage, existing_entry):
        """Test changing nickname to the same value as current."""
        # Setup context with same nickname as current
        context = {
            "command_args": ["OldNickname"],  # Same as existing
            "user_id": 12345,
            "username": "testuser",
            "group_id": -100123456789
        }
        
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_entry
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **context)
        
        # Verify no update was attempted
        mock_storage.update_nickname.assert_not_called()
        
        # Verify message about same nickname
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "🤔" in call_args
        assert "already set to" in call_args
        assert "OldNickname" in call_args
    
    @pytest.mark.asyncio
    async def test_change_nickname_invalid_nickname(self, mock_message, mock_storage, existing_entry, valid_context):
        """Test changing to invalid nickname."""
        # Setup context with invalid nickname (too long)
        context = valid_context.copy()
        context["command_args"] = ["a" * 51]  # 51 characters, exceeds limit
        
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_entry
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **context)
        
        # Verify no update was attempted
        mock_storage.update_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "too long" in call_args
    
    @pytest.mark.asyncio
    async def test_change_nickname_missing_context(self, mock_message, mock_storage):
        """Test handling missing context data from middleware."""
        # Setup incomplete context
        context = {
            "command_args": ["NewNickname"],
            "user_id": None,  # Missing user_id
            "username": "testuser",
            "group_id": -100123456789
        }
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **context)
        
        # Verify no storage calls
        mock_storage.has_nickname.assert_not_called()
        mock_storage.update_nickname.assert_not_called()
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Unable to process command" in call_args
    
    @pytest.mark.asyncio
    async def test_change_nickname_storage_unavailable(self, mock_message, valid_context):
        """Test handling when storage service is unavailable."""
        with patch('src.handlers.change.storage_service', None):
            # Execute
            await handle_change_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Service temporarily unavailable" in call_args
    
    @pytest.mark.asyncio
    async def test_change_nickname_storage_failure(self, mock_message, mock_storage, valid_context, existing_entry):
        """Test handling storage operation failure."""
        # Setup
        mock_storage.has_nickname.return_value = True
        mock_storage.get_nickname.return_value = existing_entry
        mock_storage.update_nickname.return_value = False  # Simulate failure
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "Failed to change nickname" in call_args
    
    @pytest.mark.asyncio
    async def test_change_nickname_exception_handling(self, mock_message, mock_storage, valid_context):
        """Test exception handling in change command."""
        # Setup
        mock_storage.has_nickname.side_effect = Exception("Database error")
        
        with patch('src.handlers.change.storage_service', mock_storage):
            # Execute
            await handle_change_command(mock_message, **valid_context)
        
        # Verify error message
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]  # First positional argument
        assert "❌" in call_args
        assert "unexpected error occurred" in call_args


class TestNicknameValidation:
    """Test cases for nickname validation function."""
    
    def test_validate_nickname_valid(self):
        """Test validation of valid nicknames."""
        valid_nicknames = [
            "TestUser",
            "Cool User 123",
            "user_name",
            "User-Name",
            "User.Name",
            "User@123",
            "User#Tag",
            "User$Money",
            "User%Percent",
            "User^Power",
            "User&More",
            "User*Star",
            "User(Paren)",
            "User+Plus",
            "User=Equal",
            "User[Bracket]",
            "User{Brace}",
            "User|Pipe",
            "User;Semi",
            "User:Colon",
            "User,Comma",
            "User<Less>",
            "User?Question",
            "User~Tilde",
            "User`Backtick",
            "a",  # Minimum length
            "a" * 50  # Maximum length
        ]
        
        for nickname in valid_nicknames:
            is_valid, error_msg = validate_nickname(nickname)
            result = error_msg or ""
            assert result == "", f"Expected '{nickname}' to be valid, got: {result}"
    
    def test_validate_nickname_invalid_empty(self):
        """Test validation of empty nicknames."""
        invalid_nicknames = ["", "   ", "\t", "\n"]
        
        for nickname in invalid_nicknames:
            is_valid, error_msg = validate_nickname(nickname)
            result = error_msg or ""
            assert "cannot be empty" in result
    
    def test_validate_nickname_invalid_too_long(self):
        """Test validation of too long nicknames."""
        long_nickname = "a" * 51  # 51 characters
        is_valid, error_msg = validate_nickname(long_nickname)
        result = error_msg or ""
        assert "too long" in result
    
    def test_validate_nickname_invalid_characters(self):
        """Test validation of nicknames with invalid characters."""
        # Test with some potentially problematic characters
        invalid_nicknames = [
            "User\nNewline",
            "User\tTab",
            "User\rCarriageReturn"
        ]
        
        for nickname in invalid_nicknames:
            is_valid, error_msg = validate_nickname(nickname)
            result = error_msg or ""
            assert "invalid characters" in result
    
    def test_validate_nickname_invalid_whitespace(self):
        """Test validation of nicknames with invalid whitespace."""
        invalid_nicknames = [
            "User  Double",  # Double space
            " StartSpace",   # Leading space
            "EndSpace ",     # Trailing space
            "  BothSpaces  " # Both leading and trailing
        ]
        
        for nickname in invalid_nicknames:
            is_valid, error_msg = validate_nickname(nickname)
            result = error_msg or ""
            assert result != "", f"Expected '{nickname}' to be invalid"


class TestHandlerRegistration:
    """Test cases for handler registration."""
    
    def test_register_change_handler(self):
        """Test registering the change handler with dispatcher."""
        # Setup
        mock_dispatcher = MagicMock()
        mock_storage = MagicMock(spec=StorageService)
        
        # Execute
        register_change_handler(mock_dispatcher, mock_storage)
        
        # Verify dispatcher was called
        mock_dispatcher.include_router.assert_called_once()