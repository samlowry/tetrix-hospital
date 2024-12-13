from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from typing import Optional
import logging
import asyncio

logger = logging.getLogger('tetrix')

class BotManager:
    def __init__(self, token: str, db, User, ton_client):
        """Initialize bot with dependencies"""
        self.application = Application.builder().token(token).build()
        self.db = db
        self.User = User
        self.ton_client = ton_client
        self.running = False
        self.setup_handlers()

    def setup_handlers(self):
        """Setup bot command and callback handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        keyboard = [
            [InlineKeyboardButton("Connect TON Wallet", callback_data='connect_wallet')],
            [InlineKeyboardButton("Create TON Wallet", callback_data='create_wallet')],
            [InlineKeyboardButton("Check Stats", callback_data='check_stats')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Welcome to TETRIX! Let's get started:",
            reply_markup=reply_markup
        )

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            user = self.User.query.filter_by(
                telegram_id=update.effective_user.id
            ).first()
            
            if not user:
                await update.message.reply_text(
                    "Please connect your wallet first using /start"
                )
                return
                
            stats = user.get_stats()
            message = (
                f"🏆 Your Stats:\n\n"
                f"Points: {stats['points']}\n"
                f"TETRIX Balance: {stats['tetrix_balance']}\n"
                f"Invite Slots: {stats['invite_slots']}\n"
                f"Total Invites: {stats['total_invites']}\n"
                f"Point Multiplier: {stats['point_multiplier']}x"
            )
            
            await update.message.reply_text(message)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text(
                "Sorry, couldn't fetch your stats. Please try again later."
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'connect_wallet':
            # TODO: Implement wallet connection flow
            await query.edit_message_text(
                "Please send your TON wallet address:"
            )
            
        elif query.data == 'create_wallet':
            await query.edit_message_text(
                "To create a TON wallet:\n\n"
                "1. Download TON Wallet app\n"
                "2. Create new wallet\n"
                "3. Return here and click 'Connect TON Wallet'\n\n"
                "Download links:\n"
                "iOS: [App Store Link]\n"
                "Android: [Play Store Link]"
            )
            
        elif query.data == 'check_stats':
            await self.stats(update, context)

    async def handle_wallet_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle wallet address messages"""
        wallet_address = update.message.text
        telegram_id = update.effective_user.id
        
        try:
            # Validate wallet format
            if not self.validate_wallet_address(wallet_address):
                await update.message.reply_text("Invalid wallet address format. Please try again.")
                return
            
            # Check wallet balance
            balance = await self.ton_client.get_tetrix_balance(wallet_address)
            
            # Create or update user
            user = self.User.query.filter_by(telegram_id=telegram_id).first()
            if not user:
                user = self.User(wallet_address=wallet_address, telegram_id=telegram_id)
                self.db.session.add(user)
            else:
                user.wallet_address = wallet_address
            
            self.db.session.commit()
            
            await update.message.reply_text(
                f"Wallet connected successfully!\n"
                f"TETRIX Balance: {balance}\n"
                f"Use /stats to check your status"
            )
            
        except Exception as e:
            logger.error(f"Error connecting wallet: {e}")
            await update.message.reply_text("Error connecting wallet. Please try again later.")

    async def start_bot(self):
        await self.application.initialize()
        await self.application.start()
        self.running = True
        while self.running:
            try:
                await self.application.update_queue.get()
            except Exception as e:
                logger.error(f"Error in bot polling: {e}")
                if not self.running:
                    break
                await asyncio.sleep(1)

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.start_bot())
        except KeyboardInterrupt:
            self.running = False
        finally:
            loop.close()

    def stop(self):
        """Stop the bot"""
        self.running = False

    def validate_wallet_address(self, wallet_address: str) -> bool:
        """Validate wallet address format"""
        # Implement your validation logic here
        return True