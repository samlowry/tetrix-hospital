import os
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Application, CallbackContext
import httpx
from telegram.error import TimedOut, NetworkError, TelegramError
import logging
import asyncio
from functools import wraps

logger = logging.getLogger('tetrix')

def retry_on_timeout(max_retries=3, initial_delay=1):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (TimedOut, NetworkError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed with {str(e)}, retrying in {delay}s...")
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(f"All {max_retries} attempts failed")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    raise
            
            raise last_exception
        return wrapper
    return decorator

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

@retry_on_timeout(max_retries=3, initial_delay=1)
async def handle_callback(update: Update, context: CallbackContext):
    """Handle callback query with retries."""
    query = update.callback_query
    try:
        # Answer callback query first
        await query.answer()
        
        # Process the callback data
        callback_data = query.data
        if callback_data == "start":
            # Handle start callback
            keyboard = create_inline_keyboard([
                {"text": "Connect Wallet", "callback_data": "connect"}
            ])
            await query.message.edit_text(
                "Welcome to TETRIX! Please connect your wallet to continue.",
                reply_markup=keyboard
            )
        elif callback_data == "connect":
            # Handle connect callback
            keyboard = create_inline_keyboard([
                {"text": "Open TON Connect", "url": "https://ton-connect.github.io/"}
            ])
            await query.message.edit_text(
                "Please connect your TON wallet to continue.",
                reply_markup=keyboard
            )
    except (TimedOut, NetworkError) as e:
        logger.error(f"Network error in callback handler: {e}")
        raise
    except TelegramError as e:
        logger.error(f"Telegram error in callback handler: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in callback handler: {e}")
        raise

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
            http2=True,
            retries=3
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