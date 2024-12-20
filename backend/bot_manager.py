from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from typing import Optional
import logging
import asyncio
import os
import telegram
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import WEBHOOK_URL, REDIS_URL

logger = logging.getLogger('tetrix')

class BotManager:
    def __init__(self, token: str, db, User, ton_client, app):
        """Initialize bot with dependencies"""
        logger.info("Initializing bot manager...")
        
        if not token:
            raise ValueError("Bot token not found in environment variables")
        
        if not os.getenv('BACKEND_URL'):
            raise ValueError("BACKEND_URL not found in environment variables")
        
        self.token = token
        self.db = db
        self.User = User
        self.ton_client = ton_client
        self.app = app
        
        # Initialize bot with token
        self.bot = telegram.Bot(token=token)
        
        # Setup webhook URL
        self.webhook_url = WEBHOOK_URL
        
        self.application = Application.builder().token(token).build()
        self.redis = app.extensions['redis']
        
        # Initialize limiter with Redis URL from config
        self.limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri=REDIS_URL
        )
        
        self.setup_handlers()
        logger.info("Bot manager initialized successfully")

    def setup_handlers(self):
        """Setup bot command and callback handlers"""
        logger.info("Setting up bot handlers...")
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        # Add message handler for invite codes
        from telegram.ext import MessageHandler, filters
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        logger.info("Bot handlers set up successfully")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        logger.info(f"Received /start command from user {update.effective_user.id}")
        
        # Use Flask app context
        with self.app.app_context():
            # Check if user is registered
            user = self.User.query.filter_by(telegram_id=update.effective_user.id).first()
            
            if user:
                # Check registration status
                if user.is_fully_registered or user.is_early_backer:
                    # Show dashboard for fully registered users
                    await self.display_user_dashboard(update.effective_user.id)
                else:
                    # Show invite code prompt for users who need to complete registration
                    logger.info(f"User {update.effective_user.id} needs to complete registration with invite code")
                    message = "✨ *Welcome back\\!*\n\n"
                    message += "To complete your registration, please enter an invite code\\.\n"
                    message += "You can get an invite code from an existing TETRIX member\\."
                    
                    keyboard = [[InlineKeyboardButton("I have a code", callback_data='enter_invite_code')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        message,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
            else:
                # Show initial wallet connection prompt for new users
                keyboard = [
                    [InlineKeyboardButton("Connect TON Wallet", web_app={"url": self.frontend_url})],
                    [InlineKeyboardButton("Create TON Wallet", callback_data='create_wallet')]
                ]
                message = "Welcome to TETRIX! Let's get started:"
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(message, reply_markup=reply_markup)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        try:
            # For stats and invite-related callbacks, check registration status first
            if query.data in ['check_stats', 'show_invites', 'back_to_menu']:
                with self.app.app_context():
                    user = self.User.query.filter_by(telegram_id=update.effective_user.id).first()
                    if not user or not (user.is_fully_registered or user.is_early_backer):
                        logger.info(f"Ignoring {query.data} callback for non-fully registered user")
                        return
            
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
                # Send new dashboard message
                await self.display_user_dashboard(telegram_id=update.effective_user.id)
                
            elif query.data == 'show_invites':
                with self.app.app_context():
                    user = self.User.query.filter_by(telegram_id=update.effective_user.id).first()
                    if not user:
                        await query.edit_message_text("Please connect your wallet first.")
                        return
                    
                    codes = user.get_invite_codes()
                    
                    # Format invite codes
                    code_lines = []
                    for code_info in codes:
                        # Escape special characters for MarkdownV2
                        code = code_info['code'].replace('-', '\\-')  # Escape dashes
                        if code_info['status'] == 'used_today':
                            code_lines.append(f"~{code}~\n")
                        else:
                            code_lines.append(f"```\n{code}\n```")
                    
                    while len(code_lines) < 5:
                        code_lines.append("*empty*")
                    
                    keyboard = [
                        [InlineKeyboardButton("Refresh Codes", callback_data='show_invites')],
                        [InlineKeyboardButton("Back to Stats", callback_data='back_to_menu')]                    
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send new message with codes
                    message = "Your Invite Codes:\n\n" + "\n".join(code_lines) + "\n"
                    await self.application.bot.send_message(
                        update.effective_user.id,
                        message,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
                
            elif query.data == 'back_to_menu':
                # Show dashboard for registered users
                await self.display_user_dashboard(telegram_id=update.effective_user.id)
                
        except telegram.error.BadRequest as e:
            if "Message is not modified" in str(e):
                # Just acknowledge the refresh with a notification
                await query.answer("Stats are up to date!")
            else:
                raise

    async def handle_wallet_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle wallet address messages"""
        with self.app.app_context():
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
        """Start the bot with webhook"""
        logger.info("Starting bot...")
        try:
            # Initialize application
            await self.application.initialize()
            
            # Get current webhook info
            webhook_info = await self.bot.get_webhook_info()
            current_url = webhook_info.url
            target_url = self.webhook_url  # Use the full URL from config

            # Only set webhook if URL is different
            if current_url != target_url:
                logger.info(f"Updating webhook from {current_url} to {target_url}")
                await self.application.bot.set_webhook(
                    url=target_url,
                    allowed_updates=['message', 'callback_query']
                )
            else:
                logger.info("Webhook URL is already correct, skipping update")

            # Start application
            await self.application.start()
            logger.info("Bot started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return False

    async def stop_bot(self):
        """Stop the bot"""
        try:
            await self.application.stop()
            logger.info("Bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            raise

    def validate_wallet_address(self, wallet_address: str) -> bool:
        """Validate wallet address format"""
        # Implement your validation logic here
        return True

    async def _should_edit_message(self, telegram_id: int, message_id: int, update: Update = None) -> bool:
        """Check if we should edit the message or send a new one.
        Returns True if we should edit, False if we should send new message."""
        if not message_id:
            logger.info("No message_id provided, will send new message")
            return False
            
        try:
            # Check if this is a callback query (button press)
            if not update or not update.callback_query:
                logger.info("Not a button press, will send new message")
                return False
                
            # Check if we're trying to edit the same message that has the button
            if update.callback_query.message.message_id != message_id:
                logger.info(f"Button press was on different message (button: {update.callback_query.message.message_id}, target: {message_id}), will send new message")
                return False
                
            logger.info(f"Will edit message {message_id} in response to button press")
            return True
            
        except Exception as e:
            logger.error(f"Error checking message status: {e}")
            return False

    async def display_user_dashboard(self, telegram_id: int, message_id: Optional[int] = None, update: Update = None):
        """Display user dashboard with points and stats"""
        with self.app.app_context():
            try:
                logger.info(f"Displaying dashboard for user {telegram_id}")
                
                user = self.User.query.filter_by(telegram_id=telegram_id).first()
                if not user:
                    logger.warning(f"User {telegram_id} not found in database")
                    return
                
                stats = user.get_stats()
                
                # Create ASCII health bar (escape all special chars)
                health_percentage = 1.0  # Set to 1%
                bar_length = 20
                filled = max(1, int((health_percentage / 100) * bar_length))  # At least 1 bar if percentage > 0
                health_bar = "\\[" + "█" * filled + "░" * (bar_length - filled) + "\\]"
                
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
`{health_bar} {escape_md(f"{health_percentage:.1f}")}%`

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

                # Always send new message
                logger.info("Sending new dashboard message")
                await self.application.bot.send_message(
                    telegram_id,
                    message,
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
                
            except Exception as e:
                logger.error(f"Error displaying dashboard: {e}")
                logger.error(f"Message that failed: {message}")  # Log the message that failed

    async def show_congratulations(self, telegram_id: int, message_id: Optional[int] = None, is_early_backer: bool = False, update: Update = None):
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

            # Always send new message for congratulations
            await self.application.bot.send_message(
                telegram_id,
                message,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error showing congratulations: {e}")

    async def request_invite_code(self, telegram_id: int, message_id: Optional[int] = None, update: Update = None):
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

            # Always send new message for invite code request
            await self.application.bot.send_message(
                telegram_id,
                message,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error requesting invite code: {e}")

    async def _check_rate_limit(self, telegram_id: int) -> bool:
        """Check if user has exceeded rate limit (5 attempts per hour)"""
        key = f"invite_code_limit:{telegram_id}"
        try:
            # Get current count
            count = self.redis.get(key)
            if count is None:
                # First attempt
                self.redis.setex(key, 3600, 1)  # Expire in 1 hour
                return True
            
            count = int(count)
            if count >= 5:
                return False
            
            # Increment count
            self.redis.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (invite codes)"""
        with self.app.app_context():
            telegram_id = update.effective_user.id
            
            # Ignore commands
            if update.message.text.startswith('/'):
                return
                
            text = update.message.text.strip()  # Trim whitespace and newlines
            logger.info(f"Received message from {telegram_id}: {text}")
            
            # Check if user exists
            user = self.User.query.filter_by(telegram_id=telegram_id).first()
            if not user:
                logger.info(f"User {telegram_id} not found in database, ignoring message")
                return
                
            # If user is fully registered or is early backer, ignore non-command messages
            if user.is_fully_registered or user.is_early_backer:
                logger.info(f"User {telegram_id} is fully registered or early backer, ignoring message")
                return
            
            # Check rate limit for unregistered users
            if not await self._check_rate_limit(telegram_id):
                logger.info(f"Rate limit exceeded for user {telegram_id}")
                await update.message.reply_text(
                    "❌ Rate limit exceeded. Please try again later.",
                    reply_markup=None
                )
                return
            
            # At this point, user exists but is not fully registered
            # Treat any message as a potential invite code
            logger.info(f"Treating message as invite code from unregistered user {telegram_id}")
            
            # Verify invite code
            try:
                logger.info(f"Verifying invite code: {text}")
                invite = self.User.verify_invite_code(text)  # Returns invite object or None
                logger.info(f"Invite code verification result: {invite is not None}")
                
                if invite:
                    # Use the invite code
                    logger.info(f"Using invite code {text} for user {user.id}")
                    if self.User.use_invite_code(text, user.id):
                        # Show congratulations message with dashboard button
                        logger.info("Sending success message")
                        keyboard = [[InlineKeyboardButton("Go to Dashboard", callback_data='check_stats')]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        message = "✨ *Congratulations\\!*\n\n"
                        message += "Your invite code has been accepted\\. Welcome to TETRIX\\!"
                        
                        # Always send new message for invite code acceptance
                        await update.message.reply_text(
                            message,
                            parse_mode='MarkdownV2',
                            reply_markup=reply_markup
                        )
                    else:
                        logger.error(f"Failed to use invite code {text}")
                        await update.message.reply_text(
                            "❌ Error using invite code. Please try another one."
                        )
                else:
                    # Invalid code, let them try again
                    logger.info("Invalid code")
                    await update.message.reply_text(
                        "❌ Invalid invite code. Please try another one."
                    )
            except Exception as e:
                logger.error(f"Error processing invite code: {e}")
                await update.message.reply_text(
                    "❌ Error processing invite code. Please try again later."
                )