"""
Bot handler and Aiogram setup for Telegram Nickname Bot.
Handles bot initialization, dispatcher setup, and connection management.
"""

import logging
import asyncio
import time
from typing import Optional
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.types import Update
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramBadRequest, TelegramUnauthorizedError

from .config import BotConfig, get_config
from .middleware import setup_middleware
from .storage import StorageService
from .handlers.start import register_start_handler
from .handlers.add import register_add_handler
from .handlers.all import register_all_handler
from .handlers.change import register_change_handler
from .handlers.remove import register_remove_handler
from .handlers.help import register_help_handler


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Main bot handler class for managing Aiogram bot and dispatcher."""
    
    def __init__(self, config: Optional[BotConfig] = None):
        """Initialize bot with configuration."""
        self.config = config or get_config()
        self.bot: Optional[Bot] = None
        self.dispatcher: Optional[Dispatcher] = None
        self.app: Optional[web.Application] = None
        self.storage: Optional[StorageService] = None
        
    async def initialize(self) -> None:
        """Initialize bot and dispatcher with comprehensive error handling and retry logic."""
        max_retries = 3
        retry_delay = 1.0  # 1 second
        
        for attempt in range(max_retries):
            try:
                # Initialize bot with token
                self.bot = Bot(token=self.config.bot_token)
                
                # Test bot connection with retry logic
                bot_info = await self._retry_api_call(
                    self.bot.get_me,
                    "get bot info",
                    max_retries=3
                )
                logger.info(f"Bot initialized successfully: @{bot_info.username}")
                
                # Initialize dispatcher
                self.dispatcher = Dispatcher()
                
                # Initialize storage service
                self.storage = StorageService(self.config.storage_file)
                
                # Setup middleware
                setup_middleware(self.dispatcher)
                
                # Register handlers
                self._register_handlers()
                
                logger.info("Bot and dispatcher initialized successfully")
                return
                
            except TelegramUnauthorizedError as e:
                logger.error(f"Bot token is invalid: {e}")
                raise  # Don't retry for invalid token
                
            except TelegramBadRequest as e:
                logger.error(f"Bad request during initialization: {e}")
                raise  # Don't retry for bad requests
                
            except (TelegramAPIError, TelegramNetworkError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed during initialization: {e}")
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                else:
                    logger.error(f"Failed to initialize bot after {max_retries} attempts: {e}")
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error during bot initialization: {e}")
                raise
    
    async def _retry_api_call(self, api_call, operation_name: str, max_retries: int = 3, *args, **kwargs):
        """
        Retry API calls with exponential backoff for transient errors.
        
        Args:
            api_call: The API function to call
            operation_name: Description of the operation for logging
            max_retries: Maximum number of retry attempts
            *args, **kwargs: Arguments to pass to the API call
            
        Returns:
            Result of the API call
            
        Raises:
            The last exception if all retries fail
        """
        retry_delay = 1.0  # 1 second base delay
        
        for attempt in range(max_retries):
            try:
                result = await api_call(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"API call '{operation_name}' succeeded on attempt {attempt + 1}")
                return result
                
            except TelegramUnauthorizedError:
                # Don't retry for authorization errors
                logger.error(f"Authorization error for '{operation_name}' - not retrying")
                raise
                
            except TelegramBadRequest as e:
                # Don't retry for bad requests (usually permanent errors)
                logger.error(f"Bad request for '{operation_name}': {e} - not retrying")
                raise
                
            except (TelegramAPIError, TelegramNetworkError) as e:
                if attempt < max_retries - 1:
                    delay = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"API call '{operation_name}' failed on attempt {attempt + 1}: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"API call '{operation_name}' failed after {max_retries} attempts: {e}")
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error in API call '{operation_name}': {e}")
                raise

    def _register_handlers(self) -> None:
        """Register command handlers with dispatcher."""
        # Register start command handler
        register_start_handler(self.dispatcher)
        
        # Register add command handler
        register_add_handler(self.dispatcher, self.storage)
        
        # Register all command handler
        register_all_handler(self.dispatcher, self.storage)
        
        # Register change command handler
        register_change_handler(self.dispatcher, self.storage)
        
        # Register remove command handler
        register_remove_handler(self.dispatcher, self.storage)
        
        # Register help command handler
        register_help_handler(self.dispatcher)
        
        logger.info("Command handlers registered successfully")
    
    async def setup_webhook(self) -> web.Application:
        """Set up webhook for production deployment with retry logic."""
        if not self.config.webhook_url:
            raise ValueError("Webhook URL is required for webhook setup")
        
        try:
            # Set webhook with retry logic
            await self._retry_api_call(
                self.bot.set_webhook,
                "set webhook",
                max_retries=3,
                url=self.config.webhook_url,
                drop_pending_updates=True
            )
            logger.info(f"Webhook set to: {self.config.webhook_url}")
            
            # Create aiohttp application
            self.app = web.Application()
            
            # Create webhook handler
            webhook_handler = SimpleRequestHandler(
                dispatcher=self.dispatcher,
                bot=self.bot
            )
            
            # Register webhook handler
            webhook_handler.register(self.app, path="/webhook")
            
            # Add health check endpoint for Railway monitoring
            self._setup_health_check()
            
            # Setup application
            setup_application(self.app, self.dispatcher, bot=self.bot)
            
            logger.info("Webhook setup completed successfully")
            return self.app
            
        except Exception as e:
            logger.error(f"Error during webhook setup: {e}")
            raise
    
    def _setup_health_check(self) -> None:
        """Set up health check endpoint for Railway monitoring."""
        async def health_check(request):
            """Health check endpoint that returns bot status."""
            try:
                # Check if bot is initialized and responsive
                if not self.bot:
                    return web.json_response(
                        {"status": "unhealthy", "error": "Bot not initialized"},
                        status=503
                    )
                
                # Test bot connection with a simple API call
                try:
                    await self._retry_api_call(
                        self.bot.get_me,
                        "health check",
                        max_retries=1
                    )
                    
                    # Check storage service
                    storage_healthy = self.storage and self.storage.is_healthy()
                    
                    if storage_healthy:
                        return web.json_response({
                            "status": "healthy",
                            "timestamp": time.time(),
                            "bot": "connected",
                            "storage": "healthy"
                        })
                    else:
                        return web.json_response({
                            "status": "degraded",
                            "timestamp": time.time(),
                            "bot": "connected",
                            "storage": "unhealthy"
                        }, status=200)  # Still return 200 for degraded state
                        
                except Exception as api_error:
                    logger.warning(f"Health check API error: {api_error}")
                    return web.json_response({
                        "status": "unhealthy",
                        "timestamp": time.time(),
                        "error": "Bot API connection failed"
                    }, status=503)
                    
            except Exception as e:
                logger.error(f"Health check error: {e}")
                return web.json_response({
                    "status": "unhealthy",
                    "timestamp": time.time(),
                    "error": "Internal health check error"
                }, status=503)
        
        # Register health check route
        self.app.router.add_get("/health", health_check)
    
    async def start_polling(self) -> None:
        """Start polling for development environment with retry logic."""
        try:
            # Delete webhook if it exists with retry logic
            await self._retry_api_call(
                self.bot.delete_webhook,
                "delete webhook",
                max_retries=3,
                drop_pending_updates=True
            )
            logger.info("Webhook deleted, starting polling mode")
            
            # Start polling with error handling
            while True:
                try:
                    await self.dispatcher.start_polling(
                        self.bot,
                        skip_updates=True
                    )
                    break  # Exit loop if polling starts successfully
                    
                except (TelegramAPIError, TelegramNetworkError) as e:
                    logger.error(f"Polling error: {e}. Restarting in 5 seconds...")
                    await asyncio.sleep(5)
                    continue
                    
        except Exception as e:
            logger.error(f"Error during polling setup: {e}")
            raise
    
    async def start(self) -> Optional[web.Application]:
        """Start the bot based on configuration."""
        await self.initialize()
        
        if self.config.use_webhook():
            logger.info("Starting bot in webhook mode")
            return await self.setup_webhook()
        else:
            logger.info("Starting bot in polling mode")
            await self.start_polling()
            return None
    
    async def stop(self) -> None:
        """Stop the bot and clean up resources."""
        try:
            if self.bot:
                await self.bot.session.close()
                logger.info("Bot session closed")
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")


async def create_bot(config: Optional[BotConfig] = None) -> TelegramBot:
    """Factory function to create and initialize bot."""
    bot = TelegramBot(config)
    return bot


async def run_webhook_app(app: web.Application, port: int) -> None:
    """Run the webhook application."""
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, host="0.0.0.0", port=port)
        await site.start()
        
        logger.info(f"Webhook server started on port {port}")
        
        # Keep the server running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            await runner.cleanup()
            
    except Exception as e:
        logger.error(f"Error running webhook app: {e}")
        raise


def main() -> None:
    """Main entry point for bot execution."""
    async def run():
        try:
            config = get_config()
            bot = await create_bot(config)
            
            if config.use_webhook():
                app = await bot.start()
                if app:
                    await run_webhook_app(app, config.port)
            else:
                await bot.start()
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            raise
        finally:
            if 'bot' in locals():
                await bot.stop()
    
    # Run the bot
    asyncio.run(run())


if __name__ == "__main__":
    main()