import os
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application

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
        print("Bot token not provided")
        return
        
    bot = Bot(token=bot_token)
    webhook_url = os.environ.get('WEBHOOK_URL')
    if webhook_url:
        # Remove any existing webhook
        await bot.delete_webhook()
        # Set new webhook
        await bot.set_webhook(url=webhook_url)
        print(f"Bot webhook set to {webhook_url}")
    else:
        print("No webhook URL provided, bot will use polling")
    return bot