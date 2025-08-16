"""
Tests for configuration management.
"""

import os
import pytest
from unittest.mock import patch
from src.config import BotConfig, get_config


class TestBotConfig:
    """Test cases for BotConfig class."""
    
    def test_from_env_with_required_vars(self):
        """Test configuration creation with required environment variables."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            "PORT": "3000",
            "PYTHON_ENV": "development"
        }):
            config = BotConfig.from_env()

            assert config.bot_token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
            assert config.port == 3000
            assert config.python_env == "development"
            assert config.storage_file == "data/nicknames.json"  # default
            assert config.webhook_url is None
    
    def test_from_env_missing_bot_token(self):
        """Test that missing bot token raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN environment variable is required"):
                BotConfig.from_env()
    
    def test_from_env_with_all_vars(self):
        """Test configuration with all environment variables set."""
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            "STORAGE_FILE": "custom/path/nicknames.json",
            "PORT": "5000",
            "WEBHOOK_URL": "https://example.com/webhook",
            "PYTHON_ENV": "production"
        }):
            config = BotConfig.from_env()
            
            assert config.bot_token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
            assert config.storage_file == "custom/path/nicknames.json"
            assert config.port == 5000
            assert config.webhook_url == "https://example.com/webhook"
            assert config.python_env == "production"
    
    def test_is_production(self):
        """Test production environment detection."""
        config = BotConfig(
            bot_token="test_token",
            storage_file="test.json",
            port=8000,
            python_env="production"
        )
        assert config.is_production() is True
        
        config.python_env = "development"
        assert config.is_production() is False
    
    def test_use_webhook(self):
        """Test webhook usage determination."""
        # Production with webhook URL
        config = BotConfig(
            bot_token="test_token",
            storage_file="test.json",
            port=8000,
            webhook_url="https://example.com/webhook",
            python_env="production"
        )
        assert config.use_webhook() is True
        
        # Production without webhook URL
        config.webhook_url = None
        assert config.use_webhook() is False
        
        # Development with webhook URL
        config.python_env = "development"
        config.webhook_url = "https://example.com/webhook"
        assert config.use_webhook() is False
    
    def test_validate_success(self):
        """Test successful validation."""
        config = BotConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            storage_file="data/nicknames.json",
            port=8000,
            python_env="development"
        )
        # Should not raise any exception
        config.validate()
    
    def test_validate_empty_bot_token(self):
        """Test validation with empty bot token."""
        config = BotConfig(
            bot_token="",
            storage_file="data/nicknames.json",
            port=8000
        )
        with pytest.raises(ValueError, match="Bot token cannot be empty"):
            config.validate()
    
    def test_validate_invalid_bot_token_format(self):
        """Test validation with invalid bot token format."""
        config = BotConfig(
            bot_token="invalid_token",
            storage_file="data/nicknames.json",
            port=8000
        )
        with pytest.raises(ValueError, match="Invalid bot token format"):
            config.validate()
    
    def test_validate_invalid_port(self):
        """Test validation with invalid port."""
        config = BotConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            storage_file="data/nicknames.json",
            port=0
        )
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            config.validate()
        
        config.port = 70000
        with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
            config.validate()
    
    def test_validate_production_without_webhook(self):
        """Test validation of production environment without webhook URL."""
        config = BotConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            storage_file="data/nicknames.json",
            port=8000,
            python_env="production"
        )
        with pytest.raises(ValueError, match="WEBHOOK_URL is required for production environment"):
            config.validate()
    
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_validate_creates_storage_directory(self, mock_exists, mock_makedirs):
        """Test that validation creates storage directory if it doesn't exist."""
        mock_exists.return_value = False
        
        config = BotConfig(
            bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
            storage_file="custom/path/nicknames.json",
            port=8000
        )
        config.validate()
        
        mock_makedirs.assert_called_once_with("custom/path", exist_ok=True)


def test_get_config():
    """Test get_config function."""
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
        "PORT": "8000"
    }):
        config = get_config()
        assert isinstance(config, BotConfig)
        assert config.bot_token == "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"