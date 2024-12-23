import os
import aiohttp
import logging

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def get_telegram_name(telegram_id: int) -> str:
    """Get user's current display name via Bot API"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return str(telegram_id)
            
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={'chat_id': telegram_id}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        result = data['result']
                        first_name = result.get('first_name', '')
                        last_name = result.get('last_name', '')
                        full_name = f"{first_name} {last_name}".strip()
                        return full_name or str(telegram_id)
        
        logger.error(f"Failed to get Telegram name for {telegram_id}")
        return str(telegram_id)
        
    except Exception as e:
        logger.error(f"Error getting Telegram name: {e}")
        return str(telegram_id) 