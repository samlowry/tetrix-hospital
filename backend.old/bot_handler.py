from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

class TetrixBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    def setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.button))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("I have TON wallet", callback_data='has_wallet')],
            [InlineKeyboardButton("Create TON wallet", callback_data='create_wallet')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Welcome to TETRIX! Do you have a TON wallet?",
            reply_markup=reply_markup
        )

    async def button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == 'has_wallet':
            # TODO: Implement wallet connection flow
            await query.edit_message_text("Please connect your TON wallet...")
        elif query.data == 'create_wallet':
            # TODO: Implement wallet creation guide
            await query.edit_message_text("Let's create your TON wallet...")

    def run(self):
        self.application.run_polling() 