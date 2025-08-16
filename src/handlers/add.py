"""
Add command handler for Telegram Nickname Bot.
Handles /add <nickname> command for adding user nicknames.
"""

import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from ..storage import StorageService
from ..validation import validate_nickname, validate_user_context, sanitize_command_args, get_user_friendly_error

logger = logging.getLogger(__name__)

# Initialize storage service (will be injected via dependency)
storage_service: StorageService = None


def set_storage_service(service: StorageService) -> None:
    """Set the storage service instance for the handler."""
    global storage_service
    storage_service = service


async def handle_add_command(message: Message, **kwargs) -> None:
    """
    Handle /add <nickname> command for adding user nicknames.
    
    Requirements addressed:
    - 2.1: Store nickname associated with user's Telegram username for specific group
    - 2.2: Notify user if nickname is already added
    - 2.3: Prompt user to provide nickname if missing parameter
    - 2.4: Confirm addition to user when successful
    
    Args:
        message: The incoming message with /add command
        **kwargs: Additional context from middleware (command_args, user_id, username, group_id)
    """
    try:
        # Get context data from middleware
        command_args = kwargs.get("command_args", [])
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
        
        # Sanitize command arguments
        sanitized_args = sanitize_command_args(command_args)
        
        # Check if nickname parameter is provided
        if not sanitized_args:
            await message.answer(
                get_user_friendly_error('missing_parameter') + "\n\n"
                "**Usage:** `/add <your_nickname>`\n"
                "**Example:** `/add CoolUser123`\n\n"
                "💡 **Tip:** Your nickname should be something you'd like others in this group to call you!"
            )
            return
        
        # Extract nickname from command arguments
        nickname = " ".join(sanitized_args)
        
        # Validate nickname
        nickname_valid, validation_error = validate_nickname(nickname)
        if not nickname_valid:
            await message.answer(get_user_friendly_error('validation_error', validation_error))
            return
        
        # Check if user already has a nickname in this group
        try:
            if storage_service.has_nickname(group_id, user_id):
                existing_entry = storage_service.get_nickname(group_id, user_id)
                current_nickname = existing_entry.nickname if existing_entry else "Unknown"
                await message.answer(
                    get_user_friendly_error('duplicate_nickname') + "\n\n"
                    f"**Current nickname:** {current_nickname}\n\n"
                    f"If you want to change it, use `/change <new_nickname>` instead."
                )
                return
        except Exception as e:
            logger.error(f"Error checking existing nickname: {e}")
            await message.answer(get_user_friendly_error('storage_error'))
            return
        
        # Add the nickname
        try:
            success = storage_service.add_nickname(
                group_id=group_id,
                user_id=user_id,
                username=username,
                nickname=nickname
            )
            
            if success:
                # Confirm successful addition
                await message.answer(
                    f"✅ **Nickname added successfully!**\n\n"
                    f"**Your nickname:** {nickname}\n"
                    f"**Username:** @{username}\n\n"
                    f"Others can now see your nickname when they use `/all` to list all nicknames in this group.\n\n"
                    f"💡 **Tip:** Use `/change <new_nickname>` if you want to update it later!"
                )
                
                logger.info(
                    f"Nickname '{nickname}' added successfully for user @{username} "
                    f"(ID: {user_id}) in group {group_id}"
                )
            else:
                # Storage operation failed
                await message.answer(get_user_friendly_error('storage_error'))
                logger.error(
                    f"Failed to add nickname '{nickname}' for user {user_id} in group {group_id}"
                )
                
        except Exception as e:
            logger.error(f"Error adding nickname to storage: {e}")
            await message.answer(get_user_friendly_error('storage_error'))
        
    except Exception as e:
        logger.error(f"Unexpected error handling add command: {e}")
        await message.answer(get_user_friendly_error('unknown_error'))


# Removed _validate_nickname function - now using validation.py module


def register_add_handler(dispatcher, storage: StorageService) -> None:
    """
    Register add command handler with dispatcher.
    
    Args:
        dispatcher: Aiogram dispatcher instance
        storage: Storage service instance
    """
    set_storage_service(storage)
    # Create a new router for this registration
    add_router = Router()
    add_router.message(Command("add"))(handle_add_command)
    dispatcher.include_router(add_router)
    logger.info("Add command handler registered")