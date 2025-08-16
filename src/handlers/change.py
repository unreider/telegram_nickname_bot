"""
Change command handler for Telegram Nickname Bot.
Handles /change <nickname> command for updating user nicknames.
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


async def handle_change_command(message: Message, **kwargs) -> None:
    """
    Handle /change <nickname> command for updating user nicknames.
    
    Requirements addressed:
    - 4.1: Update user's existing nickname for that group
    - 4.2: Notify user if no nickname has been added yet
    - 4.3: Prompt user to provide new nickname if missing parameter
    - 4.4: Confirm change to user when successful
    
    Args:
        message: The incoming message with /change command
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
        
        # Check if user has an existing nickname in this group
        try:
            if not storage_service.has_nickname(group_id, user_id):
                await message.answer(
                    get_user_friendly_error('nickname_not_found') + "\n\n"
                    "Use `/add <nickname>` to add a nickname first, then you can change it later.\n\n"
                    "**Example:** `/add CoolUser123`"
                )
                return
        except Exception as e:
            logger.error(f"Error checking existing nickname: {e}")
            await message.answer(get_user_friendly_error('storage_error'))
            return
        
        # Sanitize command arguments
        sanitized_args = sanitize_command_args(command_args)
        
        # Check if new nickname parameter is provided
        if not sanitized_args:
            try:
                current_entry = storage_service.get_nickname(group_id, user_id)
                current_nickname = current_entry.nickname if current_entry else "Unknown"
            except Exception as e:
                logger.error(f"Error getting current nickname: {e}")
                current_nickname = "Unknown"
                
            await message.answer(
                get_user_friendly_error('missing_parameter') + "\n\n"
                "**Usage:** `/change <new_nickname>`\n"
                "**Example:** `/change NewCoolUser456`\n\n"
                f"**Current nickname:** {current_nickname}\n\n"
                "💡 **Tip:** Your new nickname should be something you'd like others in this group to call you!"
            )
            return
        
        # Extract new nickname from command arguments
        new_nickname = " ".join(sanitized_args)
        
        # Validate new nickname
        nickname_valid, validation_error = validate_nickname(new_nickname)
        if not nickname_valid:
            await message.answer(get_user_friendly_error('validation_error', validation_error))
            return
        
        # Get current nickname for comparison
        try:
            current_entry = storage_service.get_nickname(group_id, user_id)
            old_nickname = current_entry.nickname if current_entry else "Unknown"
        except Exception as e:
            logger.error(f"Error getting current nickname for comparison: {e}")
            await message.answer(get_user_friendly_error('storage_error'))
            return
        
        # Check if new nickname is the same as current
        if new_nickname == old_nickname:
            await message.answer(
                f"🤔 Your nickname is already set to **{new_nickname}**!\n\n"
                "If you want to keep it the same, no action is needed. "
                "Otherwise, please provide a different nickname."
            )
            return
        
        # Update the nickname
        try:
            success = storage_service.update_nickname(
                group_id=group_id,
                user_id=user_id,
                new_nickname=new_nickname
            )
            
            if success:
                # Confirm successful change
                await message.answer(
                    f"✅ **Nickname changed successfully!**\n\n"
                    f"**Old nickname:** {old_nickname}\n"
                    f"**New nickname:** {new_nickname}\n"
                    f"**Username:** @{username}\n\n"
                    f"Others can now see your updated nickname when they use `/all` to list all nicknames in this group.\n\n"
                    f"💡 **Tip:** Use `/change <nickname>` again if you want to update it further!"
                )
                
                logger.info(
                    f"Nickname changed successfully for user @{username} "
                    f"(ID: {user_id}) in group {group_id}: '{old_nickname}' -> '{new_nickname}'"
                )
            else:
                # Storage operation failed
                await message.answer(get_user_friendly_error('storage_error'))
                logger.error(
                    f"Failed to change nickname for user {user_id} in group {group_id}: "
                    f"'{old_nickname}' -> '{new_nickname}'"
                )
                
        except Exception as e:
            logger.error(f"Error updating nickname in storage: {e}")
            await message.answer(get_user_friendly_error('storage_error'))
        
    except Exception as e:
        logger.error(f"Unexpected error handling change command: {e}")
        await message.answer(get_user_friendly_error('unknown_error'))


# Removed _validate_nickname function - now using validation.py module


def register_change_handler(dispatcher, storage: StorageService) -> None:
    """
    Register change command handler with dispatcher.
    
    Args:
        dispatcher: Aiogram dispatcher instance
        storage: Storage service instance
    """
    set_storage_service(storage)
    # Create a new router for this registration
    change_router = Router()
    change_router.message(Command("change"))(handle_change_command)
    dispatcher.include_router(change_router)
    logger.info("Change command handler registered")