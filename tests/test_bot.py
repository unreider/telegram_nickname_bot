"""
Tests for bot handler and Aiogram setup.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError
from aiohttp import web

from src.bot import TelegramBot, create_bot
from src.config import BotConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return BotConfig(
        bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
        storage_file="test_data/nicknames.json",
        port=8000,
        webhook_url=None,
        python_env="development"
    )


@pytest.fixture
def mock_production_config():
    """Create a mock production configuration for testing."""
    return BotConfig(
        bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
        storage_file="test_data/nicknames.json",
        port=8000,
        webhook_url="https://example.com/webhook",
        python_env="production"
    )


class TestTelegramBot:
    """Test cases for TelegramBot class."""
    
    def test_init(self, mock_config):
        """Test bot initialization."""
        bot = TelegramBot(mock_config)
        
        assert bot.config == mock_config
        assert bot.bot is None
        assert bot.dispatcher is None
        assert bot.app is None
    
    def test_init_without_config(self):
        """Test bot initialization without config uses default."""
        with patch('src.bot.get_config') as mock_get_config:
            mock_get_config.return_value = Mock()
            bot = TelegramBot()
            assert bot.config is not None
            mock_get_config.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_config):
        """Test successful bot initialization."""
        bot = TelegramBot(mock_config)
        
        # Mock bot and its methods
        mock_bot_instance = AsyncMock()
        mock_bot_info = Mock()
        mock_bot_info.username = "test_bot"
        mock_bot_instance.get_me.return_value = mock_bot_info
        
        with patch('src.bot.Bot', return_value=mock_bot_instance) as mock_bot_class:
            with patch('src.bot.Dispatcher') as mock_dispatcher_class:
                mock_dispatcher_instance = Mock()
                mock_dispatcher_class.return_value = mock_dispatcher_instance
                
                await bot.initialize()
                
                # Verify bot was created with correct token
                mock_bot_class.assert_called_once_with(token=mock_config.bot_token)
                
                # Verify bot connection was tested
                mock_bot_instance.get_me.assert_called_once()
                
                # Verify dispatcher was created
                mock_dispatcher_class.assert_called_once()
                
                # Verify instances were assigned
                assert bot.bot == mock_bot_instance
                assert bot.dispatcher == mock_dispatcher_instance
    
    @pytest.mark.asyncio
    async def test_initialize_telegram_api_error(self, mock_config):
        """Test initialization with Telegram API error."""
        bot = TelegramBot(mock_config)
        
        mock_bot_instance = AsyncMock()
        # Create a mock method for TelegramAPIError
        from aiogram.methods import GetMe
        mock_method = GetMe()
        mock_bot_instance.get_me.side_effect = TelegramAPIError(mock_method, "API Error")
        
        with patch('src.bot.Bot', return_value=mock_bot_instance):
            with pytest.raises(TelegramAPIError):
                await bot.initialize()
    
    @pytest.mark.asyncio
    async def test_initialize_network_error(self, mock_config):
        """Test initialization with network error."""
        bot = TelegramBot(mock_config)
        
        mock_bot_instance = AsyncMock()
        # Create a mock method for TelegramNetworkError
        from aiogram.methods import GetMe
        mock_method = GetMe()
        mock_bot_instance.get_me.side_effect = TelegramNetworkError(mock_method, "Network Error")
        
        with patch('src.bot.Bot', return_value=mock_bot_instance):
            with pytest.raises(TelegramNetworkError):
                await bot.initialize()
    
    @pytest.mark.asyncio
    async def test_initialize_unexpected_error(self, mock_config):
        """Test initialization with unexpected error."""
        bot = TelegramBot(mock_config)
        
        with patch('src.bot.Bot', side_effect=Exception("Unexpected error")):
            with pytest.raises(Exception):
                await bot.initialize()
    
    @pytest.mark.asyncio
    async def test_setup_webhook_success(self, mock_production_config):
        """Test successful webhook setup."""
        bot = TelegramBot(mock_production_config)
        
        # Mock bot
        mock_bot_instance = AsyncMock()
        bot.bot = mock_bot_instance
        
        # Mock dispatcher
        mock_dispatcher = Mock()
        bot.dispatcher = mock_dispatcher
        
        with patch('src.bot.SimpleRequestHandler') as mock_handler_class:
            with patch('src.bot.setup_application') as mock_setup_app:
                with patch('src.bot.web.Application') as mock_app_class:
                    mock_app_instance = Mock()
                    mock_app_class.return_value = mock_app_instance
                    
                    mock_handler_instance = Mock()
                    mock_handler_class.return_value = mock_handler_instance
                    
                    app = await bot.setup_webhook()
                    
                    # Verify webhook was set
                    mock_bot_instance.set_webhook.assert_called_once_with(
                        url=mock_production_config.webhook_url,
                        drop_pending_updates=True
                    )
                    
                    # Verify handler was created and registered
                    mock_handler_class.assert_called_once_with(
                        dispatcher=mock_dispatcher,
                        bot=mock_bot_instance
                    )
                    mock_handler_instance.register.assert_called_once_with(
                        mock_app_instance, 
                        path="/webhook"
                    )
                    
                    # Verify application setup
                    mock_setup_app.assert_called_once_with(
                        mock_app_instance, 
                        mock_dispatcher, 
                        bot=mock_bot_instance
                    )
                    
                    assert app == mock_app_instance
                    assert bot.app == mock_app_instance
    
    @pytest.mark.asyncio
    async def test_setup_webhook_no_url(self, mock_config):
        """Test webhook setup without URL raises error."""
        bot = TelegramBot(mock_config)
        
        with pytest.raises(ValueError, match="Webhook URL is required"):
            await bot.setup_webhook()
    
    @pytest.mark.asyncio
    async def test_setup_webhook_api_error(self, mock_production_config):
        """Test webhook setup with API error."""
        bot = TelegramBot(mock_production_config)
        
        mock_bot_instance = AsyncMock()
        # Create a mock method for TelegramAPIError
        from aiogram.methods import SetWebhook
        mock_method = SetWebhook(url="test")
        mock_bot_instance.set_webhook.side_effect = TelegramAPIError(mock_method, "API Error")
        bot.bot = mock_bot_instance
        bot.dispatcher = Mock()
        
        with pytest.raises(TelegramAPIError):
            await bot.setup_webhook()
    
    @pytest.mark.asyncio
    async def test_start_polling_success(self, mock_config):
        """Test successful polling start."""
        bot = TelegramBot(mock_config)
        
        mock_bot_instance = AsyncMock()
        mock_dispatcher = AsyncMock()
        
        bot.bot = mock_bot_instance
        bot.dispatcher = mock_dispatcher
        
        await bot.start_polling()
        
        # Verify webhook was deleted
        mock_bot_instance.delete_webhook.assert_called_once_with(drop_pending_updates=True)
        
        # Verify polling was started
        mock_dispatcher.start_polling.assert_called_once_with(
            mock_bot_instance,
            skip_updates=True
        )
    
    @pytest.mark.asyncio
    async def test_start_polling_api_error(self, mock_config):
        """Test polling start with API error."""
        bot = TelegramBot(mock_config)
        
        mock_bot_instance = AsyncMock()
        # Create a mock method for TelegramAPIError
        from aiogram.methods import DeleteWebhook
        mock_method = DeleteWebhook()
        mock_bot_instance.delete_webhook.side_effect = TelegramAPIError(mock_method, "API Error")
        bot.bot = mock_bot_instance
        bot.dispatcher = Mock()
        
        with pytest.raises(TelegramAPIError):
            await bot.start_polling()
    
    @pytest.mark.asyncio
    async def test_start_polling_network_error(self, mock_config):
        """Test polling start with network error."""
        bot = TelegramBot(mock_config)
        
        mock_bot_instance = AsyncMock()
        mock_dispatcher = AsyncMock()
        # Create a mock method for TelegramNetworkError
        from aiogram.methods import DeleteWebhook
        mock_method = DeleteWebhook()
        mock_dispatcher.start_polling.side_effect = TelegramNetworkError(mock_method, "Network Error")
        
        bot.bot = mock_bot_instance
        bot.dispatcher = mock_dispatcher
        
        with pytest.raises(TelegramNetworkError):
            await bot.start_polling()
    
    @pytest.mark.asyncio
    async def test_start_development_mode(self, mock_config):
        """Test starting bot in development mode (polling)."""
        bot = TelegramBot(mock_config)
        
        with patch.object(bot, 'initialize') as mock_init:
            with patch.object(bot, 'start_polling') as mock_polling:
                result = await bot.start()
                
                mock_init.assert_called_once()
                mock_polling.assert_called_once()
                assert result is None
    
    @pytest.mark.asyncio
    async def test_start_production_mode(self, mock_production_config):
        """Test starting bot in production mode (webhook)."""
        bot = TelegramBot(mock_production_config)
        mock_app = Mock()
        
        with patch.object(bot, 'initialize') as mock_init:
            with patch.object(bot, 'setup_webhook', return_value=mock_app) as mock_webhook:
                result = await bot.start()
                
                mock_init.assert_called_once()
                mock_webhook.assert_called_once()
                assert result == mock_app
    
    @pytest.mark.asyncio
    async def test_stop(self, mock_config):
        """Test bot stop and cleanup."""
        bot = TelegramBot(mock_config)
        
        mock_session = AsyncMock()
        mock_bot_instance = Mock()
        mock_bot_instance.session = mock_session
        bot.bot = mock_bot_instance
        
        await bot.stop()
        
        mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_with_error(self, mock_config):
        """Test bot stop with error doesn't raise."""
        bot = TelegramBot(mock_config)
        
        mock_session = AsyncMock()
        mock_session.close.side_effect = Exception("Close error")
        mock_bot_instance = Mock()
        mock_bot_instance.session = mock_session
        bot.bot = mock_bot_instance
        
        # Should not raise exception
        await bot.stop()
        mock_session.close.assert_called_once()


