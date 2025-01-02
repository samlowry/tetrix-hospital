import os
import logging
import aiohttp

logger = logging.getLogger(__name__)

async def send_telegram_message(telegram_id: int, text: str) -> bool:
    """Send a message to a Telegram user"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to send message: {error_text}")
                    return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False 