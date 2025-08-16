"""
All command handler for Telegram Nickname Bot.
Handles /all command for listing all nicknames in the group.
"""

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..storage import StorageService

logger = logging.getLogger(__name__)

# Initialize storage service (will be injected via dependency)
storage_service: StorageService = None


def set_storage_service(service: StorageService) -> None:
    """Set the storage service instance for the handler."""
    global storage_service
    storage_service = service


async def handle_all_command(message: Message, **kwargs) -> None:
    """
    Handle /all command for listing all nicknames in the group.
    
    Requirements addressed:
    - 3.1: List all nicknames in format: [order-number]. [telegram-username] - [user's-specified-nickname]
    - 3.2: Inform users when no nicknames exist
    - 3.3: Order entries consistently (by addition order)
    
    Args:
        message: The incoming message with /all command
        **kwargs: Additional context from middleware (group_id)
    """
    try:
        # Get context data from middleware
        group_id = kwargs.get("group_id")
        
        # Validate that we have required context
        if not group_id:
            logger.error("Missing group_id from middleware")
            await message.answer("❌ Unable to process command. Please try again.")
            return
        
        # Check if storage service is available
        if not storage_service:
            logger.error("Storage service not initialized")
            await message.answer("❌ Service temporarily unavailable. Please try again later.")
            return
        
        # Get all nicknames for this group
        nicknames = storage_service.get_all_nicknames(group_id)
        
        # Handle empty nickname list scenario
        if not nicknames:
            await message.answer(
                "📝 **No nicknames added yet!**\n\n"
                "Be the first to add your nickname with `/add <your_nickname>`!\n\n"
                "💡 **Tip:** Nicknames help others in the group know what to call you."
            )
            return
        
        # Format nickname list with consistent ordering
        nickname_list = []
        for index, entry in enumerate(nicknames, 1):
            # Format: [order-number]. [telegram-username] - [user's-specified-nickname]
            formatted_entry = f"{index}. @{entry.username} - {entry.nickname}"
            nickname_list.append(formatted_entry)
        
        # Create response message
        count = len(nicknames)
        plural = "nickname" if count == 1 else "nicknames"
        
        response_message = (
            f"📋 **All Nicknames in This Group ({count} {plural}):**\n\n"
            + "\n".join(nickname_list) +
            f"\n\n💡 **Tip:** Use `/add <nickname>` to add yours, "
            f"or `/change <nickname>` to update an existing one!"
        )
        
        # Send the formatted list
        await message.answer(
            text=response_message,
            parse_mode="Markdown"
        )
        
        logger.info(
            f"All command handled successfully for group {group_id}, "
            f"returned {count} nicknames"
        )
        
    except Exception as e:
        logger.error(f"Error handling all command: {e}")
        await message.answer(
            "❌ An unexpected error occurred while retrieving nicknames. "
            "Please try again later."
        )


def register_all_handler(dispatcher, storage: StorageService) -> None:
    """
    Register all command handler with dispatcher.
    
    Args:
        dispatcher: Aiogram dispatcher instance
        storage: Storage service instance
    """
    set_storage_service(storage)
    # Create a new router for this registration
    all_router = Router()
    all_router.message(Command("all"))(handle_all_command)
    dispatcher.include_router(all_router)
    logger.info("All command handler registered")