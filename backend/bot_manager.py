from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from typing import Optional
import logging
import asyncio
import os

logger = logging.getLogger('tetrix')

class BotManager:
    def __init__(self, token: str, db, User, ton_client, app):
        """Initialize bot with dependencies"""
        logger.info("Initializing bot manager...")
        self.application = Application.builder().token(token).build()
        self.db = db
        self.User = User
        self.ton_client = ton_client
        self.running = False
        self.flask_app = app
        self.frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        self.setup_handlers()
        logger.info("Bot manager initialized successfully")

    def setup_handlers(self):
        """Setup bot command and callback handlers"""
        logger.info("Setting up bot handlers...")
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        logger.info("Bot handlers set up successfully")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        
        # Use Flask app context
        with self.flask_app.app_context():
            # Check if user is registered
            user = self.User.query.filter_by(telegram_id=update.effective_user.id).first()
            
            if user:
                keyboard = [
                    [InlineKeyboardButton("Reconnect TON Wallet", callback_data='reconnect_wallet')],
                    [InlineKeyboardButton("Check Stats", callback_data='check_stats')]
                ]
                message = "Welcome back to TETRIX! What would you like to do?"
            else:
                keyboard = [
                    [InlineKeyboardButton("Connect TON Wallet", callback_data='connect_wallet')],
                    [InlineKeyboardButton("Create TON Wallet", callback_data='create_wallet')]
                ]
                message = "Welcome to TETRIX! Let's get started:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await update.message.reply_text(message, reply_markup=reply_markup)
                logger.info("Sent welcome message successfully")
            except Exception as e:
                logger.error(f"Error sending welcome message: {e}")

    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        with self.flask_app.app_context():
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
            keyboard = [[InlineKeyboardButton("Connect Wallet", web_app={"url": self.frontend_url})]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Please connect your TON wallet using our secure web interface:",
                reply_markup=reply_markup
            )
            
        elif query.data == 'reconnect_wallet':
            keyboard = [[InlineKeyboardButton("Reconnect Wallet", web_app={"url": self.frontend_url})]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Please verify your wallet using our secure web interface:",
                reply_markup=reply_markup
            )
            
        elif query.data == 'create_wallet':
            await query.edit_message_text(
                "To create a TON wallet:\n\n"
                "1. Download TON Wallet app\n"
                "2. Create new wallet\n"
                "3. Return here and click 'Connect TON Wallet'\n\n"
                "Download links:\n"
                "iOS: https://apps.apple.com/us/app/ton-wallet/id1473849522\n"
                "Android: https://play.google.com/store/apps/details?id=org.ton.wallet"
            )
            
        elif query.data == 'check_stats':
            await self.stats(update, context)

    async def handle_wallet_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle wallet address messages"""
        with self.flask_app.app_context():
            wallet_address = update.message.text
            telegram_id = update.effective_user.id
            
            try:
                # Validate wallet format
                if not self.validate_wallet_address(wallet_address):
                    await update.message.reply_text("Invalid wallet address format. Please try again.")
                    return
                
                # Check if this is a reconnection attempt
                user = self.User.query.filter_by(telegram_id=telegram_id).first()
                if user:
                    if user.wallet_address == wallet_address:
                        await update.message.reply_text(
                            "Identity verified! Your wallet is still connected.\n"
                            "Use /stats to check your status"
                        )
                    else:
                        await update.message.reply_text(
                            "❌ This wallet address doesn't match our records.\n"
                            "Please use the wallet address you registered with."
                        )
                    return
                
                # This is a new connection
                balance = await self.ton_client.get_tetrix_balance(wallet_address)
                user = self.User(wallet_address=wallet_address, telegram_id=telegram_id)
                self.db.session.add(user)
                self.db.session.commit()
                
                await update.message.reply_text(
                    f"Wallet connected successfully!\n"
                    f"TETRIX Balance: {balance}\n"
                    f"Use /stats to check your status"
                )
                
            except Exception as e:
                logger.error(f"Error handling wallet message: {e}")
                await update.message.reply_text("Error processing wallet address. Please try again later.")

    async def start_bot(self):
        logger.info("Starting bot...")
        try:
            await self.application.initialize()
            await self.application.start()
            self.running = True
            logger.info("Bot started successfully")
            
            # Start polling for updates
            await self.application.updater.start_polling()
            logger.info("Bot polling started")
            
            # Keep the bot running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
        finally:
            if self.running:
                await self.application.updater.stop()
                await self.application.stop()
                logger.info("Bot stopped")

    def run(self):
        logger.info("Setting up event loop for bot")
        try:
            asyncio.run(self.start_bot())
            logger.info("Bot event loop started")
        except KeyboardInterrupt:
            logger.info("Bot shutdown requested")
            self.running = False
        except Exception as e:
            logger.error(f"Error in bot run: {e}")
            raise

    def stop(self):
        """Stop the bot"""
        self.running = False

    def validate_wallet_address(self, wallet_address: str) -> bool:
        """Validate wallet address format"""
        # Implement your validation logic here
        return True