"""
Input validation utilities for Telegram Nickname Bot.
Provides comprehensive validation and sanitization for user inputs.
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Configuration constants
MAX_NICKNAME_LENGTH = 50
MIN_NICKNAME_LENGTH = 1
ALLOWED_NICKNAME_PATTERN = r'^[a-zA-Z0-9 \-_\.!@#$%^&*()+=\[\]{}|;:,.<>?~`]+$'


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def sanitize_nickname(nickname: str) -> str:
    """
    Sanitize nickname input by removing dangerous characters and normalizing whitespace.
    
    Args:
        nickname: Raw nickname input from user
        
    Returns:
        Sanitized nickname string
        
    Raises:
        ValidationError: If nickname cannot be sanitized
    """
    if not isinstance(nickname, str):
        raise ValidationError("Nickname must be a string")
    
    # Replace control characters with spaces (newlines, tabs, etc.)
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', nickname)
    
    # Normalize whitespace - replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Strip leading and trailing whitespace
    sanitized = sanitized.strip()
    
    return sanitized


def validate_nickname(nickname: str) -> Tuple[bool, Optional[str]]:
    """
    Validate nickname according to bot rules.
    
    Args:
        nickname: The nickname to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if nickname is valid, False otherwise
        - error_message: Error description if invalid, None if valid
    """
    try:
        # Basic type check
        if not isinstance(nickname, str):
            return False, "Nickname must be text"
        
        # Check for suspicious patterns BEFORE sanitization to catch raw input
        if _contains_suspicious_patterns(nickname):
            return False, "Nickname contains potentially harmful content. Please choose a different nickname."
        
        # Sanitize after security check
        sanitized = sanitize_nickname(nickname)
        
        # Check if nickname is empty after sanitization
        if not sanitized:
            return False, "Nickname cannot be empty. Please provide a valid nickname."
        
        # Check nickname length
        if len(sanitized) > MAX_NICKNAME_LENGTH:
            return False, f"Nickname is too long. Please use a nickname with {MAX_NICKNAME_LENGTH} characters or less."
        
        if len(sanitized) < MIN_NICKNAME_LENGTH:
            return False, f"Nickname is too short. Please provide at least {MIN_NICKNAME_LENGTH} character."
        
        # Check for allowed characters
        if not re.match(ALLOWED_NICKNAME_PATTERN, sanitized):
            return False, (
                "Nickname contains invalid characters. Please use only letters, numbers, "
                "spaces, and common symbols."
            )
        
        # Check for excessive whitespace (should be handled by sanitization, but double-check)
        if '  ' in sanitized:  # Multiple consecutive spaces
            return False, "Nickname cannot contain multiple consecutive spaces."
        
        # Check if nickname starts or ends with whitespace (should be handled by sanitization)
        if sanitized != sanitized.strip():
            return False, "Nickname cannot start or end with spaces."
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validating nickname '{nickname}': {e}")
        return False, "Unable to validate nickname. Please try again."


def _contains_suspicious_patterns(nickname: str) -> bool:
    """
    Check for suspicious patterns that might indicate malicious input.
    
    Args:
        nickname: Sanitized nickname to check
        
    Returns:
        True if suspicious patterns found, False otherwise
    """
    # Check for potential script injection patterns
    suspicious_patterns = [
        r'<script',
        r'javascript:',
        r'data:',
        r'vbscript:',
        r'onload=',
        r'onerror=',
        r'onclick=',
        r'eval\(',
        r'alert\(',
        r'document\.',
        r'window\.',
        r'location\.',
        r'href=',
        r'src=',
        r'\\x[0-9a-fA-F]{2}',  # Hex encoded characters
        r'%[0-9a-fA-F]{2}',    # URL encoded characters
    ]
    
    nickname_lower = nickname.lower()
    
    for pattern in suspicious_patterns:
        if re.search(pattern, nickname_lower, re.IGNORECASE):
            logger.warning(f"Suspicious pattern detected in nickname: {pattern}")
            return True
    
    return False


def validate_user_context(user_id: Optional[int], username: Optional[str], group_id: Optional[int]) -> Tuple[bool, Optional[str]]:
    """
    Validate user context data from middleware.
    
    Args:
        user_id: Telegram user ID
        username: Telegram username
        group_id: Telegram group chat ID
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if user_id is None or not isinstance(user_id, int):
        return False, "Invalid user ID"
    
    if username is None or not isinstance(username, str) or not username.strip():
        return False, "Invalid username"
    
    if group_id is None or not isinstance(group_id, int):
        return False, "Invalid group ID"
    
    # Additional validation for Telegram-specific constraints
    if user_id <= 0:
        return False, "Invalid user ID format"
    
    if group_id >= 0:  # Group IDs should be negative
        return False, "Invalid group ID format"
    
    # Validate username format (basic check)
    if not re.match(r'^[a-zA-Z0-9_]{1,32}$', username):
        return False, "Invalid username format"
    
    return True, None


def sanitize_command_args(args: list) -> list:
    """
    Sanitize command arguments from user input.
    
    Args:
        args: List of command arguments
        
    Returns:
        List of sanitized arguments
    """
    if not isinstance(args, list):
        return []
    
    sanitized_args = []
    for arg in args:
        if isinstance(arg, str):
            # Replace control characters with spaces and normalize whitespace
            sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', arg)
            sanitized = re.sub(r'\s+', ' ', sanitized)
            sanitized = sanitized.strip()
            
            if sanitized:  # Only add non-empty arguments
                sanitized_args.append(sanitized)
    
    return sanitized_args


def get_user_friendly_error(error_type: str, context: Optional[str] = None) -> str:
    """
    Get user-friendly error messages for different error types.
    
    Args:
        error_type: Type of error (e.g., 'storage_error', 'validation_error', etc.)
        context: Additional context for the error
        
    Returns:
        User-friendly error message
    """
    error_messages = {
        'storage_error': "❌ Unable to save your data right now. Please try again in a moment.",
        'validation_error': "❌ Invalid input. Please check your command and try again.",
        'service_unavailable': "❌ Service temporarily unavailable. Please try again later.",
        'network_error': "❌ Network connection issue. Please try again in a moment.",
        'api_error': "❌ Unable to communicate with Telegram. Please try again later.",
        'permission_error': "❌ Permission denied. Please check bot permissions in this group.",
        'rate_limit': "❌ Too many requests. Please wait a moment before trying again.",
        'unknown_error': "❌ An unexpected error occurred. Please try again later.",
        'invalid_command': "❌ Invalid command format. Use /help to see available commands.",
        'missing_parameter': "📝 Missing required parameter. Please check the command usage.",
        'duplicate_nickname': "⚠️ You already have a nickname set in this group!",
        'nickname_not_found': "⚠️ You don't have a nickname set in this group yet!",
        'group_only': "⚠️ This bot only works in group chats.",
    }
    
    base_message = error_messages.get(error_type, error_messages['unknown_error'])
    
    if context:
        return f"{base_message}\n\n💡 **Additional info:** {context}"
    
    return base_message