#!/usr/bin/env python3
"""
Telegram Nickname Bot - Main entry point for Railway deployment
"""

import asyncio
import logging
import signal
import sys
import os
from src.bot import create_bot, run_webhook_app
from src.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for Railway deployment."""
    bot = None
    try:
        # Get configuration
        config = get_config()
        logger.info(f"Starting Telegram Nickname Bot in {config.python_env} mode")
        logger.info(f"Storage file: {config.storage_file}")
        logger.info(f"Port: {config.port}")
        
        # Create and initialize bot
        bot = await create_bot(config)
        logger.info("Bot created and initialized successfully")
        
        # Set up graceful shutdown
        shutdown_event = asyncio.Event()
        
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start bot based on environment
        if config.use_webhook():
            logger.info(f"Starting webhook server on port {config.port}")
            logger.info(f"Webhook URL: {config.webhook_url}")
            app = await bot.start()
            if app:
                # Run webhook server with graceful shutdown
                runner = None
                try:
                    from aiohttp import web
                    runner = web.AppRunner(app)
                    await runner.setup()
                    
                    site = web.TCPSite(runner, host="0.0.0.0", port=config.port)
                    await site.start()
                    
                    logger.info(f"Webhook server started successfully on port {config.port}")
                    
                    # Wait for shutdown signal
                    await shutdown_event.wait()
                    
                finally:
                    if runner:
                        await runner.cleanup()
                        logger.info("Webhook server stopped")
        else:
            logger.info("Starting in polling mode")
            await bot.start()
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if bot:
            try:
                await bot.stop()
                logger.info("Bot shutdown completed")
            except Exception as e:
                logger.error(f"Error during bot shutdown: {e}")


if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Run the bot
    asyncio.run(main())