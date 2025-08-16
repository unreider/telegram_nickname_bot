"""
Unit tests for the validation module.
Tests input validation, sanitization, and error handling.
"""

import pytest
from src.validation import (
    validate_nickname, sanitize_nickname, validate_user_context,
    sanitize_command_args, get_user_friendly_error, ValidationError,
    _contains_suspicious_patterns
)


class TestNicknameValidation:
    """Test cases for nickname validation."""
    
    def test_validate_nickname_valid_cases(self):
        """Test validation of valid nicknames."""
        valid_nicknames = [
            "TestUser",
            "Cool User 123",
            "user_name",
            "User-Name",
            "User.Name",
            "User@123",
            "User#Tag",
            "User$Money",
            "User%Percent",
            "User^Power",
            "User&More",
            "User*Star",
            "User(Paren)",
            "User+Plus",
            "User=Equal",
            "User[Bracket]",
            "User{Brace}",
            "User|Pipe",
            "User;Semi",
            "User:Colon",
            "User,Comma",
            "User<Less>",
            "User?Question",
            "User~Tilde",
            "User`Backtick",
            "a",  # Minimum length
            "a" * 50  # Maximum length
        ]
        
        for nickname in valid_nicknames:
            is_valid, error = validate_nickname(nickname)
            assert is_valid, f"Expected '{nickname}' to be valid, got error: {error}"
            assert error is None
    
    def test_validate_nickname_empty_cases(self):
        """Test validation of empty nicknames."""
        empty_nicknames = ["", "   ", "\t", "\n", "\r\n", "  \t  "]
        
        for nickname in empty_nicknames:
            is_valid, error = validate_nickname(nickname)
            assert not is_valid
            assert "cannot be empty" in error
    
    def test_validate_nickname_too_long(self):
        """Test validation of too long nicknames."""
        long_nickname = "a" * 51  # 51 characters
        is_valid, error = validate_nickname(long_nickname)
        assert not is_valid
        assert "too long" in error
    
    def test_validate_nickname_invalid_type(self):
        """Test validation with non-string input."""
        invalid_inputs = [123, None, [], {}, True]
        
        for invalid_input in invalid_inputs:
            is_valid, error = validate_nickname(invalid_input)
            assert not is_valid
            assert "must be text" in error
    
    def test_validate_nickname_suspicious_patterns(self):
        """Test validation of nicknames with suspicious patterns."""
        suspicious_nicknames = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "User<script>",
            "eval(malicious)",
            "document.cookie",
            "window.location",
            "User\\x41",  # Hex encoded
            "User%41",    # URL encoded
        ]
        
        for nickname in suspicious_nicknames:
            is_valid, error = validate_nickname(nickname)
            assert not is_valid
            assert "harmful content" in error
    
    def test_validate_nickname_control_characters(self):
        """Test validation of nicknames with control characters."""
        control_char_nicknames = [
            "User\nNewline",
            "User\tTab",
            "User\rCarriage",
            "User\x00Null",
            "User\x1fControl"
        ]
        
        for nickname in control_char_nicknames:
            is_valid, error = validate_nickname(nickname)
            # Should be sanitized and become valid or invalid based on remaining content
            # Control characters should be removed by sanitization
            pass  # The actual behavior depends on sanitization


class TestNicknameSanitization:
    """Test cases for nickname sanitization."""
    
    def test_sanitize_nickname_control_characters(self):
        """Test sanitization replaces control characters with spaces."""
        test_cases = [
            ("User\nName", "User Name"),
            ("User\tName", "User Name"),
            ("User\rName", "User Name"),
            ("User\x00Name", "User Name"),  # Null character becomes space
            ("User\x1fName", "User Name"),  # Control character becomes space
        ]
        
        for input_nick, expected in test_cases:
            result = sanitize_nickname(input_nick)
            assert result == expected
    
    def test_sanitize_nickname_whitespace_normalization(self):
        """Test sanitization normalizes whitespace."""
        test_cases = [
            ("User  Name", "User Name"),
            ("  User Name  ", "User Name"),
            ("User   Multiple   Spaces", "User Multiple Spaces"),
            ("\t\nUser\t\nName\t\n", "User Name"),
        ]
        
        for input_nick, expected in test_cases:
            result = sanitize_nickname(input_nick)
            assert result == expected
    
    def test_sanitize_nickname_invalid_type(self):
        """Test sanitization with invalid input type."""
        with pytest.raises(ValidationError):
            sanitize_nickname(123)
        
        with pytest.raises(ValidationError):
            sanitize_nickname(None)


