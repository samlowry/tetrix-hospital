import os
import logging
import aiohttp
import unicodedata

logger = logging.getLogger(__name__)

def get_visual_width(s: str) -> int:
    """Get visual width of string considering wide characters"""
    width = 0
    for char in s:
        # Get East Asian width property
        width_property = unicodedata.east_asian_width(char)
        # F, W are full-width (wide), A is ambiguous (wide in East Asian context)
        width += 2 if width_property in ('F', 'W', 'A') else 1
    return width

def trim_to_visual_width(s: str, max_width: int) -> str:
    """Trim string to max visual width considering wide characters"""
    result = ""
    current_width = 0
    
    for char in s:
        char_width = 2 if unicodedata.east_asian_width(char) in ('F', 'W', 'A') else 1
        if current_width + char_width > max_width:
            return result + "…"
        current_width += char_width
        result += char
        
    return result

async def send_telegram_message(telegram_id: int, text: str, **kwargs) -> bool:
    """Send a message to a Telegram user"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": telegram_id,
        "text": text,
        "parse_mode": "HTML",
        **kwargs
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    return True
                logger.error(f"Error sending message: {await response.text()}")
                return False
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

async def split_and_send_message(telegram_id: int, text: str, **kwargs) -> bool:
    """Split long message and send parts"""
    MAX_LENGTH = 4000  # Leave some room for formatting
    
    # If message is short enough, send as is
    if len(text) <= MAX_LENGTH:
        return await send_telegram_message(telegram_id=telegram_id, text=text, **kwargs)
    
    # Split message into parts
    parts = []
    current_part = ""
    
    for line in text.split("\n"):
        # If adding this line would exceed max length
        if len(current_part) + len(line) + 1 > MAX_LENGTH:
            # If current part is not empty, add it to parts
            if current_part:
                parts.append(current_part)
            current_part = line
        else:
            # Add line to current part
            current_part = current_part + "\n" + line if current_part else line
    
    # Add last part if not empty
    if current_part:
        parts.append(current_part)
    
    # Send all parts
    success = True
    for part in parts:
        if not await send_telegram_message(telegram_id=telegram_id, text=part, **kwargs):
            success = False
    
    return success 