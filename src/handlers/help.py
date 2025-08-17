"""
Help command handler for Telegram Nickname Bot.
Handles /help command with comprehensive command list and descriptions.
"""

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

logger = logging.getLogger(__name__)

# Module-level router to satisfy tests and allow reuse
help_router = Router()

async def handle_help_command(message: Message, **kwargs) -> None:
    """
    Handle /help command with comprehensive command list and descriptions.
    
    Requirements addressed:
    - 6.1: List all available commands with their descriptions
    - 6.2: Include command syntax and purpose for each command
    - 6.3: Response is clear and easy to understand
    
    Args:
        message: The incoming message with /help command
    """
    try:
        # Create comprehensive help message with all commands
        help_message = (
            "🤖 **Nickname Bot - Command Help**\n\n"
            "I help you manage custom nicknames in your group chat. "
            "Here are all available commands with detailed descriptions:\n\n"
            
            "**📋 Available Commands:**\n\n"
            
            "🚀 **`/start`**\n"
            "   • **Purpose:** Show bot introduction and overview\n"
            "   • **Syntax:** `/start`\n"
            "   • **Description:** Displays welcome message and basic command list\n\n"
            
            "➕ **`/add <nickname>`**\n"
            "   • **Purpose:** Add a nickname for yourself\n"
            "   • **Syntax:** `/add YourNickname`\n"
            "   • **Description:** Sets a custom nickname that others can see when listing all nicknames\n"
            "   • **Example:** `/add CoolUser123`\n\n"
            
            "📝 **`/all`**\n"
            "   • **Purpose:** List all nicknames in this group\n"
            "   • **Syntax:** `/all`\n"
            "   • **Description:** Shows all group members who have set nicknames in numbered format\n\n"
            
            "✏️ **`/change <nickname>`**\n"
            "   • **Purpose:** Change your existing nickname\n"
            "   • **Syntax:** `/change NewNickname`\n"
            "   • **Description:** Updates your current nickname to a new one (you must have a nickname already)\n"
            "   • **Example:** `/change SuperUser456`\n\n"
            
            "🗑️ **`/remove`**\n"
            "   • **Purpose:** Remove your nickname\n"
            "   • **Syntax:** `/remove`\n"
            "   • **Description:** Deletes your nickname from the group's list completely\n\n"
            
            "❓ **`/help`**\n"
            "   • **Purpose:** Show this detailed help message\n"
            "   • **Syntax:** `/help`\n"
            "   • **Description:** Displays comprehensive information about all available commands\n\n"
            
            "**💡 Important Notes:**\n"
            "• All commands work only in group chats\n"
            "• Nicknames are specific to each group\n"
            "• You can only manage your own nickname\n"
            "• Nicknames are displayed alongside your Telegram username\n\n"
            
            "**🔧 Need Help?**\n"
            "If you encounter any issues, try using `/start` to see the basic overview, "
            "or contact your group administrator."
        )
        
        # Send response to the same chat where command was issued
        await message.answer(
            text=help_message,
            parse_mode="Markdown"
        )
        
        logger.info(
            f"Help command handled successfully for user {message.from_user.id} "
            f"in chat {message.chat.id}"
        )
        
    except Exception as e:
        logger.error(f"Error handling help command: {e}")
        # Send a simple fallback message if markdown parsing fails
        fallback_message = (
            "Nickname Bot - Command Help\n\n"
            "Available Commands:\n\n"
            "/start - Show bot introduction\n"
            "/add <nickname> - Add a nickname for yourself\n"
            "Example: /add CoolUser123\n\n"
            "/all - List all nicknames in this group\n\n"
            "/change <nickname> - Change your existing nickname\n"
            "Example: /change SuperUser456\n\n"
            "/remove - Remove your nickname\n\n"
            "/help - Show this help message\n\n"
            "Important Notes:\n"
            "- All commands work only in group chats\n"
            "- Nicknames are specific to each group\n"
            "- You can only manage your own nickname\n\n"
            "Need help? Contact your group administrator."
        )
        
        try:
            await message.answer(text=fallback_message)
        except Exception as fallback_error:
            logger.error(f"Failed to send fallback message: {fallback_error}")


# Bind handler to the module-level router
help_router.message(Command("help")) (handle_help_command)


def register_help_handler(dispatcher) -> None:
    """Register help command handler with dispatcher."""
    # Include the module-level router (used by tests)
    dispatcher.include_router(help_router)
    logger.info("Help command handler registered")