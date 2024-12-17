from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from typing import Optional
import logging
import asyncio
import os
import telegram

logger = logging.getLogger('tetrix')

class BotManager:
    def __init__(self, token: str, db, User, ton_client, app):
        """Initialize bot with dependencies"""
        logger.info("Initializing bot manager...")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables")
        self.application = Application.builder().token(token).build()
        self.bot = telegram.Bot(token=token)  # Initialize bot instance
        self.db = db
        self.User = User
        self.ton_client = ton_client
        self.running = False
        self.flask_app = app
        self.frontend_url = os.getenv('FRONTEND_URL')
        self.redis = app.extensions['redis']  # Get Redis from Flask app
        self.setup_handlers()
        logger.info("Bot manager initialized successfully")

    def setup_handlers(self):
        """Setup bot command and callback handlers"""
        logger.info("Setting up bot handlers...")
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        logger.info("Bot handlers set up successfully")

    def _get_message_key(self, user_id: int) -> str:
        """Get Redis key for storing message ID"""
        return f"bot:message:{user_id}"

    async def _store_message_id(self, user_id: int, message_id: int):
        """Store message ID in Redis"""
        key = self._get_message_key(user_id)
        self.redis.set(key, str(message_id), ex=3600)  # Expire after 1 hour
        logger.info(f"Stored message ID {message_id} for user {user_id} in Redis")

    async def _get_message_id(self, user_id: int) -> Optional[int]:
        """Get message ID from Redis"""
        key = self._get_message_key(user_id)
        message_id = self.redis.get(key)
        if message_id:
            return int(message_id)
        return None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        
        # Use Flask app context
        with self.flask_app.app_context():
            # Check if user is registered
            user = self.User.query.filter_by(telegram_id=update.effective_user.id).first()
            
            if user:
                # Show dashboard for registered users
                await self.display_user_dashboard(update.effective_user.id)
            else:
                keyboard = [
                    [InlineKeyboardButton("Connect TON Wallet", web_app={"url": self.frontend_url})],
                    [InlineKeyboardButton("Create TON Wallet", callback_data='create_wallet')]
                ]
                message = "Welcome to TETRIX! Let's get started:"
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                try:
                    sent_message = await update.message.reply_text(message, reply_markup=reply_markup)
                    # Store the message ID in Redis
                    await self._store_message_id(update.effective_user.id, sent_message.message_id)
                except Exception as e:
                    logger.error(f"Error sending welcome message: {e}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        try:
            if query.data == 'enter_invite_code':
                # Show message asking to enter invite code
                message = "Please enter your invite code:"
                await query.edit_message_text(
                    text=message,
                    reply_markup=None  # Remove buttons while waiting for code
                )
                
            elif query.data == 'reconnect_wallet':
                keyboard = [[InlineKeyboardButton("Reconnect Wallet", web_app={"url": self.frontend_url})]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "Please verify your wallet using our secure web interface:",
                    reply_markup=reply_markup
                )
                
            elif query.data == 'create_wallet':
                keyboard = [
                    [InlineKeyboardButton("Connect Wallet", web_app={"url": self.frontend_url})],
                    [InlineKeyboardButton("Return", callback_data='return_to_start')]
                ]
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
                
            elif query.data == 'return_to_start':
                keyboard = [
                    [InlineKeyboardButton("Connect TON Wallet", web_app={"url": self.frontend_url})],
                    [InlineKeyboardButton("Create TON Wallet", callback_data='create_wallet')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "Welcome to TETRIX! Let's get started:",
                    reply_markup=reply_markup
                )
                
            elif query.data == 'check_stats':
                # Use the same dashboard display function
                await self.display_user_dashboard(update.effective_user.id, query.message.message_id)
                
            elif query.data == 'show_invites':
                with self.flask_app.app_context():
                    user = self.User.query.filter_by(telegram_id=update.effective_user.id).first()
                    if not user:
                        await query.edit_message_text("Please connect your wallet first.")
                        return
                    
                    codes = user.get_invite_codes()
                    
                    # Format invite codes
                    code_lines = []
                    for code_info in codes:
                        if code_info['status'] == 'used_today':
                            code_lines.append(f"~~```\n{code_info['code']}\n```~~ (Used)")
                        else:
                            code_lines.append(f"```\n{code_info['code']}\n```")
                    
                    while len(code_lines) < 5:
                        code_lines.append("*empty*")
                    
                    keyboard = [
                        [InlineKeyboardButton("Refresh Codes", callback_data='show_invites')],
                        [InlineKeyboardButton("Back to Stats", callback_data='back_to_menu')]                    
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Join codes with double newlines for separate copy blocks
                    message = "Your Invite Codes:\n\n" + "\n\n".join(code_lines) + "\n\n"
                    try:
                        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                    except telegram.error.BadRequest as e:
                        if "Message is not modified" in str(e):
                            # Just acknowledge the refresh with a notification
                            await query.answer("Codes are up to date!")
                        else:
                            raise
                
            elif query.data == 'back_to_menu':
                # Show dashboard for registered users
                await self.display_user_dashboard(update.effective_user.id, query.message.message_id)
        except telegram.error.BadRequest as e:
            if "Message is not modified" in str(e):
                # Just acknowledge the refresh with a notification
                await query.answer("Stats are up to date!")
            else:
                raise

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
                        # Show dashboard instead of old stats message
                        await self.display_user_dashboard(telegram_id)
                    else:
                        await update.message.reply_text(
                            " This wallet address doesn't match our records.\n"
                            "Please use the wallet address you registered with."
                        )
                    return
                
                # This is a new connection
                balance = await self.ton_client.get_tetrix_balance(wallet_address)
                user = self.User(wallet_address=wallet_address, telegram_id=telegram_id)
                self.db.session.add(user)
                self.db.session.commit()
                
                # Show dashboard instead of old stats message
                await self.display_user_dashboard(telegram_id)
                
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

    async def display_user_dashboard(self, telegram_id: int, message_id: Optional[int] = None):
        """Display user dashboard with points and stats"""
        with self.flask_app.app_context():
            try:
                user = self.User.query.filter_by(telegram_id=telegram_id).first()
                if not user:
                    return
                
                stats = user.get_stats()
                
                # Create ASCII health bar (escape all special chars)
                health_percentage = 42.0  # Dummy value for now
                bar_length = 20
                filled = int((health_percentage / 100) * bar_length)
                health_bar = "\\[" + "\\=" * filled + " " * (bar_length - filled) + "\\]"
                
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
Early backer bonus: {escape_md(str(stats['points_breakdown']['early_backer_bonus']))} points"""

                # Add buttons for actions
                keyboard = [
                    [InlineKeyboardButton("Refresh Stats", callback_data='check_stats')],
                    [InlineKeyboardButton("Show Invite Codes", callback_data='show_invites')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Try to get message ID from Redis if not provided
                if not message_id:
                    message_id = await self._get_message_id(telegram_id)
                    if message_id:
                        logger.info(f"Using message ID {message_id} from Redis for user {telegram_id}")

                if message_id:
                    try:
                        await self.application.bot.edit_message_text(
                            chat_id=telegram_id,
                            message_id=message_id,
                            text=message,
                            parse_mode='MarkdownV2',
                            reply_markup=reply_markup
                        )
                        logger.info(f"Successfully edited message {message_id} for user {telegram_id}")
                    except Exception as e:
                        logger.error(f"Error editing message: {e}")
                        # If editing fails, send a new message
                        sent_message = await self.application.bot.send_message(
                            telegram_id,
                            message,
                            parse_mode='MarkdownV2',
                            reply_markup=reply_markup
                        )
                        await self._store_message_id(telegram_id, sent_message.message_id)
                else:
                    # Send new message
                    sent_message = await self.application.bot.send_message(
                        telegram_id,
                        message,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
                    await self._store_message_id(telegram_id, sent_message.message_id)
                
            except Exception as e:
                logger.error(f"Error displaying dashboard: {e}")
                logger.error(f"Message that failed: {message}")  # Log the message that failed

    async def show_congratulations(self, telegram_id: int, message_id: Optional[int] = None, is_early_backer: bool = False):
        """Show congratulations message after successful registration"""
        try:
            # Escape special characters for MarkdownV2
            def escape_md(text):
                chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                escaped = str(text)
                for char in chars:
                    escaped = escaped.replace(char, f"\\{char}")
                return escaped

            # Format congratulations message
            message = "🎉 *Congratulations\\!*\n\n"
            message += "Your wallet has been successfully connected\\."
            
            if is_early_backer:
                message += "\n\n🌟 *You are an Early Backer\\!*\n"
                message += "You'll receive special bonuses and privileges\\."

            # Add button to view dashboard
            keyboard = [[InlineKeyboardButton("Go to Dashboard", callback_data='check_stats')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if message_id:
                try:
                    await self.application.bot.edit_message_text(
                        chat_id=telegram_id,
                        message_id=message_id,
                        text=message,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error editing congratulations message: {e}")
            else:
                sent_message = await self.application.bot.send_message(
                    telegram_id,
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
                await self._store_message_id(telegram_id, sent_message.message_id)

        except Exception as e:
            logger.error(f"Error showing congratulations: {e}")

    async def request_invite_code(self, telegram_id: int, message_id: Optional[int] = None):
        """Request invite code from user who is not an early backer"""
        try:
            # Escape special characters for MarkdownV2
            def escape_md(text):
                chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                escaped = str(text)
                for char in chars:
                    escaped = escaped.replace(char, f"\\{char}")
                return escaped

            # Format message requesting invite code
            message = "✨ *Wallet Connected Successfully\\!*\n\n"
            message += "To complete your registration, please enter an invite code\\.\n"
            message += "You can get an invite code from an existing TETRIX member\\."

            # Add button to try again if they have a code
            keyboard = [[InlineKeyboardButton("I have a code", callback_data='enter_invite_code')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if message_id:
                try:
                    await self.application.bot.edit_message_text(
                        chat_id=telegram_id,
                        message_id=message_id,
                        text=message,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error editing invite code request message: {e}")
            else:
                sent_message = await self.application.bot.send_message(
                    telegram_id,
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
                await self._store_message_id(telegram_id, sent_message.message_id)

        except Exception as e:
            logger.error(f"Error requesting invite code: {e}")