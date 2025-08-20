"""
Configuration management for Telegram Nickname Bot.
Handles environment variables and deployment configurations.
"""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class BotConfig:
    """Configuration class for the Telegram Nickname Bot."""
    
    bot_token: str
    storage_file: str
    port: int
    webhook_url: Optional[str] = None
    python_env: str = "development"
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        """Create configuration from environment variables."""
        # Validate required environment variables
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        # Set default storage file path
        storage_file = os.getenv("STORAGE_FILE", "data/nicknames.json")
        
        # Get port from environment (Railway provides this)
        port = int(os.getenv("PORT", "8000"))
        
        # Get environment type first
        python_env = os.getenv("PYTHON_ENV", "development")
        
        # Get webhook URL for production deployment
        webhook_url = os.getenv("WEBHOOK_URL")
        
        # If no explicit webhook URL is provided but we're in production,
        # try to construct it from Railway environment variables
        if not webhook_url and python_env.lower() == "production":
            railway_static_url = os.getenv("RAILWAY_STATIC_URL")
            railway_public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
            
            if railway_static_url:
                webhook_url = f"{railway_static_url}/webhook"
            elif railway_public_domain:
                webhook_url = f"https://{railway_public_domain}/webhook"
        
        return cls(
            bot_token=bot_token,
            storage_file=storage_file,
            port=port,
            webhook_url=webhook_url,
            python_env=python_env
        )
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.python_env.lower() == "production"
    
    def use_webhook(self) -> bool:
        """Determine if webhook should be used instead of polling."""
        return self.is_production() and self.webhook_url is not None
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.bot_token:
            raise ValueError("Bot token cannot be empty")
        
        if not self.bot_token.startswith(("bot", "BOT")):
            # Telegram bot tokens typically don't start with 'bot', but let's validate format
            if ":" not in self.bot_token:
                raise ValueError("Invalid bot token format")
        
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        
        if self.is_production() and not self.webhook_url:
            raise ValueError("WEBHOOK_URL is required for production environment")
        
        # Ensure storage directory exists
        storage_dir = os.path.dirname(self.storage_file)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)


def get_config() -> BotConfig:
    """Get validated configuration instance."""
    config = BotConfig.from_env()
    config.validate()
    return config