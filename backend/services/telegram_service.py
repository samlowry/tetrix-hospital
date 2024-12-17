from utils.redis_service import redis_client
from utils.bot_manager import bot

class TelegramService:
    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> int:
        """Send message and return message_id."""
        if not bot:
            print("Warning: Bot not initialized, skipping message send")
            return 0
            
        message = await bot.send_message(
            chat_id=chat_id, 
            text=text, 
            reply_markup=reply_markup
        )
        return message.message_id

    async def edit_message(self, chat_id: int, message_id: int, text: str, reply_markup=None) -> bool:
        """Edit existing message."""
        if not bot:
            print("Warning: Bot not initialized, skipping message edit")
            return False
            
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            print(f"Failed to edit message: {e}")
            return False

    async def delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete message by id."""
        if not bot:
            print("Warning: Bot not initialized, skipping message delete")
            return False
            
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except Exception as e:
            print(f"Failed to delete message: {e}")
            return False 