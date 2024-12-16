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
        self.frontend_url = os.getenv('FRONTEND_URL', 'https://tetrix-bot.vercel.app')
        self.last_button_messages = {}  # Store last button message IDs
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
                    [InlineKeyboardButton("Connect TON Wallet", web_app={"url": self.frontend_url})],
                    [InlineKeyboardButton("Create TON Wallet", callback_data='create_wallet')]
                ]
                message = "Welcome to TETRIX! Let's get started:"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                sent_message = await update.message.reply_text(message, reply_markup=reply_markup)
                # Store the message ID
                self.last_button_messages[update.effective_user.id] = sent_message.message_id
                logger.info(f"Stored button message ID {sent_message.message_id} for user {update.effective_user.id}")
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
        
        if query.data == 'reconnect_wallet':
            keyboard = [[InlineKeyboardButton("Reconnect Wallet", web_app={"url": self.frontend_url})]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Please verify your wallet using our secure web interface:",
                reply_markup=reply_markup
            )
            
        elif query.data == 'create_wallet':
            keyboard = [[InlineKeyboardButton("Connect Wallet", web_app={"url": self.frontend_url})]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "To create a TON wallet:\n\n"
                "1. Open @wallet in Telegram\n"
                "2. Click 'Create Wallet'\n"
                "3. Follow the setup instructions\n"
                "4. Return here and connect your wallet\n\n"
                "Click the button below when you're ready to connect:",
                reply_markup=reply_markup
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

    async def display_user_dashboard(self, telegram_id: int):
        """Display user dashboard with points and stats"""
        with self.flask_app.app_context():
            try:
                user = self.User.query.filter_by(telegram_id=telegram_id).first()
                if not user:
                    return
                
                # Try to delete the last message with buttons
                try:
                    if telegram_id in self.last_button_messages:
                        last_message_id = self.last_button_messages[telegram_id]
                        await self.application.bot.delete_message(
                            chat_id=telegram_id,
                            message_id=last_message_id
                        )
                        del self.last_button_messages[telegram_id]  # Clean up
                        logger.info(f"Deleted message {last_message_id} for user {telegram_id}")
                except Exception as e:
                    logger.error(f"Error deleting previous message: {e}")
                    # Continue even if deletion fails
                
                stats = user.get_stats()
                
                # Create ASCII health bar (escape all special chars)
                health_percentage = 42.0  # Dummy value for now
                bar_length = 20
                filled = int((health_percentage / 100) * bar_length)
                health_bar = "\\[" + "\\=" * filled + " " * (bar_length - filled) + "\\]"
                
                # Format invite codes with status
                code_lines = []
                for code_info in stats['invite_codes']:
                    if code_info['status'] == 'used_today':
                        # Strike-through for used codes
                        code_lines.append(f"~`{code_info['code']}`~ \\(Used\\)")
                    else:
                        code_lines.append(f"`{code_info['code']}`")
                
                while len(code_lines) < 5:  # Pad with empty slots
                    code_lines.append("\\_empty slot\\_")
                
                # Escape special characters for MarkdownV2
                def escape_md(text):
                    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                    escaped = str(text)
                    for char in chars:
                        escaped = escaped.replace(char, f"\\{char}")
                    return escaped
                
                # Format message with escaped characters
                message = f"""
TETRIX health status:
{health_bar} {escape_md(f"{health_percentage:.1f}")}%

Total Points: {escape_md(str(stats['points']))}

Points Breakdown:
For holding: {escape_md(str(stats['points_breakdown']['holding']))} points
For invites: {escape_md(str(stats['points_breakdown']['invites']))} points
Early backer bonus: {escape_md(str(stats['points_breakdown']['early_backer_bonus']))} points

Your Invite Codes:
{chr(10).join(code_lines)}
"""
                
                await self.application.bot.send_message(
                    telegram_id,
                    message,
                    parse_mode='MarkdownV2'
                )
                
            except Exception as e:
                logger.error(f"Error displaying dashboard: {e}")
                logger.error(f"Message that failed: {message}")  # Log the message that failed