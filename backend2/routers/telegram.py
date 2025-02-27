from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import logging
from typing import Optional, Dict, Any
import json
import aiohttp
from pydantic import BaseModel
from datetime import datetime

from models.database import get_session
from services.user_service import UserService, get_telegram_info
from services.redis_service import RedisService, UserStatus
from core.deps import get_redis
from core.config import get_settings
from locales.language_utils import with_locale, LANGUAGE_MODULES
from services.tetrix_service import TetrixService
from core.cache import CacheKeys
from locales import ru, en

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram"])

# Hardcoded for security - obscure webhook path with random suffix
WEBHOOK_PATH = '/telegram-webhook9eu3f3843ry9834843'

async def send_telegram_message(telegram_id: int, **kwargs) -> bool:
    """Send message via Telegram API"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": telegram_id, **kwargs}
    
    logger.info(f"Sending telegram message to chat_id={telegram_id}")
    logger.debug(f"Message data: {data}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status == 200:
                logger.info(f"Message sent successfully to chat_id={telegram_id}")
                return True
            logger.error(f"Error sending message to chat_id={telegram_id}. Status: {response.status}")
            response_text = await response.text()
            logger.error(f"Response text: {response_text}")
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

def get_visual_width(s: str) -> int:
    """Calculate visual width of string, counting wide chars as 2 positions"""
    width = 0
    for char in s:
        # Count emoji, circled letters and other wide chars as 2 positions
        if ord(char) > 0x1FFF:  # Beyond Basic Latin and Latin-1 Supplement
            width += 2
        else:
            width += 1
    return width

def trim_to_visual_width(s: str, max_width: int) -> str:
    """Trim string to specified visual width, adding ellipsis if needed"""
    if get_visual_width(s) <= max_width:
        return s
        
    result = ""
    current_width = 0
    
    for char in s:
        char_width = 2 if ord(char) > 0x1FFF else 1
        if current_width + char_width + 1 > max_width:  # +1 for ellipsis
            return result + "…"
        current_width += char_width
        result += char
        
    return result

async def split_and_send_message(telegram_id: int, text: str, **kwargs) -> bool:
    """Split long message and send parts"""
    MAX_LENGTH = 4000  # Leave some room for formatting
    
    # If message is short enough, send as is
    if len(text) <= MAX_LENGTH:
        return await send_telegram_message(telegram_id=telegram_id, text=text, **kwargs)
    
    # Split message into parts
    parts = []
    while text:
        if len(text) <= MAX_LENGTH:
            parts.append(text)
            break
            
        # Find last newline before MAX_LENGTH
        split_pos = text.rfind('\n', 0, MAX_LENGTH)
        if split_pos == -1:
            # If no newline found, split at MAX_LENGTH
            split_pos = MAX_LENGTH
            
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    
    # Send each part
    success = True
    for i, part in enumerate(parts, 1):
        part_text = f"Part {i}/{len(parts)}:\n\n{part}"
        if not await send_telegram_message(telegram_id=telegram_id, text=part_text, **kwargs):
            success = False
            
    return success

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
            telegram_id=telegram_id,
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
    async def handle_language_change(self, telegram_id: int, language: str, strings) -> bool:
        """Handle language change request"""
        try:
            # Update language in cache and DB
            await self.user_service.set_user_language(telegram_id, language)
            
            # Get strings for the new language
            strings = LANGUAGE_MODULES.get(language, ru)
            
            # Get user
            user = await self.user_service.get_user_by_telegram_id(telegram_id)
            
            if user.registration_phase == 'preregistered':
                # Show path selection menu
                return await send_telegram_message(
                    telegram_id=telegram_id,
                    text=strings.CHOOSE_PATH,
                    reply_markup={
                        "inline_keyboard": [
                            [{"text": strings.BUTTONS["be_friend"], "callback_data": "path_friend"}],
                            [{"text": strings.BUTTONS["get_job"], "callback_data": "path_job"}]
                        ]
                    }
                )
            
            # For all other phases - standard logic
            return await self.handle_start_command(telegram_id=telegram_id, strings=strings)
            
        except Exception as e:
            logger.error(f"Failed to change language for user {telegram_id}: {e}")
            return False

    @with_locale
    async def handle_start_command(self, *, telegram_id: int, strings, is_threads_campaign: bool = False) -> bool:
        """Handle /start command"""
        try:
            # Check if user exists in DB
            user = await self.user_service.get_user_by_telegram_id(telegram_id)
            logger.info(f"[TELEGRAM] User lookup for {telegram_id}: {'found' if user else 'not found'}")
            
            if not user:
                # Create new user in pre-registration state
                user = await self.user_service.create_user(
                    telegram_id=telegram_id,
                    wallet_address=None,
                    is_threads_campaign=is_threads_campaign
                )
                logger.info(f"[TELEGRAM] Created new user {telegram_id} in {'threads_job_campaign' if is_threads_campaign else 'preregistered'} state")
            
            # Check if language is set - ALWAYS DO THIS FIRST
            lang = await self.user_service.get_user_language(telegram_id)
            logger.info(f"[TELEGRAM] User {telegram_id} language: {lang}")
            
            if not lang:
                logger.debug(f"[TELEGRAM] No language set for user {telegram_id}, showing language selection")
                return await self.handle_language_selection(telegram_id=telegram_id, strings=strings)

            # Now handle different registration phases
            if user.registration_phase == 'threads_job_campaign':
                # Check if user already started threads campaign
                campaign_entry = await self.user_service.get_threads_campaign_entry(telegram_id)
                if campaign_entry:
                    if campaign_entry.analysis_report:
                        # If user already has analysis report - show it again
                        logger.info(f"[TELEGRAM] Showing existing analysis for user {telegram_id}")
                        try:
                            report = json.loads(campaign_entry.analysis_report)
                            return await split_and_send_message(
                                telegram_id=telegram_id,
                                text=strings.THREADS_ANALYSIS_COMPLETE.format(
                                    analysis_text=self.user_service.llm_service.format_report(report)
                                ),
                                parse_mode="HTML",
                                disable_web_page_preview=True
                            )
                        except Exception as e:
                            logger.error(f"Error showing analysis: {e}")
                        return True
                    elif campaign_entry.posts_json:
                        # If we have posts but no analysis - resume analysis
                        logger.info(f"[TELEGRAM] Resuming analysis for user {telegram_id}")
                        await send_telegram_message(
                            telegram_id=telegram_id,
                            text=strings.THREADS_ANALYZING,
                            parse_mode="Markdown"
                        )
                        # Start analysis
                        success = await self.analyze_threads_profile(telegram_id=telegram_id, strings=strings)
                        return success
                    elif campaign_entry.threads_user_id:
                        # If we have profile but no posts - fetch posts and analyze
                        logger.info(f"[TELEGRAM] Starting analysis for existing profile of user {telegram_id}")
                        await send_telegram_message(
                            telegram_id=telegram_id,
                            text=strings.THREADS_ANALYZING,
                            parse_mode="Markdown"
                        )
                        success = await self.analyze_threads_profile(telegram_id=telegram_id, strings=strings)
                        return success
                    else:
                        # If we have campaign entry but no profile info - something went wrong, request profile again
                        logger.warning(f"[TELEGRAM] Campaign entry without profile info for user {telegram_id}")
                        return await send_telegram_message(
                            telegram_id=telegram_id,
                            text=strings.THREADS_PROFILE_REQUEST,
                            parse_mode="HTML"
                        )
                # If no campaign entry - request threads profile
                return await send_telegram_message(
                    telegram_id=telegram_id,
                    text=strings.THREADS_PROFILE_REQUEST,
                    parse_mode="HTML"
                )
                
            # If user exists but not fully registered
            if user.registration_phase == 'preregistered':
                # New user - send to wallet connection
                await self.redis_service.set_status_waiting_wallet(telegram_id)
                user_lang = await self.user_service.get_user_language(telegram_id) or 'ru'
                web_app_url = f"{settings.FRONTEND_URL}?lang={user_lang}"
                logger.debug(f"[TELEGRAM] Initial URL for user {telegram_id}: {web_app_url}, language: {user_lang}")
                
                return await send_telegram_message(
                    telegram_id=telegram_id,
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
            if user.registration_phase == 'pending':
                # User with wallet but without invite code
                await self.redis_service.set_status_waiting_invite(telegram_id)
                return await send_telegram_message(
                    telegram_id=telegram_id,
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
                telegram_id=telegram_id,
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
                parse_mode="HTML",
                reply_markup={
                    "inline_keyboard": [
                        [{"text": strings.BUTTONS["refresh_stats"], "callback_data": "refresh_stats"}],
                        [{"text": strings.BUTTONS["show_invites"], "callback_data": "show_invites"}],
                        [{"text": strings.BUTTONS["leaderboard"], "callback_data": "leaderboard"}]
                    ]
                }
            )
        except Exception as e:
            logger.error(f"[TELEGRAM] Error in handle_start_command for {telegram_id}: {str(e)}", exc_info=True)
            return False

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
                telegram_id=telegram_id,
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
                telegram_id=telegram_id,
                text=strings.INVALID_INVITE_CODE
            )

    @with_locale
    async def handle_callback_query(self, *, telegram_id: int, callback_data: str, strings) -> bool:
        """Handle callback requests from buttons"""
        try:
            logger.debug("Processing callback_data: %s for user %d", callback_data, telegram_id)
            
            # Get user once at the start
            user = await self.user_service.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.warning("User %d not found", telegram_id)
                return False
            
            # Use user's language
            user_lang = user.language or 'ru'
            
            # Handle language selection
            if callback_data.startswith("lang_"):
                lang = callback_data[5:]  # Extract language code
                return await self.handle_language_change(telegram_id=telegram_id, language=lang, strings=strings)
            
            if callback_data == "path_friend":
                # Show standard wallet connection menu
                return await self.handle_start_command(telegram_id=telegram_id, strings=strings)
                
            elif callback_data == "path_job":
                # Change phase and show threads profile request
                await self.user_service.update_user(user, registration_phase='threads_job_campaign')
                return await self.handle_start_command(telegram_id=telegram_id, strings=strings)
                
            if callback_data == "create_wallet":
                web_app_url = f"{settings.FRONTEND_URL}?lang={user_lang}"
                logger.debug(f"[WebApp] Generated URL from create_wallet for user {telegram_id}: {web_app_url}, language: {user_lang}")
                
                return await send_telegram_message(
                    telegram_id=telegram_id,
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
                web_app_url = f"{settings.FRONTEND_URL}?lang={user_lang}"
                logger.debug(f"[WebApp] Generated URL from back_to_start for user {telegram_id}: {web_app_url}, language: {user_lang}")
                
                return await send_telegram_message(
                    telegram_id=telegram_id,
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
                
            elif callback_data in ["check_stats", "show_invites", "refresh_stats", "refresh_invites"] or callback_data.startswith("leaderboard") or callback_data == "noop":
                if user.registration_phase != 'active':
                    logger.warning("User %d not active", telegram_id)
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
                        telegram_id=telegram_id,
                        text=(
                            f"{strings.INVITE_CODES_TITLE}\n\n" +
                            "\n".join(code_lines) +
                            f"\n\n{strings.INVITE_CODES_REWARD}"
                        ),
                        parse_mode="HTML",
                        reply_markup={
                            "inline_keyboard": [
                                [{"text": strings.BUTTONS["refresh_invites"], "callback_data": "refresh_invites"}],
                                [{"text": strings.BUTTONS["back_to_stats"], "callback_data": "check_stats"}]
                            ]
                        }
                    )
                elif callback_data.startswith("leaderboard"):
                    # Parse page from callback data
                    parts = callback_data.split(":")
                    current_page = 0
                    
                    if len(parts) > 1:
                        # Extract current page from the navigation command
                        if parts[1] == "next":
                            # Extract page number from the button text
                            if len(parts) > 2:
                                current_page = int(parts[2])
                            current_page += 1
                        elif parts[1] == "prev":
                            if len(parts) > 2:
                                current_page = int(parts[2])
                            current_page -= 1
                        elif parts[1] == "page" and len(parts) > 2:
                            # Keep the same page for refresh
                            current_page = int(parts[2])
                    elif callback_data == "noop":
                        # For old messages, treat noop as refresh of current page
                        current_page = 0
                    
                    # Get leaderboard data from cache
                    leaderboard = await self.user_service.get_leaderboard_snapshot()
                    user_position = await self.user_service.get_user_leaderboard_position(user)
                    user_rank = await self.user_service.get_user_rank(user)
                    user_stats = await self.user_service.get_user_stats(user)
                    
                    # Calculate start and end indices based on page
                    total_users = len(leaderboard)
                    logger.debug(f"Total users in leaderboard: {total_users}")
                    
                    start_idx = 10 * current_page
                    end_idx = min(start_idx + 10, total_users)
                    
                    # Adjust indices if they're out of bounds
                    if start_idx >= total_users:
                        start_idx = max(0, total_users - 10)
                        end_idx = total_users
                        current_page = start_idx // 10
                    
                    logger.debug(f"Page {current_page}, indices: {start_idx}-{end_idx}")
                    
                    # Format title with user's position
                    message = strings.LEADERBOARD_TITLE.format(
                        position=user_position,
                        points=user_stats['points'],
                        rank=strings.RANKS[user_rank]
                    )
                    
                    # Single pre block for the entire list
                    message += "<pre>"
                    
                    # Add paginated lines
                    for i, leader in enumerate(leaderboard[start_idx:end_idx], start_idx + 1):
                        name = leader['name']
                        # Trim name considering visual width
                        name = trim_to_visual_width(name, 16)
                            
                        # Format with exact spacing (16 visual positions)
                        visual_padding = 16 - get_visual_width(name)
                        
                        # Add pointer emoji only to user's line
                        pointer = " 👈" if leader['telegram_id'] == telegram_id else ""
                        line = f"{i:2d}. {name}{' ' * visual_padding}{leader['points']:5d}{pointer}\n"
                        
                        # Add line with or without bold formatting
                        if leader['telegram_id'] == telegram_id:
                            message += f"<b>{line}</b>"
                        else:
                            message += line
                            
                    # Close the pre block
                    message += "</pre>"
                    
                    # Add footer with signature
                    message += strings.LEADERBOARD_FOOTER
                    
                    # Calculate pagination buttons
                    page_info = strings.BUTTONS["leaderboard_page"].format(
                        start=start_idx + 1,
                        end=end_idx,
                        total=total_users
                    )
                    logger.debug(f"Page info: {page_info}, start_idx: {start_idx}, end_idx: {end_idx}")
                    
                    # Create navigation buttons
                    keyboard = []
                    nav_row = []
                    
                    # Add Prev button if not on first page
                    if start_idx > 0:
                        logger.debug("Adding Prev button")
                        nav_row.append({"text": strings.BUTTONS["leaderboard_prev"], 
                                      "callback_data": f"leaderboard:prev:{current_page}"})
                    
                    # Add current page info (now as refresh button)
                    nav_row.append({"text": page_info, 
                                  "callback_data": f"leaderboard:page:{current_page}"})
                    
                    # Add Next button if there are more users
                    if end_idx < total_users:
                        logger.debug(f"Adding Next button (end_idx: {end_idx} < total_users: {total_users})")
                        nav_row.append({"text": strings.BUTTONS["leaderboard_next"], 
                                      "callback_data": f"leaderboard:next:{current_page}"})
                    
                    keyboard.append(nav_row)
                    keyboard.append([{"text": strings.BUTTONS["back_to_stats"], "callback_data": "check_stats"}])
                    
                    logger.debug(f"Final keyboard: {keyboard}")
                    
                    return await send_telegram_message(
                        telegram_id=telegram_id,
                        text=message,
                        parse_mode="HTML",
                        reply_markup={
                            "inline_keyboard": keyboard
                        }
                    )
                else:
                    stats = await self.user_service.get_user_stats(user)
                    tetrix_service = TetrixService(self.redis, self.session)
                    tetrix_metrics = await tetrix_service.get_metrics()
                    
                    return await send_telegram_message(
                        telegram_id=telegram_id,
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
                        parse_mode="HTML",
                        reply_markup={
                            "inline_keyboard": [
                                [{"text": strings.BUTTONS["refresh_stats"], "callback_data": "refresh_stats"}],
                                [{"text": strings.BUTTONS["show_invites"], "callback_data": "show_invites"}],
                                [{"text": strings.BUTTONS["leaderboard"], "callback_data": "leaderboard"}]
                            ]
                        }
                    )
            
            logger.warning("Unknown callback_data: %s", callback_data)
            return False
            
        except Exception as e:
            logger.error("Error in handle_callback_query: %s", str(e), exc_info=True)
            return False

    @with_locale
    async def handle_message(self, *, telegram_id: int, text: str, strings, language: str = 'ru') -> None:
        """Handle incoming message from user"""
        logger.debug(f"Handling message from telegram_id={telegram_id}, text='{text}'")
        
        # Get user
        user = await self.user_service.get_user_by_telegram_id(telegram_id)
        if not user:
            logger.debug(f"User not found for telegram_id={telegram_id}")
            return
        logger.debug(f"Found user: id={user.id}, telegram_id={user.telegram_id}, phase={user.registration_phase}")
        
        # Handle different registration phases
        if user.registration_phase == 'threads_job_campaign':
            logger.debug("User is in THREADS_JOB_CAMPAIGN phase")
            
            # Check if user already has analysis report
            campaign = await self.user_service.get_threads_campaign_entry(telegram_id)
            if campaign and campaign.analysis_report:
                logger.debug("User already has analysis report, ignoring message")
                return
                
            # Try to create campaign entry
            success, error = await self.user_service.create_threads_campaign_entry(telegram_id, text)
            logger.debug(f"create_threads_campaign_entry result: success={success}, error={error}")
            
            if not success:
                # Send error message
                if error == 'invalid_format':
                    logger.debug("Sending invalid format message")
                    await send_telegram_message(
                        telegram_id=telegram_id,
                        text=strings.THREADS_INVALID_FORMAT,
                        parse_mode="Markdown"
                    )
                elif error == 'not_found':
                    logger.debug("Sending profile not found message")
                    await send_telegram_message(
                        telegram_id=telegram_id,
                        text=strings.THREADS_PROFILE_NOT_FOUND,
                        parse_mode="Markdown"
                    )
                return
                
            # Send analyzing message
            await send_telegram_message(
                telegram_id=telegram_id,
                text=strings.THREADS_ANALYZING,
                parse_mode="Markdown"
            )
                
            # Start analysis
            logger.debug("Starting threads profile analysis")
            success = await self.user_service.analyze_threads_profile(telegram_id)
            logger.debug(f"analyze_threads_profile result: success={success}")
            
            if not success:
                logger.debug("Sending analysis error message")
                await send_telegram_message(
                    telegram_id=telegram_id,
                    text=strings.THREADS_ANALYSIS_ERROR,
                    parse_mode="Markdown"
                )
                return

    async def handle_callback(self, telegram_id: int, callback_data: str) -> None:
        """Handle callback query"""
        try:
            # Get user's language
            user_lang = await self.user_service.get_user_language(telegram_id) or 'ru'
            
            # Handle callback directly based on data
            if callback_data.startswith('lang_'):
                # Language selection
                language = callback_data[5:]  # Remove 'lang_' prefix
                await self.handle_language_change(telegram_id=telegram_id, language=language)
            elif callback_data == 'refresh_stats':
                await self.handle_refresh_stats(telegram_id=telegram_id)
            elif callback_data == 'show_invites':
                await self.handle_show_invites(telegram_id=telegram_id)
            elif callback_data == 'leaderboard':
                await self.handle_show_leaderboard(telegram_id=telegram_id)
            elif callback_data == 'create_wallet':
                await self.handle_create_wallet(telegram_id=telegram_id)
                
        except Exception as e:
            logger.error(f"Error handling callback from {telegram_id}: {e}")
            await self.send_error_message(telegram_id)

    @with_locale
    async def analyze_threads_profile(self, *, telegram_id: int, strings) -> bool:
        """Analyze user's Threads profile"""
        try:
            logger.debug(f"Starting analyze_threads_profile for telegram_id={telegram_id}")
            
            # Start analysis
            success = await self.user_service.analyze_threads_profile(telegram_id)
            logger.debug(f"analyze_threads_profile result: success={success}")
            
            if not success:
                # Send error message
                logger.debug("Sending analysis error message")
                await send_telegram_message(
                    telegram_id=telegram_id,
                    text=strings.THREADS_ANALYSIS_ERROR,
                    parse_mode="Markdown"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error in analyze_threads_profile: {e}")
            await send_telegram_message(
                telegram_id=telegram_id,
                text=strings.THREADS_ANALYSIS_ERROR,
                parse_mode="Markdown"
            )
            return False

@router.post(WEBHOOK_PATH)
async def telegram_webhook(
    update: Dict[str, Any],
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis)
):
    """Handle incoming updates from Telegram"""
    try:
        logger.debug("Received update: %s", update)
        
        # Get cache from app state
        cache = request.app.state.cache
        
        # Initialize services with cache
        user_service = UserService(session)
        user_service.cache = cache  # Set cache instance
        redis_service = RedisService(redis, cache)  # Pass cache to RedisService
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
            if text.startswith("/start"):
                # Check for threads campaign parameter
                is_threads_campaign = "threads" in text
                success = await handler.handle_start_command(telegram_id=telegram_id, is_threads_campaign=is_threads_campaign)
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
                
            # Handle regular messages
            await handler.handle_message(telegram_id=telegram_id, text=text)
            return {"ok": True}
            
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
            if user and user.registration_phase == 'pending':
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

@router.get("/test/user-status/{telegram_id}")
async def test_user_status(
    telegram_id: int,
    request: Request,
    redis: Redis = Depends(get_redis)
):
    """Test endpoint for get_user_status"""
    redis_service = request.app.state.redis_service
    
    # Check cache first
    if redis_service.cache:
        key = CacheKeys.USER_STATUS.format(telegram_id=telegram_id)
        cached = await redis_service.cache.get(key)
        if cached is not None:
            return {"status": json.loads(cached), "source": "cache"}
    
    # Check Redis
    key = CacheKeys.USER_STATUS.format(telegram_id=telegram_id)
    status = await redis.get(key)
    if status:
        return {"status": json.loads(status), "source": "redis"}
    
    return {"status": None, "source": "none"}

@router.post("/test/user-status/{telegram_id}")
async def test_set_user_status(
    telegram_id: int,
    request: Request,
    status: str = UserStatus.WAITING_WALLET.value
):
    """Test endpoint for set_user_status"""
    redis_service = request.app.state.redis_service
    status_data = {
        'status': status,
        'updated_at': datetime.utcnow().isoformat()
    }
    await redis_service.set_user_status(telegram_id, status_data)
    return {"status": "ok"}