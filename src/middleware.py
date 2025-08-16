"""
Middleware for group chat validation and command preprocessing.
Ensures bot only works in group chats and validates commands.
"""

import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.enums import ChatType


logger = logging.getLogger(__name__)


class GroupChatMiddleware(BaseMiddleware):
    """
    Middleware to ensure bot only responds to commands in group chats.
    Validates chat type and preprocesses commands for group context.
    """
    
    def __init__(self):
        """Initialize the middleware."""
        super().__init__()
        self.allowed_chat_types = {ChatType.GROUP, ChatType.SUPERGROUP}
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process incoming updates and validate group chat requirement.
        
        Args:
            handler: Next handler in the chain
            event: Telegram event (Message, etc.)
            data: Handler data dictionary
            
        Returns:
            Handler result or None if validation fails
        """
        # Only process Message events
        if not isinstance(event, Message):
            return await handler(event, data)
        
        message: Message = event
        
        # Check if message is from a group chat
        if not self._is_group_chat(message):
            logger.info(
                f"Ignoring command from non-group chat: {message.chat.type} "
                f"(chat_id: {message.chat.id})"
            )
            # Send a polite message explaining the bot only works in groups
            await message.answer(
                "🤖 This bot only works in group chats. "
                "Please add me to a group to use nickname commands!"
            )
            return None
        
        # Add group validation data to handler context
        data["is_group_chat"] = True
        data["group_id"] = message.chat.id
        data["group_title"] = message.chat.title or "Unknown Group"
        
        # Log group activity for debugging
        logger.info(
            f"Processing command in group '{data['group_title']}' "
            f"(ID: {data['group_id']}) from user @{message.from_user.username or 'unknown'}"
        )
        
        # Continue to next handler
        return await handler(event, data)
    
    def _is_group_chat(self, message: Message) -> bool:
        """
        Check if the message is from a group chat.
        
        Args:
            message: Telegram message object
            
        Returns:
            True if message is from a group chat, False otherwise
        """
        return message.chat.type in self.allowed_chat_types


class CommandValidationMiddleware(BaseMiddleware):
    """
    Middleware for command preprocessing and validation.
    Handles command parsing and parameter validation.
    """
    
    def __init__(self):
        """Initialize the middleware."""
        super().__init__()
        self.bot_commands = {
            "/start", "/add", "/all", "/change", "/remove", "/help"
        }
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process and validate commands before handling.
        
        Args:
            handler: Next handler in the chain
            event: Telegram event (Message, etc.)
            data: Handler data dictionary
            
        Returns:
            Handler result or None if validation fails
        """
        # Only process Message events
        if not isinstance(event, Message):
            return await handler(event, data)
        
        message: Message = event
        
        # Only process messages that start with commands
        if not message.text or not message.text.startswith('/'):
            return await handler(event, data)
        
        # Parse command and arguments
        command_parts = message.text.split()
        command = command_parts[0].lower()
        
        # Remove bot username from command if present (e.g., /start@botname -> /start)
        if '@' in command:
            command = command.split('@')[0]
        
        # Check if it's a recognized bot command
        if command not in self.bot_commands:
            # Not our command, let other handlers process it
            return await handler(event, data)
        
        # Add command parsing data to handler context
        data["command"] = command
        data["command_args"] = command_parts[1:] if len(command_parts) > 1 else []
        data["raw_command_text"] = message.text
        
        # Validate user information
        if not message.from_user:
            logger.warning("Received command from unknown user")
            await message.answer("❌ Unable to identify user. Please try again.")
            return None
        
        # Add user data to context
        data["user_id"] = message.from_user.id
        data["username"] = message.from_user.username or f"user_{message.from_user.id}"
        data["user_full_name"] = message.from_user.full_name
        
        logger.info(
            f"Validated command '{command}' with {len(data['command_args'])} arguments "
            f"from user @{data['username']}"
        )
        
        # Continue to command handler
        return await handler(event, data)


def setup_middleware(dispatcher) -> None:
    """
    Register middleware with the dispatcher.
    
    Args:
        dispatcher: Aiogram dispatcher instance
    """
    # Register group chat validation middleware first
    dispatcher.message.middleware(GroupChatMiddleware())
    
    # Register command validation middleware second
    dispatcher.message.middleware(CommandValidationMiddleware())
    
    logger.info("Middleware registered successfully")