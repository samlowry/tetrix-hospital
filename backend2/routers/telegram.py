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
from locales.ru import *  # Import all messages

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram"])

# Hardcoded for security - obscure webhook path with random suffix
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

async def setup_webhook() -> bool:
    """Set up webhook for bot during application startup"""
    webhook_url = f"{settings.BACKEND_URL}{WEBHOOK_PATH}"
    
    async with aiohttp.ClientSession() as session:
        # Check current webhook
        async with session.get(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getWebhookInfo"
        ) as response:
            info = await response.json()
            if info.get("ok"):
                current_url = info["result"].get("url", "")
                if current_url == webhook_url:
                    logger.info(f"Webhook already set to {webhook_url}")
                    return True
    
        # Set new webhook
        async with session.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook",
            json={
                "url": webhook_url,
                "drop_pending_updates": True
            }
        ) as response:
            result = await response.json()
            if not result.get("ok"):
                logger.error(f"Failed to set webhook: {result.get('description')}")
                return False
            logger.info(f"Webhook set successfully to {webhook_url}")
            return True

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

async def handle_start_command(
    telegram_id: int,
    user_service: UserService,
    redis_service: RedisService
) -> bool:
    """Handle /start command"""
    # Check if user exists in DB
    user = await user_service.get_user_by_telegram_id(telegram_id)
    
    if not user:
        # New user - send to wallet connection
        await redis_service.set_status_waiting_wallet(telegram_id)
        return await send_telegram_message(
            telegram_id,
            text=WELCOME_NEW_USER,
            parse_mode="Markdown",
            reply_markup={
                "inline_keyboard": [
                    [{
                        "text": BUTTONS["connect_wallet"],
                        "web_app": {"url": settings.FRONTEND_URL}
                    }],
                    [{
                        "text": BUTTONS["create_wallet"],
                        "callback_data": "create_wallet"
                    }]
                ]
            }
        )
    
    # Check registration status
    if not user.is_fully_registered and not user.is_early_backer:
        # User with wallet but without invite code
        await redis_service.set_status_waiting_invite(telegram_id)
        return await send_telegram_message(
            telegram_id,
            text=WELCOME_NEED_INVITE,
            parse_mode="Markdown"
        )
    
    # Fully registered user
    await redis_service.set_status_registered(telegram_id)
    stats = await user_service.get_user_stats(user)
    available_invites = await user_service.get_available_invites(user)
    
    return await send_telegram_message(
        telegram_id,
        text=WELCOME_BACK.format(
            progress_bar="[" + "█" + "░" * 19 + "] 1.0%",
            points=stats['points'],
            total_invites=stats['total_invites'],
            available_slots=available_invites
        ),
        parse_mode="Markdown",
        reply_markup={
            "inline_keyboard": [
                [{"text": BUTTONS["show_invites"], "callback_data": "show_invites"}],
                [{"text": BUTTONS["stats"], "callback_data": "check_stats"}]
            ]
        }
    )

async def handle_invite_code(
    telegram_id: int,
    code: str,
    user_service: UserService,
    redis_service: RedisService
) -> bool:
    """Handle entered invite code"""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        return False

    # Check code
    if await user_service.use_invite_code(code, user):
        await redis_service.set_status_registered(telegram_id)
        
        # Send only registration complete message with button
        return await send_telegram_message(
            telegram_id,
            text=REGISTRATION_COMPLETE,
            parse_mode="Markdown",
            reply_markup={
                "inline_keyboard": [[{
                    "text": BUTTONS["stats"],
                    "callback_data": "check_stats"
                }]]
            },
            disable_web_page_preview=True
        )
    else:
        return await send_telegram_message(
            telegram_id,
            text=INVALID_INVITE_CODE
        )