class TestCreateBot:
    """Test cases for create_bot factory function."""
    
    @pytest.mark.asyncio
    async def test_create_bot_with_config(self, mock_config):
        """Test creating bot with provided config."""
        bot = await create_bot(mock_config)
        
        assert isinstance(bot, TelegramBot)
        assert bot.config == mock_config
    
    @pytest.mark.asyncio
    async def test_create_bot_without_config(self):
        """Test creating bot without config uses default."""
        with patch('src.bot.get_config') as mock_get_config:
            mock_get_config.return_value = Mock()
            bot = await create_bot()
            
            assert isinstance(bot, TelegramBot)
            mock_get_config.assert_called_once()


class TestMainFunction:
    """Test cases for main execution functions."""
    
    @pytest.mark.asyncio
    async def test_run_webhook_app(self):
        """Test running webhook application."""
        mock_app = Mock()
        
        with patch('src.bot.web.AppRunner') as mock_runner_class:
            with patch('src.bot.web.TCPSite') as mock_site_class:
                mock_runner = AsyncMock()
                mock_runner_class.return_value = mock_runner
                
                mock_site = AsyncMock()
                mock_site_class.return_value = mock_site
                
                # Mock asyncio.Future to raise KeyboardInterrupt immediately
                with patch('asyncio.Future', side_effect=KeyboardInterrupt):
                    from src.bot import run_webhook_app
                    await run_webhook_app(mock_app, 8000)
                
                # Verify runner setup and cleanup
                mock_runner.setup.assert_called_once()
                mock_runner.cleanup.assert_called_once()
                
                # Verify site creation and start
                mock_site_class.assert_called_once_with(mock_runner, host="0.0.0.0", port=8000)
                mock_site.start.assert_called_once()