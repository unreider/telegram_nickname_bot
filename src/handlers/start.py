"""
Start command handler for Telegram Nickname Bot.
Handles /start command with bot introduction and available commands.
"""

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

logger = logging.getLogger(__name__)

# Module-level router to satisfy tests and allow reuse
start_router = Router()

async def handle_start_command(message: Message, **kwargs) -> None:
    """
    Handle /start command with bot introduction and available commands.
    
    Requirements addressed:
    - 1.1: Respond with introduction message explaining bot purpose
    - 1.2: Suggest available commands to the user
    - 1.3: Only respond in the same group chat where command was issued
    
    Args:
        message: The incoming message with /start command
    """
    try:
        # Create introduction message with available commands
        intro_message = (
            "🤖 **Welcome to Nickname Bot!**\n\n"
            "I help you manage custom nicknames in your group chat. "
            "Here's what I can do:\n\n"
            "**Available Commands:**\n"
            "• `/start` - Show this introduction message\n"
            "• `/add <nickname>` - Add a nickname for yourself\n"
            "• `/all` - List all nicknames in this group\n"
            "• `/change <nickname>` - Change your existing nickname\n"
            "• `/remove` - Remove your nickname\n"
            "• `/help` - Show detailed help for all commands\n\n"
            "💡 **Tip:** All commands work only in group chats, and nicknames are specific to each group.\n\n"
            "Get started by adding your nickname with `/add <your_nickname>`!"
        )
        
        # Send response to the same chat where command was issued
        await message.answer(
            text=intro_message,
            parse_mode="Markdown"
        )
        
        logger.info(
            f"Start command handled successfully for user {message.from_user.id} "
            f"in chat {message.chat.id}"
        )
        
    except Exception as e:
        logger.error(f"Error handling start command: {e}")
        # Send a simple fallback message if markdown parsing fails
        fallback_message = (
            "Welcome to Nickname Bot!\n\n"
            "I help you manage custom nicknames in your group chat.\n\n"
            "Available commands:\n"
            "/start - Show this message\n"
            "/add <nickname> - Add a nickname\n"
            "/all - List all nicknames\n"
            "/change <nickname> - Change your nickname\n"
            "/remove - Remove your nickname\n"
            "/help - Show detailed help\n\n"
            "Get started with /add <your_nickname>!"
        )
        
        try:
            await message.answer(text=fallback_message)
        except Exception as fallback_error:
            logger.error(f"Failed to send fallback message: {fallback_error}")


# Bind handler to the module-level router
start_router.message(Command("start")) (handle_start_command)


def register_start_handler(dispatcher) -> None:
    """Register start command handler with dispatcher."""
    # Include the module-level router (used by tests)
    dispatcher.include_router(start_router)
    logger.info("Start command handler registered")