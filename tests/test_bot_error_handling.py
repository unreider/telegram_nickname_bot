"""
Unit tests for bot error handling and retry logic.
Tests API retry mechanisms and error recovery.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramUnauthorizedError, TelegramBadRequest

from src.bot import TelegramBot
from src.config import BotConfig


class TestBotErrorHandling:
    """Test cases for bot error handling and retry logic."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock bot configuration."""
        config = MagicMock(spec=BotConfig)
        config.bot_token = "test_token"
        config.storage_file = "test_storage.json"
        config.webhook_url = None
        config.port = 8000
        config.use_webhook.return_value = False
        return config
    
    @pytest.fixture
    def bot(self, mock_config):
        """Create a bot instance with mock config."""
        return TelegramBot(mock_config)
    
    @pytest.mark.asyncio
    async def test_retry_api_call_success_first_attempt(self, bot):
        """Test successful API call on first attempt."""
        # Setup
        mock_api_call = AsyncMock(return_value="success")
        
        # Execute
        result = await bot._retry_api_call(mock_api_call, "test operation")
        
        # Verify
        assert result == "success"
        mock_api_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_api_call_success_after_retry(self, bot):
        """Test successful API call after retry."""
        # Setup
        mock_api_call = AsyncMock()
        mock_api_call.side_effect = [
            TelegramNetworkError(method="test", message="Network error"),
            "success"
        ]
        
        # Execute
        result = await bot._retry_api_call(mock_api_call, "test operation", max_retries=2)
        
        # Verify
        assert result == "success"
        assert mock_api_call.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_api_call_max_retries_exceeded(self, bot):
        """Test API call failure after max retries."""
        # Setup
        mock_api_call = AsyncMock()
        mock_api_call.side_effect = TelegramNetworkError(method="test", message="Persistent network error")
        
        # Execute and verify exception
        with pytest.raises(TelegramNetworkError):
            await bot._retry_api_call(mock_api_call, "test operation", max_retries=3)
        
        assert mock_api_call.call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_api_call_no_retry_for_auth_error(self, bot):
        """Test that authorization errors are not retried."""
        # Setup
        mock_api_call = AsyncMock()
        mock_api_call.side_effect = TelegramUnauthorizedError(method="test", message="Invalid token")
        
        # Execute and verify exception
        with pytest.raises(TelegramUnauthorizedError):
            await bot._retry_api_call(mock_api_call, "test operation", max_retries=3)
        
        # Should not retry for auth errors
        mock_api_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_api_call_no_retry_for_bad_request(self, bot):
        """Test that bad requests are not retried."""
        # Setup
        mock_api_call = AsyncMock()
        mock_api_call.side_effect = TelegramBadRequest(method="test", message="Bad request")
        
        # Execute and verify exception
        with pytest.raises(TelegramBadRequest):
            await bot._retry_api_call(mock_api_call, "test operation", max_retries=3)
        
        # Should not retry for bad requests
        mock_api_call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_retry_api_call_unexpected_error(self, bot):
        """Test handling of unexpected errors."""
        # Setup
        mock_api_call = AsyncMock()
        mock_api_call.side_effect = ValueError("Unexpected error")
        
        # Execute and verify exception
        with pytest.raises(ValueError):
            await bot._retry_api_call(mock_api_call, "test operation", max_retries=3)
        
        # Should not retry for unexpected errors
        mock_api_call.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.bot.Bot')
    @patch('src.bot.Dispatcher')
    @patch('src.bot.StorageService')
    @patch('src.bot.setup_middleware')
    async def test_initialize_success_after_retry(self, mock_setup_middleware, mock_storage, mock_dispatcher, mock_bot_class, bot):
        """Test successful initialization after retry."""
        # Setup
        mock_bot_instance = AsyncMock()
        mock_bot_instance.get_me.side_effect = [
            TelegramNetworkError(method="getMe", message="Network error"),
            MagicMock(username="test_bot")
        ]
        mock_bot_class.return_value = mock_bot_instance
        
        mock_dispatcher_instance = MagicMock()
        mock_dispatcher.return_value = mock_dispatcher_instance
        
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        
        # Execute
        await bot.initialize()
        
        # Verify
        assert bot.bot == mock_bot_instance
        assert bot.dispatcher == mock_dispatcher_instance
        assert bot.storage == mock_storage_instance
        assert mock_bot_instance.get_me.call_count == 2
    
    @pytest.mark.asyncio
    @patch('src.bot.Bot')
    async def test_initialize_auth_error_no_retry(self, mock_bot_class, bot):
        """Test that initialization doesn't retry on auth errors."""
        # Setup
        mock_bot_instance = AsyncMock()
        mock_bot_instance.get_me.side_effect = TelegramUnauthorizedError(method="getMe", message="Invalid token")
        mock_bot_class.return_value = mock_bot_instance
        
        # Execute and verify exception
        with pytest.raises(TelegramUnauthorizedError):
            await bot.initialize()
        
        # Should not retry for auth errors
        mock_bot_instance.get_me.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.bot.Bot')
    async def test_initialize_max_retries_exceeded(self, mock_bot_class, bot):
        """Test initialization failure after max retries."""
        # Setup
        mock_bot_instance = AsyncMock()
        mock_bot_instance.get_me.side_effect = TelegramNetworkError(method="getMe", message="Persistent network error")
        mock_bot_class.return_value = mock_bot_instance
        
        # Execute and verify exception
        with pytest.raises(TelegramNetworkError):
            await bot.initialize()
        
        # Should retry 3 times at initialize level, each with 3 retries at API level = 9 total calls
        assert mock_bot_instance.get_me.call_count == 9
    
    @pytest.mark.asyncio
    async def test_setup_webhook_with_retry(self, bot):
        """Test webhook setup with retry logic."""
        # Setup
        bot.config.webhook_url = "https://example.com/webhook"
        bot.bot = AsyncMock()
        bot.dispatcher = MagicMock()
        
        bot.bot.set_webhook.side_effect = [
            TelegramNetworkError(method="setWebhook", message="Network error"),
            None  # Success
        ]
        
        with patch('src.bot.web.Application') as mock_app_class, \
             patch('src.bot.SimpleRequestHandler') as mock_handler_class, \
             patch('src.bot.setup_application') as mock_setup_app:
            
            mock_app = MagicMock()
            mock_app_class.return_value = mock_app
            
            mock_handler = MagicMock()
            mock_handler_class.return_value = mock_handler
            
            # Execute
            result = await bot.setup_webhook()
            
            # Verify
            assert result == mock_app
            assert bot.bot.set_webhook.call_count == 2
    
    @pytest.mark.asyncio
    async def test_start_polling_with_retry(self, bot):
        """Test polling start with retry logic."""
        # Setup
        bot.bot = AsyncMock()
        bot.dispatcher = AsyncMock()
        
        bot.bot.delete_webhook.side_effect = [
            TelegramNetworkError(method="deleteWebhook", message="Network error"),
            None  # Success
        ]
        
        # Mock start_polling to avoid infinite loop
        bot.dispatcher.start_polling.return_value = None
        
        # Execute
        await bot.start_polling()
        
        # Verify
        assert bot.bot.delete_webhook.call_count == 2
        bot.dispatcher.start_polling.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_polling_continuous_retry_on_error(self, bot):
        """Test that polling restarts on errors."""
        # Setup
        bot.bot = AsyncMock()
        bot.dispatcher = AsyncMock()
        
        bot.bot.delete_webhook.return_value = None
        
        # Mock start_polling to fail once then succeed
        call_count = 0
        async def mock_start_polling(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TelegramNetworkError(method="startPolling", message="Network error")
            return None
        
        bot.dispatcher.start_polling.side_effect = mock_start_polling
        
        # Execute with timeout to avoid infinite loop
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await bot.start_polling()
            
            # Verify retry behavior
            assert bot.dispatcher.start_polling.call_count == 2
            mock_sleep.assert_called_once_with(5)
    
    @pytest.mark.asyncio
    async def test_stop_with_error_handling(self, bot):
        """Test bot stop with error handling."""
        # Setup
        bot.bot = AsyncMock()
        bot.bot.session = AsyncMock()
        bot.bot.session.close.side_effect = Exception("Close error")
        
        # Execute - should not raise exception
        await bot.stop()
        
        # Verify close was attempted
        bot.bot.session.close.assert_called_once()


class TestBotIntegrationErrorHandling:
    """Test cases for integration-level error handling."""
    
    @pytest.mark.asyncio
    @patch('src.bot.get_config')
    @patch('src.bot.TelegramBot.initialize')
    @patch('src.bot.TelegramBot.start')
    async def test_main_error_handling(self, mock_start, mock_initialize, mock_get_config):
        """Test main function error handling."""
        from src.bot import main
        
        # Setup
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config
        mock_initialize.side_effect = Exception("Initialization error")
        
        # Execute and verify exception is raised
        with pytest.raises(Exception):
            main()


if __name__ == "__main__":
    pytest.main([__file__])