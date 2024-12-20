import os
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application
import httpx
from telegram.error import TimedOut, NetworkError
import logging

logger = logging.getLogger('tetrix')

def create_inline_keyboard(buttons: list[dict]) -> InlineKeyboardMarkup:
    """Create inline keyboard from button list."""
    keyboard = []
    for button in buttons:
        keyboard.append([InlineKeyboardButton(
            text=button.get('text', ''),
            callback_data=button.get('callback_data'),
            url=button.get('url')
        )])
    return InlineKeyboardMarkup(keyboard)

async def init_bot(bot_token: str = None):
    """Initialize bot with webhook if URL is provided."""
    if not bot_token:
        logger.error("Bot token not provided")
        return
        
    # Configure connection pool and timeouts
    connection_pool = httpx.AsyncConnectionPool(
        max_keepalive_connections=5,
        max_connections=10,
        keepalive_expiry=30.0
    )
    
    timeout = httpx.Timeout(
        connect=5.0,  # Connection timeout
        read=30.0,    # Read timeout
        write=30.0,   # Write timeout
        pool=30.0     # Pool timeout
    )
    
    # Create bot with custom connection settings
    bot = Bot(
        token=bot_token,
        request=httpx.AsyncClient(
            timeout=timeout,
            pool=connection_pool,
            http2=True
        )
    )
    
    webhook_url = os.environ.get('WEBHOOK_URL')
    if webhook_url:
        try:
            # Remove any existing webhook
            await bot.delete_webhook()
            # Set new webhook
            await bot.set_webhook(url=webhook_url)
            logger.info(f"Bot webhook set to {webhook_url}")
        except (TimedOut, NetworkError) as e:
            logger.error(f"Failed to set webhook: {e}")
            # Retry once
            try:
                await bot.delete_webhook()
                await bot.set_webhook(url=webhook_url)
                logger.info(f"Bot webhook set to {webhook_url} (retry successful)")
            except Exception as e:
                logger.error(f"Failed to set webhook on retry: {e}")
    else:
        logger.warning("No webhook URL provided, bot will use polling")
    return bot