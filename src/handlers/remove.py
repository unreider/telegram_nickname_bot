"""
Remove command handler for Telegram Nickname Bot.
Handles /remove command for removing user nicknames.
"""

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..storage import StorageService
from ..validation import validate_user_context, get_user_friendly_error

logger = logging.getLogger(__name__)

# Initialize storage service (will be injected via dependency)
storage_service: StorageService = None


def set_storage_service(service: StorageService) -> None:
    """Set the storage service instance for the handler."""
    global storage_service
    storage_service = service


async def handle_remove_command(message: Message, **kwargs) -> None:
    """
    Handle /remove command for removing user nicknames.
    
    Requirements addressed:
    - 5.1: Delete user's nickname from group storage
    - 5.2: Notify user if no nickname has been added yet
    - 5.3: Confirm removal to user when successful
    
    Args:
        message: The incoming message with /remove command
        **kwargs: Additional context from middleware (user_id, username, group_id)
    """
    try:
        # Get context data from middleware
        user_id = kwargs.get("user_id")
        username = kwargs.get("username")
        group_id = kwargs.get("group_id")
        
        # Validate user context
        context_valid, context_error = validate_user_context(user_id, username, group_id)
        if not context_valid:
            logger.error(f"Invalid user context: {context_error}")
            await message.answer(get_user_friendly_error('validation_error', context_error))
            return
        
        # Check if storage service is available
        if not storage_service:
            logger.error("Storage service not initialized")
            await message.answer(get_user_friendly_error('service_unavailable'))
            return
        
        # Check if user has a nickname in this group
        try:
            if not storage_service.has_nickname(group_id, user_id):
                await message.answer(
                    get_user_friendly_error('nickname_not_found') + "\n\n"
                    "💡 **Tip:** Use `/add <nickname>` to add a nickname first, "
                    "then you can remove it later if needed."
                )
                return
        except Exception as e:
            logger.error(f"Error checking existing nickname: {e}")
            await message.answer(get_user_friendly_error('storage_error'))
            return
        
        # Get the current nickname for confirmation message
        try:
            current_entry = storage_service.get_nickname(group_id, user_id)
            if not current_entry:
                # This shouldn't happen given our has_nickname check, but handle gracefully
                await message.answer(get_user_friendly_error('storage_error', "Unable to find your nickname"))
                return
        except Exception as e:
            logger.error(f"Error getting current nickname: {e}")
            await message.answer(get_user_friendly_error('storage_error'))
            return
        
        # Remove the nickname
        try:
            success = storage_service.remove_nickname(group_id, user_id)
            
            if success:
                # Confirm successful removal
                await message.answer(
                    f"✅ **Nickname removed successfully!**\n\n"
                    f"**Removed nickname:** {current_entry.nickname}\n"
                    f"**Username:** @{username}\n\n"
                    f"Your nickname has been deleted from this group. "
                    f"You can add a new one anytime using `/add <nickname>`.\n\n"
                    f"💡 **Tip:** Use `/all` to see the current list of nicknames in this group."
                )
                
                logger.info(
                    f"Nickname '{current_entry.nickname}' removed successfully for user @{username} "
                    f"(ID: {user_id}) in group {group_id}"
                )
            else:
                # Storage operation failed
                await message.answer(get_user_friendly_error('storage_error'))
                logger.error(
                    f"Failed to remove nickname for user {user_id} in group {group_id}"
                )
                
        except Exception as e:
            logger.error(f"Error removing nickname from storage: {e}")
            await message.answer(get_user_friendly_error('storage_error'))
        
    except Exception as e:
        logger.error(f"Unexpected error handling remove command: {e}")
        await message.answer(get_user_friendly_error('unknown_error'))


def register_remove_handler(dispatcher, storage: StorageService) -> None:
    """
    Register remove command handler with dispatcher.
    
    Args:
        dispatcher: Aiogram dispatcher instance
        storage: Storage service instance
    """
    set_storage_service(storage)
    # Create a new router for this registration
    remove_router = Router()
    remove_router.message(Command("remove"))(handle_remove_command)
    dispatcher.include_router(remove_router)
    logger.info("Remove command handler registered")