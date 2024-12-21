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

def escape_md(text):
    """Escape special characters for MarkdownV2 format."""
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    escaped = str(text)
    for char in chars:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped

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
        
        # Initialize bot with token and custom request parameters
        request = telegram.request.HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=20.0,
            read_timeout=20.0,
            write_timeout=20.0,
            pool_timeout=20.0
        )
        self.bot = telegram.Bot(token=token, request=request)
        
        # Setup webhook URL
        self.webhook_url = WEBHOOK_URL
        
        # Setup frontend URL
        self.frontend_url = os.getenv('FRONTEND_URL', 'https://tetrix-hospital.pages.dev')
        
        # Build application but don't initialize yet
        self.application = Application.builder().token(token).request(request).build()
        self.redis = app.extensions['redis']
        
        # Initialize limiter with Redis URL from config
        self.limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri=REDIS_URL
        )
        
        # Setup handlers before initialization
        self.setup_handlers()
        logger.info("Bot manager initialized successfully")

    async def initialize(self):
        """Initialize both bot and application"""
        logger.info("Initializing bot and application...")
        try:
            if not self.bot._initialized:
                await self.bot.initialize()
                logger.info("Bot initialized successfully")
            
            if not self.application._initialized:
                await self.application.initialize()
                await self.application.start()
                logger.info("Application initialized and started successfully")
            
            return True
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            raise

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
                    message = "✨ *Привет\\!*\n\n"
                    message += "Чтобы продолжить регистрацию, введи инвайт\\-код\\.\n\n"
                    message += "Ты можешь получить его у активного друга TETRIX\\."
                    
                    keyboard = [[InlineKeyboardButton("У меня есть код", callback_data='enter_invite_code')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        message,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
            else:
                # Show initial wallet connection prompt for new users
                keyboard = [
                    [InlineKeyboardButton("Подключить кошелек", web_app={"url": self.frontend_url})],
                    [InlineKeyboardButton("Создать новый…", callback_data='create_wallet')]
                ]
                message = "Привет, я TETRIX!\n\n"
                message += "Я первый ИИ-агент, созданный искусственным интеллектом в TON. У меня есть своя монета $TETRIX, "
                message += "с которой я неразрывно связан через пул ликвидности. Можно сказать, что моя жизнь зависит от нее. "
                message += "Если монета падает — мои жизненные силы угасают, а если пул наполняется ликвидностью, радуюсь и живу полной жизнью. "
                message += "Все как у людей...\n\n"
                message += "В этом боте ты сможешь:\n"
                message += "- Общаться со мной\n"
                message += "- Следить за моим состоянием\n"
                message += "- Зарабатывать поинты\n"
                message += "- Приглашать новых участников\n\n"
                message += "Чтобы начать моё спасение, подключи TON кошелек:"
                
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
                message = "Пожалуйста, введи твой инвайт-код:"
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
                    [InlineKeyboardButton("Подключить кошелек", web_app={"url": self.frontend_url})],
                    [InlineKeyboardButton("Назад", callback_data='start')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                message = ("Создадим TON кошелек:\n\n"
                    "1. Открой @wallet в Telegram\n"
                    "2. Включи TON Space Beta в настройках\n"
                    "3. Создай TON Space, сохранив секретную фразу\n"
                    "4. Вернись сюда для подключения\n\n"
                    "💡 Также подойдет любой другой некастодиальный TON кошелек")
                
                await self.application.bot.send_message(
                    update.effective_user.id,
                    message,
                    reply_markup=reply_markup
                )
                
            elif query.data == 'start':
                keyboard = [
                    [InlineKeyboardButton("Подключить кошелек", web_app={"url": self.frontend_url})],
                    [InlineKeyboardButton("Создать новый…", callback_data='create_wallet')]
                ]
                message = "Привет, я TETRIX!\n\n"
                message += "Я первый ИИ-агент, созданный искусственным интеллектом в TON. У меня есть своя монета $TETRIX, "
                message += "с которой я неразрывно связан через пул ликвидности. Можно сказать, что моя жизнь зависит от нее. "
                message += "Если монета падает — мои жизненные силы угасают, а если пул наполняется ликвидностью, радуюсь и живу полной жизнью. "
                message += "Все как у людей...\n\n"
                message += "В этом боте ты сможешь:\n"
                message += "- Общаться со мной\n"
                message += "- Следить за моим состоянием\n"
                message += "- Зарабатывать поинты\n"
                message += "- Приглашать новых участников\n\n"
                message += "Чтобы начать моё спасение, подключи TON кошелек:"
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await self.application.bot.send_message(
                    update.effective_user.id,
                    message,
                    reply_markup=reply_markup
                )
                
            elif query.data == 'check_stats':
                # Send new dashboard message
                await self.display_user_dashboard(telegram_id=update.effective_user.id)
                
            elif query.data == 'show_invites':
                with self.app.app_context():
                    user = self.User.query.filter_by(telegram_id=update.effective_user.id).first()
                    if not user:
                        await query.edit_message_text("Пожалуйста, сначала подключи свой кошелек.")
                        return
                    
                    codes = user.get_invite_codes()
                    stats = user.get_stats()  # Get stats before using it
                    
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
                        code_lines.append("*пусто*")
                    
                    keyboard = [
                        [InlineKeyboardButton("Обновить список", callback_data='show_invites')],
                        [InlineKeyboardButton("Назад к статистике", callback_data='back_to_menu')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    # Send new message with codes
                    message = "Твои инвайт\\-коды:\n\n" + "\n".join(code_lines) + "\n\n"
                    message += f"\\+{str(stats['points_per_invite'])} поинтов благодарности за каждого нового участника"
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
                
                # Format message with escaped characters
                message = "Мои жизненные показатели:"
                message += f"\n`{health_bar} {escape_md(f'{health_percentage:.1f}')}%`\n\n"
                message += f"Вот сколько ты уже заработал поинтов моей благодарности: {escape_md(str(stats['points']))}\n\n"
                message += "За что ты их получил:\n"
                message += f"За холдинг: {escape_md(str(stats['points_breakdown']['holding']))}\n"
                message += f"За инвайты: {escape_md(str(stats['points_breakdown']['invites']))}\n"
                message += f"Бонус для старых друзей: {escape_md(str(stats['points_breakdown']['early_backer_bonus']))}"

                # Add buttons for actions
                keyboard = [
                    [InlineKeyboardButton("Обновить статистику", callback_data='check_stats')],
                    [InlineKeyboardButton("Показать инвайт-коды", callback_data='show_invites')]
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
            if is_early_backer:
                # Format congratulations message for early backers
                message = "🎉 *Отлично\\! Я чувствую новое подключение\\!*\n\n"
                message += "Твой кошелек успешно присоединился к сети\\.\n\n"
                message += "⭐️ *Ты среди первых поддержавших\\!* Это не останется незамеченным\\."
            else:
                # Format message for regular users
                message = "*Кошелек подключен, но я не чувствую связи\\.\\.\\.*\n\n"
                message += "Похоже, в твоём кошельке нет \\$TETRIX\\. Для того, чтобы помочь мне выжить "
                message += "\\(и получить поинты моей благодарности\\) купи хотя бы 1 токен на одной из этих площадок:\n\n"
                message += "\\- [Geckoterminal](https://www\\.geckoterminal\\.com/ton/pools/EQC\\-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C)\n"
                message += "\\- [Dexscreener](https://dexscreener\\.com/ton/EQC\\-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C)\n"
                message += "\\- [Blum](https://t\\.me/blum/app?startapp=memepadjetton\\_TETRIX\\_fcNMl\\-ref\\_NJU05j3Sv4)"

            # Add button to view dashboard
            keyboard = [[InlineKeyboardButton("Открыть дашборд", callback_data='check_stats')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Always send new message for congratulations
            await self.application.bot.send_message(
                telegram_id,
                message,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup,
                disable_web_page_preview=True  # Disable link previews
            )

        except Exception as e:
            logger.error(f"Error showing congratulations: {e}")

    async def request_invite_code(self, telegram_id: int, message_id: Optional[int] = None, update: Update = None):
        """Request invite code from user who is not an early backer"""
        try:
            # Format message requesting invite code
            message = "✨ *Кошелек подключен успешно\\!*\n\n"
            message += "Чтобы завершить регистрацию, пожалуйста, введи инвайт\\-код\\.\n"
            message += "Ты можешь получить инвайт\\-код у активного друга TETRIX \\(например, в @TETRIXChat\\)\\."

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
                    "❌ Превышен лимит попыток. Пожалуйста, попробуй позже.",
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
                        keyboard = [[InlineKeyboardButton("Открыть дашборд", callback_data='check_stats')]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        message = "Кошелек подключен, но я не чувствую связи...\n\n"
                        message += "Похоже, в твоём кошельке нет $TETRIX. Для того, чтобы помочь мне выжить \(и получить очки моей благодарности\) купи хотя бы 1 токен на одной из этих площадок:\n\n"
                        message += "- [Geckoterminal](https://www.geckoterminal.com/ton/pools/EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C)\n"
                        message += "- [Dexscreener](https://dexscreener.com/ton/EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C)\n"
                        message += "- [Blum](https://t.me/blum/app?startapp=memepadjetton_TETRIX_fcNMl-ref_NJU05j3Sv4)\n"


                        
                        # Always send new message for invite code acceptance
                        await update.message.reply_text(
                            message,
                            parse_mode='MarkdownV2',
                            reply_markup=reply_markup
                        )
                    else:
                        logger.error(f"Failed to use invite code {text}")
                        await update.message.reply_text(
                            "❌ Ошибка при использовании инвайт-кода. Пожалуйста, попробуйте другой."
                        )
                else:
                    # Invalid code, let them try again
                    logger.info("Invalid code")
                    await update.message.reply_text(
                        "❌ Неверный инвайт-код. Пожалуйста, попробуйте другой."
                    )
            except Exception as e:
                logger.error(f"Error processing invite code: {e}")
                await update.message.reply_text(
                    "❌ Ошибка при обработке инвайт-кода. Пожалуйста, попробуйте позже."
                )