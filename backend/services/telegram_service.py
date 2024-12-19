from flask import current_app

class TelegramService:
    @property
    def bot_manager(self):
        return current_app.bot_manager

    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> int:
        """Send message and return message_id."""
        if not self.bot_manager.bot:
            print("Warning: Bot not initialized, skipping message send")
            return 0
            
        message = await self.bot_manager.bot.send_message(
            chat_id=chat_id, 
            text=text, 
            reply_markup=reply_markup
        )
        return message.message_id

    async def edit_message(self, chat_id: int, message_id: int, text: str, reply_markup=None) -> bool:
        """Edit existing message."""
        if not self.bot_manager.bot:
            print("Warning: Bot not initialized, skipping message edit")
            return False
            
        try:
            await self.bot_manager.bot.edit_message_text(
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
        if not self.bot_manager.bot:
            print("Warning: Bot not initialized, skipping message delete")
            return False
            
        try:
            await self.bot_manager.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except Exception as e:
            print(f"Failed to delete message: {e}")
            return False 