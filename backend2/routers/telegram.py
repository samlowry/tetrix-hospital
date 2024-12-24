from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import logging
from typing import Optional, Dict, Any
import json
import aiohttp
from pydantic import BaseModel

from models.database import get_session
from services.user_service import UserService
from services.redis_service import RedisService, UserStatus
from core.deps import get_redis
from core.config import get_settings
from locales.i18n import with_locale
from services.tetrix_service import TetrixService

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram"])

# Hardcoded for security - obscure webhook path with random suffix
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

async def send_telegram_message(chat_id: int, **kwargs) -> bool:
    """Send message via Telegram API"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, **kwargs}
    
    logger.info(f"Sending telegram message to chat_id={chat_id}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status == 200:
                logger.info(f"Message sent successfully to chat_id={chat_id}")
                return True
            logger.error(f"Error sending message to chat_id={chat_id}. Status: {response.status}")
            return False

async def answer_callback_query(callback_query_id: str) -> bool:
    """Answer callback query to remove loading state from button"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"
    data = {"callback_query_id": callback_query_id}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status == 200:
                return True
            logger.error(f"Error answering callback query: {await response.text()}")
            return False

class TelegramHandler:
    def __init__(self, user_service: UserService, redis_service: RedisService, redis: Redis, session: AsyncSession):
        self.user_service = user_service
        self.redis_service = redis_service
        self.redis = redis
        self.session = session
        # Set Redis client in user_service
        self.user_service.redis = redis

    @with_locale
    async def handle_language_selection(self, *, telegram_id: int, strings) -> bool:
        """Show language selection menu"""
        return await send_telegram_message(
            chat_id=telegram_id,
            text=strings.LANGUAGE_SELECT,
            reply_markup={
                "inline_keyboard": [
                    [
                        {"text": strings.BUTTONS["lang_ru"], "callback_data": "lang_ru"},
                        {"text": strings.BUTTONS["lang_en"], "callback_data": "lang_en"}
                    ]
                ]
            }
        )

    @with_locale
    async def handle_language_change(self, *, telegram_id: int, lang: str, strings) -> bool:
        """Handle language change"""
        # Always store in Redis for immediate effect
        redis_key = f"user:{telegram_id}:language"
        logger.debug(f"Setting language in Redis: key={redis_key}, value={lang}")
        await self.redis.set(redis_key, lang)
        
        # Verify the value was set
        saved_lang = await self.redis.get(redis_key)
        logger.debug(f"Verified language in Redis: key={redis_key}, value={saved_lang}")
        
        # If user exists in DB, update there too
        user = await self.user_service.get_user_by_telegram_id(telegram_id)
        if user:
            user.language = lang
            await self.session.commit()
            logger.debug(f"Updated language in DB for user {telegram_id}")
        else:
            logger.debug(f"User {telegram_id} not found in DB")
            
        # Show main menu with new locale
        return await self.handle_start_command(telegram_id=telegram_id)

    @with_locale
    async def handle_start_command(self, *, telegram_id: int, strings) -> bool:
        """Handle /start command"""
        # Check if user exists in DB
        user = await self.user_service.get_user_by_telegram_id(telegram_id)
        
        if not user:
            # New user - send to wallet connection
            await self.redis_service.set_status_waiting_wallet(telegram_id)
            user_lang = await self.user_service.get_user_locale(telegram_id)
            web_app_url = f"{settings.FRONTEND_URL}?lang={user_lang}"
            logger.debug(f"[WebApp] Initial URL for user {telegram_id}: {web_app_url}, language: {user_lang}")
            
            return await send_telegram_message(
                chat_id=telegram_id,
                text=strings.WELCOME_NEW_USER,
                parse_mode="Markdown",
                reply_markup={
                    "inline_keyboard": [
                        [{
                            "text": strings.BUTTONS["connect_wallet"],
                            "web_app": {"url": web_app_url}
                        }],
                        [{
                            "text": strings.BUTTONS["create_wallet"],
                            "callback_data": "create_wallet"
                        }]
                    ]
                }
            )
        
        # Check registration status
        if not user.is_fully_registered and not user.is_early_backer:
            # User with wallet but without invite code
            await self.redis_service.set_status_waiting_invite(telegram_id)
            return await send_telegram_message(
                chat_id=telegram_id,
                text=strings.WELCOME_NEED_INVITE,
                parse_mode="Markdown"
            )
            
        # Fully registered user
        await self.redis_service.set_status_registered(telegram_id)
        stats = await self.user_service.get_user_stats(user)
        
        # Get TETRIX metrics
        tetrix_service = TetrixService(self.redis, self.session)
        tetrix_metrics = await tetrix_service.get_metrics()
        
        return await send_telegram_message(
            chat_id=telegram_id,
            text=strings.WELCOME_BACK_SHORT + "\n\n" + strings.STATS_TEMPLATE.format(
                points=stats['points'],
                health_bar=tetrix_metrics['health']['bar'],
                strength_bar=tetrix_metrics['strength']['bar'],
                mood_bar=tetrix_metrics['mood']['bar'],
                emotion=tetrix_metrics['emotion'],
                holding_points=stats['points_breakdown']['holding'],
                invite_points=stats['points_breakdown']['invites'],
                early_backer_bonus=stats['points_breakdown']['early_backer_bonus']
            ),
            parse_mode="Markdown",
            reply_markup={
                "inline_keyboard": [
                    [{"text": strings.BUTTONS["refresh_stats"], "callback_data": "refresh_stats"}],
                    [{"text": strings.BUTTONS["show_invites"], "callback_data": "show_invites"}]
                ]
            }
        )

    @with_locale
    async def handle_invite_code(self, *, telegram_id: int, code: str, strings) -> bool:
        """Handle entered invite code"""
        user = await self.user_service.get_user_by_telegram_id(telegram_id)
        if not user:
            return False

        # Check code
        if await self.user_service.use_invite_code(code, user):
            await self.redis_service.set_status_registered(telegram_id)
            
            return await send_telegram_message(
                chat_id=telegram_id,
                text=strings.REGISTRATION_COMPLETE,
                parse_mode="Markdown",
                reply_markup={
                    "inline_keyboard": [[{
                        "text": strings.BUTTONS["stats"],
                        "callback_data": "check_stats"
                    }]]
                },
                disable_web_page_preview=True
            )
        else:
            return await send_telegram_message(
                chat_id=telegram_id,
                text=strings.INVALID_INVITE_CODE
            )

    @with_locale
    async def handle_callback_query(self, *, telegram_id: int, callback_data: str, strings) -> bool:
        """Handle callback requests from buttons"""
        try:
            logger.debug("Processing callback_data: %s for user %d", callback_data, telegram_id)
            
            # Handle language selection
            if callback_data.startswith("lang_"):
                lang = callback_data[5:]  # Extract language code
                return await self.handle_language_change(telegram_id=telegram_id, lang=lang, strings=strings)
            
            if callback_data == "create_wallet":
                user_lang = await self.user_service.get_user_locale(telegram_id)
                web_app_url = f"{settings.FRONTEND_URL}?lang={user_lang}"
                logger.debug(f"[WebApp] Generated URL from create_wallet for user {telegram_id}: {web_app_url}, language: {user_lang}")
                
                return await send_telegram_message(
                    chat_id=telegram_id,
                    text=strings.WALLET_CREATION_GUIDE,
                    reply_markup={
                        "inline_keyboard": [
                            [{
                                "text": strings.BUTTONS["connect_wallet"],
                                "web_app": {"url": web_app_url}
                            }],
                            [{
                                "text": strings.BUTTONS["back"],
                                "callback_data": "back_to_start"
                            }]
                        ]
                    }
                )
            
            elif callback_data == "back_to_start":
                user_lang = await self.user_service.get_user_locale(telegram_id)
                web_app_url = f"{settings.FRONTEND_URL}?lang={user_lang}"
                logger.debug(f"[WebApp] Generated URL from back_to_start for user {telegram_id}: {web_app_url}, language: {user_lang}")
                
                return await send_telegram_message(
                    chat_id=telegram_id,
                    text=strings.WELCOME_NEW_USER,
                    parse_mode="Markdown",
                    reply_markup={
                        "inline_keyboard": [
                            [{
                                "text": strings.BUTTONS["connect_wallet"],
                                "web_app": {"url": web_app_url}
                            }],
                            [{
                                "text": strings.BUTTONS["create_wallet"],
                                "callback_data": "create_wallet"
                            }]
                        ]
                    }
                )
                
            elif callback_data in ["check_stats", "show_invites", "refresh_stats", "refresh_invites"]:
                user = await self.user_service.get_user_by_telegram_id(telegram_id)
                if not user or not user.is_fully_registered:
                    logger.warning("User %d not found or not fully registered", telegram_id)
                    return False
                    
                if callback_data in ["show_invites", "refresh_invites"]:
                    codes = await self.user_service.generate_invite_codes(user)
                    code_lines = []
                    for code_info in codes:
                        code = code_info['code']
                        if code_info['status'] == 'used':
                            code_lines.append(strings.CODE_FORMATTING["used"].format(code))
                        else:
                            code_lines.append(strings.CODE_FORMATTING["active"].format(code))
                    
                    while len(code_lines) < user.max_invite_slots:
                        code_lines.append(strings.INVITE_CODES_EMPTY)
                    
                    return await send_telegram_message(
                        chat_id=telegram_id,
                        text=(
                            f"{strings.INVITE_CODES_TITLE}\n\n" +
                            "\n".join(code_lines) +
                            f"\n\n{strings.INVITE_CODES_REWARD}"
                        ),
                        parse_mode="Markdown",
                        reply_markup={
                            "inline_keyboard": [
                                [{"text": strings.BUTTONS["refresh_invites"], "callback_data": "refresh_invites"}],
                                [{"text": strings.BUTTONS["back_to_stats"], "callback_data": "check_stats"}]
                            ]
                        }
                    )
                else:
                    stats = await self.user_service.get_user_stats(user)
                    tetrix_service = TetrixService(self.redis, self.session)
                    tetrix_metrics = await tetrix_service.get_metrics()
                    
                    return await send_telegram_message(
                        chat_id=telegram_id,
                        text=strings.STATS_TEMPLATE.format(
                            points=stats['points'],
                            health_bar=tetrix_metrics['health']['bar'],
                            strength_bar=tetrix_metrics['strength']['bar'],
                            mood_bar=tetrix_metrics['mood']['bar'],
                            emotion=tetrix_metrics['emotion'],
                            holding_points=stats['points_breakdown']['holding'],
                            invite_points=stats['points_breakdown']['invites'],
                            early_backer_bonus=stats['points_breakdown']['early_backer_bonus']
                        ),
                        parse_mode="Markdown",
                        reply_markup={
                            "inline_keyboard": [
                                [{"text": strings.BUTTONS["refresh_stats"], "callback_data": "refresh_stats"}],
                                [{"text": strings.BUTTONS["show_invites"], "callback_data": "show_invites"}]
                            ]
                        }
                    )
            
            logger.warning("Unknown callback_data: %s", callback_data)
            return False
            
        except Exception as e:
            logger.error("Error in handle_callback_query: %s", str(e), exc_info=True)
            return False