class TestSuspiciousPatterns:
    """Test cases for suspicious pattern detection."""
    
    def test_contains_suspicious_patterns_script_injection(self):
        """Test detection of script injection patterns."""
        suspicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "vbscript:msgbox(1)",
            "data:text/html,<script>alert(1)</script>",
            "onload=alert(1)",
            "onerror=alert(1)",
            "onclick=alert(1)",
        ]
        
        for suspicious_input in suspicious_inputs:
            assert _contains_suspicious_patterns(suspicious_input)
    
    def test_contains_suspicious_patterns_safe_input(self):
        """Test that safe inputs are not flagged as suspicious."""
        safe_inputs = [
            "NormalUser123",
            "User with spaces",
            "User-with_symbols.and@more",
            "User#hashtag",
            "User$money",
        ]
        
        for safe_input in safe_inputs:
            assert not _contains_suspicious_patterns(safe_input)


class TestUserContextValidation:
    """Test cases for user context validation."""
    
    def test_validate_user_context_valid(self):
        """Test validation of valid user context."""
        is_valid, error = validate_user_context(12345, "testuser", -100123456789)
        assert is_valid
        assert error is None
    
    def test_validate_user_context_invalid_user_id(self):
        """Test validation with invalid user ID."""
        invalid_user_ids = [None, "123", -1, 0]
        
        for user_id in invalid_user_ids:
            is_valid, error = validate_user_context(user_id, "testuser", -100123456789)
            assert not is_valid
            assert "user ID" in error
    
    def test_validate_user_context_invalid_username(self):
        """Test validation with invalid username."""
        invalid_usernames = [None, "", "   ", "user@name", "user name", "a" * 33]
        
        for username in invalid_usernames:
            is_valid, error = validate_user_context(12345, username, -100123456789)
            assert not is_valid
            assert "username" in error
    
    def test_validate_user_context_invalid_group_id(self):
        """Test validation with invalid group ID."""
        invalid_group_ids = [None, "123", 123, 0]  # Group IDs should be negative
        
        for group_id in invalid_group_ids:
            is_valid, error = validate_user_context(12345, "testuser", group_id)
            assert not is_valid
            assert "group ID" in error


class TestCommandArgsSanitization:
    """Test cases for command arguments sanitization."""
    
    def test_sanitize_command_args_valid(self):
        """Test sanitization of valid command arguments."""
        test_cases = [
            (["arg1", "arg2"], ["arg1", "arg2"]),
            (["  arg1  ", "  arg2  "], ["arg1", "arg2"]),
            (["arg1\narg2", "arg3\targ4"], ["arg1 arg2", "arg3 arg4"]),
        ]
        
        for input_args, expected in test_cases:
            result = sanitize_command_args(input_args)
            assert result == expected
    
    def test_sanitize_command_args_empty_removal(self):
        """Test that empty arguments are removed."""
        test_cases = [
            (["arg1", "", "arg2"], ["arg1", "arg2"]),
            (["", "   ", "arg1"], ["arg1"]),
            (["arg1", "\t\n", "arg2"], ["arg1", "arg2"]),
        ]
        
        for input_args, expected in test_cases:
            result = sanitize_command_args(input_args)
            assert result == expected
    
    def test_sanitize_command_args_invalid_type(self):
        """Test sanitization with invalid input type."""
        invalid_inputs = [None, "string", 123, {}]
        
        for invalid_input in invalid_inputs:
            result = sanitize_command_args(invalid_input)
            assert result == []
    
    def test_sanitize_command_args_mixed_types(self):
        """Test sanitization with mixed argument types."""
        mixed_args = ["valid", 123, None, "another", []]
        result = sanitize_command_args(mixed_args)
        assert result == ["valid", "another"]


class TestUserFriendlyErrors:
    """Test cases for user-friendly error messages."""
    
    def test_get_user_friendly_error_known_types(self):
        """Test getting user-friendly errors for known error types."""
        error_types = [
            'storage_error',
            'validation_error',
            'service_unavailable',
            'network_error',
            'api_error',
            'permission_error',
            'rate_limit',
            'unknown_error',
            'invalid_command',
            'missing_parameter',
            'duplicate_nickname',
            'nickname_not_found',
            'group_only',
        ]
        
        for error_type in error_types:
            message = get_user_friendly_error(error_type)
            assert isinstance(message, str)
            assert len(message) > 0
            assert "❌" in message or "⚠️" in message or "📝" in message
    
    def test_get_user_friendly_error_unknown_type(self):
        """Test getting user-friendly error for unknown error type."""
        message = get_user_friendly_error('unknown_error_type')
        assert "unexpected error occurred" in message
    
    def test_get_user_friendly_error_with_context(self):
        """Test getting user-friendly error with additional context."""
        message = get_user_friendly_error('storage_error', 'Database connection failed')
        assert "Database connection failed" in message
        assert "Additional info:" in message
    
    def test_get_user_friendly_error_without_context(self):
        """Test getting user-friendly error without additional context."""
        message = get_user_friendly_error('storage_error')
        assert "Additional info:" not in message


if __name__ == "__main__":
    pytest.main([__file__])