async def handle_callback_query(
    telegram_id: int,
    callback_data: str,
    user_service: UserService,
    redis_service: RedisService
) -> bool:
    """Handle callback requests from buttons"""
    if callback_data == "create_wallet":
        return await send_telegram_message(
            telegram_id,
            text=WALLET_CREATION_GUIDE,
            reply_markup={
                "inline_keyboard": [
                    [{
                        "text": BUTTONS["connect_wallet"],
                        "web_app": {"url": settings.FRONTEND_URL}
                    }],
                    [{
                        "text": BUTTONS["back"],
                        "callback_data": "back_to_start"
                    }]
                ]
            }
        )
    
    elif callback_data == "back_to_start":
        # Return to initial menu
        return await send_telegram_message(
            telegram_id,
            text=WELCOME_NEW_USER,
            parse_mode="Markdown",
            reply_markup={
                "inline_keyboard": [
                    [{
                        "text": BUTTONS["connect_wallet"],
                        "web_app": {"url": settings.FRONTEND_URL}
                    }],
                    [{
                        "text": BUTTONS["create_wallet"],
                        "callback_data": "create_wallet"
                    }]
                ]
            }
        )
    
    elif callback_data in ["check_stats", "show_invites"]:
        user = await user_service.get_user_by_telegram_id(telegram_id)
        if not user or not user.is_fully_registered:
            return False
            
        if callback_data == "show_invites":
            codes = await user_service.generate_invite_codes(user)
            code_lines = []
            for code_info in codes:
                # Escape special characters for Markdown V2
                code = code_info['code'].replace('-', '\\-')
                if code_info['status'] == 'used':
                    code_lines.append(f"~{code}~\n")
                else:
                    code_lines.append(f"```\n{code}\n```")
            
            while len(code_lines) < user.max_invite_slots:
                code_lines.append(INVITE_CODES_EMPTY)
            
            return await send_telegram_message(
                telegram_id,
                text=(
                    f"{INVITE_CODES_TITLE}\n\n" +
                    "\n".join(code_lines) +
                    f"\n\n{INVITE_CODES_REWARD}"
                ),
                parse_mode="MarkdownV2",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": BUTTONS["refresh_invites"], "callback_data": "show_invites"}],
                        [{"text": BUTTONS["back_to_stats"], "callback_data": "check_stats"}]
                    ]
                }
            )
        else:
            stats = await user_service.get_user_stats(user)
            available_invites = await user_service.get_available_invites(user)
            
            return await send_telegram_message(
                telegram_id,
                text=STATS_TEMPLATE.format(
                    points=stats['points'],
                    progress_bar="[" + "█" + "░" * 19 + "] 1.0%",
                    holding_points=stats['points_breakdown']['holding'],
                    invite_points=stats['points_breakdown']['invites'],
                    early_backer_bonus=stats['points_breakdown']['early_backer_bonus']
                ),
                parse_mode="Markdown",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": BUTTONS["refresh_stats"], "callback_data": "check_stats"}],
                        [{"text": BUTTONS["show_invites"], "callback_data": "show_invites"}]
                    ]
                }
            )
    
    return False

@router.post(WEBHOOK_PATH)
async def telegram_webhook(
    update: Dict[str, Any],
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis)
):
    """Handle incoming updates from Telegram"""
    try:
        user_service = UserService(session)
        redis_service = RedisService(redis)
        
        # Get data from update
        message = update.get("message", {})
        callback_query = update.get("callback_query", {})
        
        if message:
            telegram_id = message.get("from", {}).get("id")
            if not telegram_id:
                return {"ok": False}
            
            text = message.get("text", "")
            
            # Handle /start command
            if text == "/start":
                success = await handle_start_command(telegram_id, user_service, redis_service)
                return {"ok": success}
            
            # Check user status
            status = await redis_service.get_user_status_value(telegram_id)
            
            # If waiting for invite code
            if status == UserStatus.WAITING_INVITE.value and text:
                success = await handle_invite_code(telegram_id, text, user_service, redis_service)
                return {"ok": success}
        
        elif callback_query:
            telegram_id = callback_query.get("from", {}).get("id")
            callback_query_id = callback_query.get("id")
            if not telegram_id or not callback_query_id:
                return {"ok": False}
            
            # Answer callback query immediately
            await answer_callback_query(callback_query_id)
            
            # Check if user just registered
            user = await user_service.get_user_by_telegram_id(telegram_id)
            if user and not user.is_fully_registered:
                logger.info(f"User {telegram_id} registered with early_backer={user.is_early_backer}")
                if user.is_early_backer:
                    # Early backer - already welcomed in /proof endpoint
                    await redis_service.set_status_registered(telegram_id)
                    return {"ok": True}
                else:
                    # Regular user - request invite code
                    await redis_service.set_status_waiting_invite(telegram_id)
                    await send_telegram_message(
                        telegram_id,
                        text=WELCOME_NEED_INVITE,
                        parse_mode="Markdown"
                    )
                return {"ok": True}
            
            # Handle callback requests
            success = await handle_callback_query(
                telegram_id,
                callback_query.get("data", ""),
                user_service,
                redis_service
            )
            return {"ok": success}
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await session.close()