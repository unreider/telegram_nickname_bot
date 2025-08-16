"""
Unit tests for help command handler.
Tests comprehensive command list with descriptions and syntax.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import Dispatcher
from aiogram.types import Message, User, Chat

from src.handlers.help import handle_help_command, register_help_handler, help_router


class TestHelpCommandHandler:
    """Test cases for /help command handler."""
    
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
    async def test_help_command_success(self, mock_message):
        """Test successful /help command handling."""
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Verify message was sent
        mock_message.answer.assert_called_once()
        
        # Get the call arguments
        call_args = mock_message.answer.call_args
        sent_text = call_args[1]['text']  # keyword argument 'text'
        parse_mode = call_args[1]['parse_mode']  # keyword argument 'parse_mode'
        
        # Verify message content
        assert "Nickname Bot - Command Help" in sent_text
        assert "I help you manage custom nicknames" in sent_text
        assert "Available Commands:" in sent_text
        assert parse_mode == "Markdown"
    
    @pytest.mark.asyncio
    async def test_help_command_all_commands_listed(self, mock_message):
        """Test that all commands are listed with descriptions."""
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Get the sent message
        call_args = mock_message.answer.call_args
        sent_text = call_args[1]['text']
        
        # Requirement 6.1: All available commands with descriptions
        required_commands = [
            ("/start", "Show bot introduction"),
            ("/add", "Add a nickname for yourself"),
            ("/all", "List all nicknames"),
            ("/change", "Change your existing nickname"),
            ("/remove", "Remove your nickname"),
            ("/help", "Show this detailed help message")
        ]
        
        for command, description_part in required_commands:
            assert command in sent_text, f"Command {command} should be listed"
            assert description_part.lower() in sent_text.lower(), f"Description for {command} should be included"
    
    @pytest.mark.asyncio
    async def test_help_command_syntax_and_purpose(self, mock_message):
        """Test that command syntax and purpose are included."""
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Get the sent message
        call_args = mock_message.answer.call_args
        sent_text = call_args[1]['text']
        
        # Requirement 6.2: Include command syntax and purpose
        syntax_examples = [
            "Syntax:",
            "Purpose:",
            "/add YourNickname",
            "/change NewNickname",
            "Example:"
        ]
        
        for syntax_element in syntax_examples:
            assert syntax_element in sent_text, f"Syntax element '{syntax_element}' should be included"
        
        # Check that commands with parameters show proper syntax
        assert "/add <nickname>" in sent_text or "/add YourNickname" in sent_text
        assert "/change <nickname>" in sent_text or "/change NewNickname" in sent_text
    
    @pytest.mark.asyncio
    async def test_help_command_clear_and_understandable(self, mock_message):
        """Test that help response is clear and easy to understand."""
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Get the sent message
        call_args = mock_message.answer.call_args
        sent_text = call_args[1]['text']
        
        # Requirement 6.3: Response is clear and easy to understand
        clarity_indicators = [
            "Purpose:",
            "Syntax:",
            "Description:",
            "Example:",
            "Important Notes:",
            "Need Help?"
        ]
        
        for indicator in clarity_indicators:
            assert indicator in sent_text, f"Clarity indicator '{indicator}' should be present"
        
        # Should include helpful notes about usage
        assert "group chats" in sent_text.lower()
        assert "specific to each group" in sent_text.lower()
    
    @pytest.mark.asyncio
    async def test_help_command_markdown_fallback(self, mock_message):
        """Test fallback to plain text when markdown parsing fails."""
        # Mock answer to raise exception on first call (markdown), succeed on second
        mock_message.answer.side_effect = [Exception("Markdown parse error"), None]
        
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Verify two calls were made (markdown attempt + fallback)
        assert mock_message.answer.call_count == 2
        
        # Check first call was with markdown
        first_call = mock_message.answer.call_args_list[0]
        assert first_call[1]['parse_mode'] == "Markdown"
        
        # Check second call was fallback without parse_mode
        second_call = mock_message.answer.call_args_list[1]
        fallback_text = second_call[1]['text']
        assert "parse_mode" not in second_call[1]
        assert "Nickname Bot - Command Help" in fallback_text
        assert "/start" in fallback_text
        assert "/add <nickname>" in fallback_text
    
    @pytest.mark.asyncio
    async def test_help_command_complete_failure(self, mock_message, caplog):
        """Test handling when both markdown and fallback messages fail."""
        # Mock answer to always raise exception
        mock_message.answer.side_effect = Exception("Network error")
        
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Verify both attempts were made
        assert mock_message.answer.call_count == 2
        
        # Verify error was logged
        assert "Failed to send fallback message" in caplog.text
    
    @pytest.mark.asyncio
    async def test_help_command_logs_success(self, mock_message, caplog):
        """Test that successful command execution is logged."""
        # Set logging level to capture INFO logs
        caplog.set_level("INFO")
        
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Verify success was logged with user and chat info
        assert "Help command handled successfully" in caplog.text
        assert "user 12345" in caplog.text
        assert "chat -67890" in caplog.text
    
    def test_register_help_handler(self):
        """Test that help handler is properly registered with dispatcher."""
        # Create mock dispatcher
        mock_dispatcher = MagicMock(spec=Dispatcher)
        
        # Register handler
        register_help_handler(mock_dispatcher)
        
        # Verify router was included
        mock_dispatcher.include_router.assert_called_once_with(help_router)
    
    @pytest.mark.asyncio
    async def test_help_command_comprehensive_content(self, mock_message):
        """Test that help command provides comprehensive information."""
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Get the sent message
        call_args = mock_message.answer.call_args
        sent_text = call_args[1]['text']
        
        # Should include examples for commands that need parameters
        assert "Example:" in sent_text
        assert "CoolUser123" in sent_text or "YourNickname" in sent_text
        assert "SuperUser456" in sent_text or "NewNickname" in sent_text
        
        # Should include important usage notes
        important_notes = [
            "only in group chats",
            "specific to each group",
            "only manage your own nickname"
        ]
        
        for note in important_notes:
            assert note.lower() in sent_text.lower(), f"Important note '{note}' should be included"
    
    @pytest.mark.asyncio
    async def test_help_command_fallback_content(self, mock_message):
        """Test that fallback message contains essential information."""
        # Mock answer to fail on markdown, succeed on fallback
        mock_message.answer.side_effect = [Exception("Markdown error"), None]
        
        # Execute the handler
        await handle_help_command(mock_message)
        
        # Get the fallback message
        second_call = mock_message.answer.call_args_list[1]
        fallback_text = second_call[1]['text']
        
        # Fallback should still contain all essential commands
        essential_commands = ["/start", "/add", "/all", "/change", "/remove", "/help"]
        for command in essential_commands:
            assert command in fallback_text, f"Command {command} should be in fallback"
        
        # Should include basic examples and notes
        assert "Example:" in fallback_text
        assert "Important Notes:" in fallback_text
        assert "group chats" in fallback_text


class TestHelpHandlerIntegration:
    """Integration tests for help handler registration and routing."""
    
    def test_help_router_configuration(self):
        """Test that help router is properly configured."""
        # Verify router exists and is configured
        assert help_router is not None
        assert hasattr(help_router, 'message')
    
    @pytest.mark.asyncio
    async def test_handler_registration_with_real_dispatcher(self):
        """Test handler registration with actual Dispatcher instance."""
        # Create real dispatcher
        dispatcher = Dispatcher()
        
        # Register handler
        register_help_handler(dispatcher)
        
        # Verify router was added (check internal structure)
        assert len(dispatcher.sub_routers) > 0
        assert help_router in dispatcher.sub_routers
    
    @pytest.mark.asyncio
    async def test_help_command_requirements_coverage(self):
        """Test that all requirements are properly addressed."""
        # Create a mock message
        message = MagicMock(spec=Message)
        message.from_user = MagicMock(spec=User)
        message.from_user.id = 12345
        message.chat = MagicMock(spec=Chat)
        message.chat.id = -67890
        message.answer = AsyncMock()
        
        # Execute the handler
        await handle_help_command(message)
        
        # Get the sent message
        call_args = message.answer.call_args
        sent_text = call_args[1]['text']
        
        # Requirement 6.1: List all available commands with descriptions
        commands_with_descriptions = [
            ("/start", "introduction"),
            ("/add", "Add a nickname"),
            ("/all", "List all nicknames"),
            ("/change", "Change your existing"),
            ("/remove", "Remove your nickname"),
            ("/help", "help message")
        ]
        
        for command, desc_part in commands_with_descriptions:
            assert command in sent_text
            assert desc_part.lower() in sent_text.lower()
        
        # Requirement 6.2: Include command syntax and purpose
        assert "Syntax:" in sent_text
        assert "Purpose:" in sent_text
        
        # Requirement 6.3: Clear and easy to understand
        assert "Description:" in sent_text
        assert "Important Notes:" in sent_text