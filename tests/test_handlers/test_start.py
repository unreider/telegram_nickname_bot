"""
Unit tests for start command handler.
Tests bot introduction message and command listing functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, Chat

from src.handlers.start import handle_start_command, register_start_handler, start_router


class TestStartCommandHandler:
    """Test cases for /start command handler."""
    
    @pytest.fixture
    def mock_message(self):
        """Create a mock message for testing."""
        message = MagicMock(spec=Message)
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 12345
        message.from_user.username = "testuser"
        message.chat = MagicMock(spec=Chat)
        message.chat.id = -67890  # Negative ID indicates group chat
        message.chat.type = "group"
        message.answer = AsyncMock()
        return message
    
    @pytest.mark.asyncio
    async def test_start_command_success(self, mock_message):
        """Test successful /start command handling."""
        # Execute the handler
        await handle_start_command(mock_message)
        
        # Verify message was sent
        mock_message.answer.assert_called_once()
        
        # Get the call arguments
        call_args = mock_message.answer.call_args
        sent_text = call_args[1]['text']  # keyword argument 'text'
        parse_mode = call_args[1]['parse_mode']  # keyword argument 'parse_mode'
        
        # Verify message content
        assert "Welcome to Nickname Bot!" in sent_text
        assert "I help you manage custom nicknames" in sent_text
        assert "Available Commands:" in sent_text
        assert "/start" in sent_text
        assert "/add <nickname>" in sent_text
        assert "/all" in sent_text
        assert "/change <nickname>" in sent_text
        assert "/remove" in sent_text
        assert "/help" in sent_text
        assert "Get started by adding your nickname" in sent_text
        assert parse_mode == "Markdown"
    
    @pytest.mark.asyncio
    async def test_start_command_markdown_fallback(self, mock_message):
        """Test fallback to plain text when markdown parsing fails."""
        # Mock answer to raise exception on first call (markdown), succeed on second
        mock_message.answer.side_effect = [Exception("Markdown parse error"), None]
        
        # Execute the handler
        await handle_start_command(mock_message)
        
        # Verify two calls were made (markdown attempt + fallback)
        assert mock_message.answer.call_count == 2
        
        # Check first call was with markdown
        first_call = mock_message.answer.call_args_list[0]
        assert first_call[1]['parse_mode'] == "Markdown"
        
        # Check second call was fallback without parse_mode
        second_call = mock_message.answer.call_args_list[1]
        fallback_text = second_call[1]['text']
        assert "parse_mode" not in second_call[1]
        assert "Welcome to Nickname Bot!" in fallback_text
        assert "/start" in fallback_text
        assert "/add <nickname>" in fallback_text
    
    @pytest.mark.asyncio
    async def test_start_command_complete_failure(self, mock_message, caplog):
        """Test handling when both markdown and fallback messages fail."""
        # Mock answer to always raise exception
        mock_message.answer.side_effect = Exception("Network error")
        
        # Execute the handler
        await handle_start_command(mock_message)
        
        # Verify both attempts were made
        assert mock_message.answer.call_count == 2
        
        # Verify error was logged
        assert "Failed to send fallback message" in caplog.text
    
    @pytest.mark.asyncio
    async def test_start_command_logs_success(self, mock_message, caplog):
        """Test that successful command execution is logged."""
        # Set logging level to capture INFO logs
        caplog.set_level("INFO")
        
        # Execute the handler
        await handle_start_command(mock_message)
        
        # Verify success was logged with user and chat info
        assert "Start command handled successfully" in caplog.text
        assert "user 12345" in caplog.text
        assert "chat -67890" in caplog.text
    
    def test_register_start_handler(self):
        """Test that start handler is properly registered with dispatcher."""
        # Create mock dispatcher
        mock_dispatcher = MagicMock(spec=Dispatcher)
        
        # Register handler
        register_start_handler(mock_dispatcher)
        
        # Verify router was included
        mock_dispatcher.include_router.assert_called_once_with(start_router)
    
    @pytest.mark.asyncio
    async def test_start_command_message_content_requirements(self, mock_message):
        """Test that start command message meets all requirements."""
        # Execute the handler
        await handle_start_command(mock_message)
        
        # Get the sent message
        call_args = mock_message.answer.call_args
        sent_text = call_args[1]['text']
        
        # Requirement 1.1: Bot explains its purpose
        assert any(phrase in sent_text.lower() for phrase in [
            "nickname", "manage", "custom", "group chat"
        ]), "Message should explain bot purpose"
        
        # Requirement 1.2: Available commands are suggested
        required_commands = ["/start", "/add", "/all", "/change", "/remove", "/help"]
        for command in required_commands:
            assert command in sent_text, f"Command {command} should be listed"
        
        # Requirement 1.3: Response is sent to same chat (verified by mock usage)
        mock_message.answer.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_command_user_guidance(self, mock_message):
        """Test that start command provides clear user guidance."""
        # Execute the handler
        await handle_start_command(mock_message)
        
        # Get the sent message
        call_args = mock_message.answer.call_args
        sent_text = call_args[1]['text']
        
        # Should provide guidance on how to get started
        assert any(phrase in sent_text.lower() for phrase in [
            "get started", "add your nickname", "tip"
        ]), "Message should provide user guidance"
        
        # Should mention group-specific functionality
        assert "group" in sent_text.lower(), "Message should mention group functionality"


class TestStartHandlerIntegration:
    """Integration tests for start handler registration and routing."""
    
    def test_start_router_configuration(self):
        """Test that start router is properly configured."""
        # Verify router exists and is configured
        assert start_router is not None
        assert hasattr(start_router, 'message')
    
    @pytest.mark.asyncio
    async def test_handler_registration_with_real_dispatcher(self):
        """Test handler registration with actual Dispatcher instance."""
        # Create real dispatcher
        dispatcher = Dispatcher()
        
        # Register handler
        register_start_handler(dispatcher)
        
        # Verify router was added (check internal structure)
        assert len(dispatcher.sub_routers) > 0
        assert start_router in dispatcher.sub_routers