@router.post(WEBHOOK_PATH)
async def telegram_webhook(
    update: Dict[str, Any],
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis)
):
    """Handle incoming updates from Telegram"""
    try:
        logger.debug("Received update: %s", update)
        
        user_service = UserService(session)
        redis_service = RedisService(redis)
        handler = TelegramHandler(user_service, redis_service, redis, session)
        
        # Get data from update
        message = update.get("message", {})
        callback_query = update.get("callback_query", {})
        
        if message:
            telegram_id = message.get("from", {}).get("id")
            if not telegram_id:
                logger.warning("No telegram_id in message update")
                return {"ok": False}
            
            text = message.get("text", "")
            logger.info("Received message from %d: %s", telegram_id, text)
            
            # Handle /start command
            if text == "/start":
                success = await handler.handle_start_command(telegram_id=telegram_id)
                return {"ok": success}
            
            # Handle /language command
            if text == "/language":
                success = await handler.handle_language_selection(telegram_id=telegram_id)
                return {"ok": success}
            
            # Check user status
            status = await redis_service.get_user_status_value(telegram_id)
            logger.debug("User %d status: %s", telegram_id, status)
            
            # If waiting for invite code
            if status == UserStatus.WAITING_INVITE.value and text:
                success = await handler.handle_invite_code(telegram_id=telegram_id, code=text)
                return {"ok": success}
            
        elif callback_query:
            telegram_id = callback_query.get("from", {}).get("id")
            callback_query_id = callback_query.get("id")
            callback_data = callback_query.get("data", "")
            
            if not telegram_id or not callback_query_id:
                logger.warning("Missing telegram_id or callback_query_id in callback_query")
                return {"ok": False}
            
            logger.info("Received callback_query from %d: %s", telegram_id, callback_data)
            
            # Answer callback query immediately
            try:
                await answer_callback_query(callback_query_id)
            except Exception as e:
                logger.error("Error answering callback query: %s", str(e))
                # Continue processing even if answering fails
            
            # Check if user just registered
            user = await user_service.get_user_by_telegram_id(telegram_id)
            if user and not user.is_fully_registered:
                logger.info("User %d registered with early_backer=%s", telegram_id, user.is_early_backer)
                if user.is_early_backer:
                    # Early backer - already welcomed in /proof endpoint
                    await redis_service.set_status_registered(telegram_id)
                    return {"ok": True}
                else:
                    # Regular user - request invite code
                    await redis_service.set_status_waiting_invite(telegram_id)
                    await handler.handle_start_command(telegram_id=telegram_id)
                return {"ok": True}
            
            # Handle callback requests
            success = await handler.handle_callback_query(telegram_id=telegram_id, callback_data=callback_data)
            return {"ok": success}
        
        return {"ok": True}
        
    except Exception as e:
        logger.error("Error processing update: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await session.close()