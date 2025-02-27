from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
import secrets
import logging
import os
import aiohttp
import json

from models.user import User
from models.invite_code import InviteCode
from typing import Optional, List, Dict, Tuple
from core.cache import CacheKeys, cache_permanent
from services.llm_service import LLMService
from services.threads_service import ThreadsService
from services.redis_service import RedisService
from models.threads_job_campaign import ThreadsJobCampaign
from core.config import get_settings
from locales.language_utils import get_strings

settings = get_settings()
logger = logging.getLogger(__name__)

async def get_telegram_info(telegram_id: int) -> Tuple[Optional[str], Optional[str]]:
    """Get user's display name and username via Bot API"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return None, None
        
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={'chat_id': telegram_id}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        result = data['result']
                        first_name = result.get('first_name', '')
                        last_name = result.get('last_name', '')
                        display_name = f"{first_name} {last_name}".strip()
                        username = result.get('username')
                        return display_name or None, username
    except Exception as e:
        logger.error(f"Error getting Telegram info: {e}")
    return None, None

def utc_now() -> datetime:
    """Returns current UTC time"""
    return datetime.utcnow()

class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = None  # Initialize cache attribute
        self._user_cache = {}  # Local cache for users within request
        self.llm_service = LLMService()  # Initialize LLM service

    async def set_redis(self, redis):
        """Set Redis client instance"""
        self.redis = redis

    async def create_user(
        self,
        telegram_id: int,
        wallet_address: Optional[str] = None,
        is_threads_campaign: bool = False
    ) -> User:
        """Create a new user"""
        # Check early_backer status
        is_early_backer = False
        try:
            logger.info(f"[USER_SERVICE] Starting create_user for telegram_id={telegram_id}, wallet={wallet_address}, is_threads_campaign={is_threads_campaign}")
            
            # Check if user already exists
            existing_user = await self.get_user_by_telegram_id(telegram_id)
            if existing_user:
                logger.info(f"[USER_SERVICE] User already exists with telegram_id={telegram_id}")
                return existing_user

            # Get Telegram info
            display_name, username = await get_telegram_info(telegram_id)
            logger.info(f"[USER_SERVICE] Got Telegram info: display_name={display_name}, username={username}")

            # If no wallet address, create user in preregistered state
            if wallet_address is None:
                logger.info(f"[USER_SERVICE] Creating new user in {'threads_job_campaign' if is_threads_campaign else 'preregistered'} state")
                user = User(
                    telegram_id=telegram_id,
                    telegram_display_name=display_name,
                    telegram_username=username,
                    wallet_address=None,
                    max_invite_slots=5,
                    ignore_slot_reset=False,
                    is_early_backer=False,
                    language=None,  # Don't set default language
                    registration_phase='threads_job_campaign' if is_threads_campaign else 'preregistered'
                )
            else:
                logger.info(f"[USER_SERVICE] Checking early backer status for wallet: {wallet_address}")
                # Use relative path from app.py
                file_path = 'first_backers.txt'
                logger.info(f"[USER_SERVICE] Looking for first_backers.txt at: {file_path}")
                
                try:
                    with open(file_path, 'r') as f:
                        early_backers = f.read().splitlines()
                        logger.info(f"[USER_SERVICE] Loaded {len(early_backers)} early backers")
                        logger.info(f"[USER_SERVICE] First few backers: {early_backers[:5]}")
                        # Normalize wallet address for comparison
                        wallet_address = wallet_address.strip().lower()
                        early_backers = [addr.strip().lower() for addr in early_backers]
                        is_early_backer = wallet_address in early_backers
                        logger.info(f"[USER_SERVICE] Is early backer check result: {is_early_backer} for wallet {wallet_address}")
                except FileNotFoundError:
                    logger.error(f"[USER_SERVICE] first_backers.txt not found at {file_path}")
                    raise
                except Exception as e:
                    logger.error(f"[USER_SERVICE] Error reading first_backers.txt: {e}", exc_info=True)
                    raise

                logger.info(f"[USER_SERVICE] Creating new user object with telegram_id={telegram_id}, is_early_backer={is_early_backer}")
                user = User(
                    telegram_id=telegram_id,
                    telegram_display_name=display_name,
                    telegram_username=username,
                    wallet_address=wallet_address,
                    max_invite_slots=5,
                    ignore_slot_reset=False,
                    is_early_backer=is_early_backer,
                    language=None,  # Don't set default language
                    registration_phase='active' if is_early_backer else 'pending'  # Set registration phase based on early_backer status
                )
            
            logger.info("[USER_SERVICE] Adding user to session")
            self.session.add(user)
            
            logger.info("[USER_SERVICE] Committing session")
            await self.session.commit()
            
            logger.info("[USER_SERVICE] Refreshing user object")
            await self.session.refresh(user)
            
            logger.info(f"[USER_SERVICE] User created successfully: telegram_id={telegram_id}, is_early_backer={is_early_backer}, language={user.language}")
            return user
            
        except Exception as e:
            logger.error(f"[USER_SERVICE] Error in create_user: {e}", exc_info=True)
            raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID"""
        try:
            # Check local cache first
            if telegram_id in self._user_cache:
                return self._user_cache[telegram_id]
            
            # Query user
            query = select(User).where(User.telegram_id == telegram_id)
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                # Cache user for this request
                self._user_cache[telegram_id] = user
            
            return user
        except Exception as e:
            logger.error(f"Failed to get user by telegram_id {telegram_id}: {e}")
            return None

    async def get_user_by_wallet_address(self, wallet_address: str) -> Optional[User]:
        """Get user by wallet address"""
        result = await self.session.execute(
            select(User).where(User.wallet_address == wallet_address)
        )
        return result.scalar_one_or_none()

    async def update_user(self, user: User, **kwargs) -> User:
        """Update user data"""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError:
            await self.session.rollback()
            raise

    async def get_available_invites(self, user: User) -> int:
        """Returns the number of available (unused) invite codes"""
        if user.registration_phase != 'active':
            return 0

        # Get all unused codes
        result = await self.session.execute(
            select(func.count(InviteCode.id))
            .where(InviteCode.creator_id == user.id)
            .where(InviteCode.used_by_id.is_(None))
        )
        return result.scalar_one()

    async def generate_invite_codes(self, user: User) -> List[Dict]:
        """Generate invite codes for user"""
        if user.registration_phase != 'active':
            return []

        now = utc_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get all unused codes (regardless of creation date)
        result = await self.session.execute(
            select(InviteCode)
            .where(InviteCode.creator_id == user.id)
            .where(InviteCode.used_by_id.is_(None))
        )
        unused_codes = result.scalars().all()

        # Get codes used today
        result = await self.session.execute(
            select(InviteCode)
            .where(InviteCode.creator_id == user.id)
            .where(InviteCode.used_by_id.isnot(None))
            .where(InviteCode.used_at >= today_start)
        )
        used_today_codes = result.scalars().all()

        # Total number of codes should not exceed max_invite_slots
        total_codes = len(unused_codes) + len(used_today_codes)
        codes_needed = max(0, user.max_invite_slots - total_codes)

        # Generate new codes if needed
        if codes_needed > 0:
            for _ in range(codes_needed):
                while True:
                    code = secrets.token_hex(8)
                    # Check code uniqueness
                    result = await self.session.execute(
                        select(InviteCode).where(InviteCode.code == code)
                    )
                    if not result.scalar_one_or_none():
                        break

                invite = InviteCode(
                    code=code,
                    creator_id=user.id,
                    created_at=now
                )
                self.session.add(invite)

            await self.session.commit()

        # Get all current codes (all unused + used today)
        result = await self.session.execute(
            select(InviteCode)
            .where(InviteCode.creator_id == user.id)
            .where(
                (InviteCode.used_by_id.is_(None)) |
                ((InviteCode.used_by_id.isnot(None)) & (InviteCode.used_at >= today_start))
            )
            .order_by(InviteCode.created_at.desc())
        )
        all_codes = result.scalars().all()

        return [{
            'code': code.code,
            'status': 'used' if code.used_by_id else 'active',
            'used_at': code.used_at.isoformat() if code.used_at else None
        } for code in all_codes]

    async def verify_invite_code(self, code: str) -> Optional[InviteCode]:
        """Verify invite code validity"""
        result = await self.session.execute(
            select(InviteCode)
            .where(InviteCode.code == code)
            .where(InviteCode.used_by_id.is_(None))
        )
        return result.scalar_one_or_none()

    async def use_invite_code(self, code: str, user: User) -> bool:
        """Use invite code"""
        invite = await self.verify_invite_code(code)
        if not invite:
            return False

        invite.used_by_id = user.id
        invite.used_at = utc_now()
        user.registration_phase = 'active'  # Set registration phase to active when invite code is used

        try:
            await self.session.commit()
            return True
        except IntegrityError:
            await self.session.rollback()
            return False

    async def get_user_stats(self, user: User) -> Dict:
        """Get user statistics"""
        # Count successful invites
        result = await self.session.execute(
            select(func.count(InviteCode.id))
            .where(InviteCode.creator_id == user.id)
            .where(InviteCode.used_by_id.isnot(None))
        )
        total_invites = result.scalar_one()

        # Get current codes
        codes = await self.generate_invite_codes(user)
        available_invites = await self.get_available_invites(user)

        # Calculate points
        holding_points = 420  # Placeholder
        points_per_invite = 420
        invite_points = total_invites * points_per_invite
        early_backer_bonus = 4200 if user.is_early_backer else 0

        total_points = holding_points + invite_points + early_backer_bonus

        return {
            'points': total_points,
            'total_invites': total_invites,
            'available_invites': available_invites,
            'registration_date': user.registration_date.isoformat(),
            'points_breakdown': {
                'holding': holding_points,
                'invites': invite_points,
                'early_backer_bonus': early_backer_bonus
            },
            'points_per_invite': points_per_invite,
            'invite_codes': codes,
            'max_invite_slots': user.max_invite_slots,
            'ignore_slot_reset': user.ignore_slot_reset
        }

    async def get_top_inviters(self, limit: int = 10) -> List[tuple]:
        """Get top users by number of invites"""
        result = await self.session.execute(
            select(User, func.count(InviteCode.id).label('invite_count'))
            .join(InviteCode, InviteCode.creator_id == User.id)
            .where(InviteCode.used_by_id.isnot(None))
            .where(User.registration_phase == 'active')
            .group_by(User.id)
            .order_by(func.count(InviteCode.id).desc())
            .limit(limit)
        )
        return result.all()

    async def delete_user(self, user: User) -> bool:
        """Delete user"""
        try:
            await self.session.delete(user)
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            raise 

    async def update_telegram_info(self, user: User) -> bool:
        """Update user's Telegram display name and username"""
        try:
            display_name, username = await get_telegram_info(user.telegram_id)
            if display_name is not None or username is not None:
                if display_name is not None:
                    user.telegram_display_name = display_name
                if username is not None:
                    user.telegram_username = username
                await self.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating Telegram info: {e}")
            await self.session.rollback()
            return False

    @cache_permanent(key_pattern=CacheKeys.USER_LANGUAGE)
    async def get_user_language(self, telegram_id: int) -> Optional[str]:
        """
        Get user's preferred language from cache or database
        Args:
            telegram_id (int): User's Telegram ID
        Returns:
            Optional[str]: Language code or None if not set
        """
        # Try cache first
        if self.cache:
            cached = await self.cache.get(CacheKeys.USER_LANGUAGE.format(telegram_id=telegram_id))
            if cached is not None:
                return cached
        
        # Check local user cache first
        if telegram_id in self._user_cache:
            user = self._user_cache[telegram_id]
            if user and user.language:
                # Update cache for future requests
                if self.cache:
                    key = CacheKeys.USER_LANGUAGE.format(telegram_id=telegram_id)
                    await self.cache.set(key, user.language)
                return user.language
        
        # If not in cache or local cache, check database
        user = await self.get_user_by_telegram_id(telegram_id)
        if user and user.language:
            # Update cache for future requests
            if self.cache:
                key = CacheKeys.USER_LANGUAGE.format(telegram_id=telegram_id)
                await self.cache.set(key, user.language)
            return user.language
            
        return None

    async def set_user_language(self, telegram_id: int, language: str) -> bool:
        """
        Set user's preferred language in cache and DB if user exists
        Args:
            telegram_id (int): User's Telegram ID
            language (str): Language code
        Returns:
            bool: True if successful
        """
        key = CacheKeys.USER_LANGUAGE.format(telegram_id=telegram_id)
        
        # Update cache
        if self.cache:
            await self.cache.set(key, language)
        
        # Update DB if user exists
        user = await self.get_user_by_telegram_id(telegram_id)
        if user and user.language != language:
            user.language = language
            await self.session.commit()
        
        return True

    async def update_user_language(self, user: User) -> bool:
        """
        Update user's language preference in cache from DB
        Args:
            user (User): User model instance
        Returns:
            bool: True if successful
        """
        if not user.telegram_id or not user.language:
            return False
        
        return await self.set_user_language(user.telegram_id, user.language)

    async def get_leaderboard_snapshot(self) -> list:
        """Get top users from leaderboard snapshot table"""
        query = text("""
            SELECT 
                ls.rank,
                ls.telegram_id,
                ls.telegram_name as name,
                ls.points
            FROM leaderboard_snapshots ls
            JOIN "user" u ON u.telegram_id = ls.telegram_id
            WHERE ls.snapshot_time = (
                SELECT MAX(snapshot_time)
                FROM leaderboard_snapshots
            )
            AND u.registration_phase = 'active'
            ORDER BY ls.rank ASC
        """)
        result = await self.session.execute(query)
        return [dict(r._mapping) for r in result]

    async def get_user_leaderboard_position(self, user) -> int:
        """Get user's position from leaderboard snapshot"""
        query = text("""
            SELECT rank 
            FROM leaderboard_snapshots ls
            JOIN "user" u ON u.telegram_id = ls.telegram_id
            WHERE ls.telegram_id = :telegram_id
            AND u.registration_phase = 'active'
            AND ls.snapshot_time = (
                SELECT MAX(snapshot_time)
                FROM leaderboard_snapshots
            )
        """)
        result = await self.session.execute(
            query, 
            {"telegram_id": user.telegram_id}
        )
        row = result.first()
        return row.rank if row else 0

    async def get_user_rank(self, user) -> str:
        """Get user's rank from leaderboard snapshot"""
        # First get total number of users and user's rank
        query = text("""
            WITH snapshot AS (
                SELECT snapshot_time, COUNT(*) as total_users
                FROM leaderboard_snapshots ls
                JOIN "user" u ON u.telegram_id = ls.telegram_id
                WHERE ls.snapshot_time = (
                    SELECT MAX(snapshot_time)
                    FROM leaderboard_snapshots
                )
                AND u.registration_phase = 'active'
                GROUP BY snapshot_time
            )
            SELECT ls.rank, s.total_users
            FROM leaderboard_snapshots ls
            JOIN "user" u ON u.telegram_id = ls.telegram_id
            JOIN snapshot s ON ls.snapshot_time = s.snapshot_time
            WHERE ls.telegram_id = :telegram_id
            AND u.registration_phase = 'active'
            AND ls.snapshot_time = (
                SELECT MAX(snapshot_time)
                FROM leaderboard_snapshots
            )
        """)
        result = await self.session.execute(
            query, 
            {"telegram_id": user.telegram_id}
        )
        row = result.first()
        if not row:
            return "newbie"
            
        rank = row.rank
        total_users = row.total_users
        
        # Calculate percentage position (0-100%)
        percentage = (rank / total_users) * 100
        
        # Assign ranks based on percentages
        if percentage <= 5:  # Top 5%
            return "legend"
        elif percentage <= 15:  # Top 15%
            return "master"
        elif percentage <= 30:  # Top 30%
            return "pro"
        elif percentage <= 50:  # Top 50%
            return "experienced"
        else:  # Bottom 50%
            return "newbie"

    async def get_threads_campaign_entry(self, telegram_id: int):
        """Get threads campaign entry for user by telegram ID"""
        from models.threads_job_campaign import ThreadsJobCampaign
        return await ThreadsJobCampaign.get_by_telegram_id(self.session, telegram_id)

    async def create_threads_campaign_entry(self, telegram_id: int, text: str) -> tuple[bool, str]:
        """
        Create threads campaign entry for user
        Returns: (success, error_code)
        error_code: None if success, 'invalid_format' or 'not_found' if failed
        """
        from models.threads_job_campaign import ThreadsJobCampaign
        from services.threads_service import ThreadsService
        
        logger.debug(f"Starting create_threads_campaign_entry for telegram_id={telegram_id}, text='{text}'")
        
        # Get user
        user = await self.get_user_by_telegram_id(telegram_id)
        if not user:
            logger.debug(f"User not found for telegram_id={telegram_id}")
            return False, 'invalid_format'
        logger.debug(f"Found user: id={user.id}, telegram_id={user.telegram_id}")
            
        # Validate and extract username
        username = self.validate_threads_username(text)
        if not username:
            logger.debug(f"Invalid Threads URL/username format: {text}")
            return False, 'invalid_format'
        logger.debug(f"Extracted username: {username}")
            
        # Get user data and posts
        threads_service = ThreadsService()
        threads_data = await threads_service.get_user_data(username)
        if not threads_data:
            logger.debug(f"Threads profile not found for username: {username}")
            return False, 'not_found'
        
        user_id = threads_data['user']['data']['user']['id']
        logger.debug(f"Found Threads user_id: {user_id}")
            
        try:
            # Delete any existing campaign entry for this user
            existing_campaign = await ThreadsJobCampaign.get_by_telegram_id(self.session, telegram_id)
            if existing_campaign:
                logger.debug(f"Deleting existing campaign entry for user_id={user.id}")
                await self.session.delete(existing_campaign)
                await self.session.commit()
            
            # Create new campaign entry with posts data
            campaign = ThreadsJobCampaign(
                user_id=user.id,
                threads_username=username,
                threads_user_id=user_id,
                posts_json=json.dumps(threads_data, ensure_ascii=False)  # Store full response
            )
            
            logger.debug(f"Attempting to save campaign entry: user_id={user.id}, threads_username={username}")
            self.session.add(campaign)
            await self.session.commit()
            logger.debug("Successfully created campaign entry")
            return True, None
        except Exception as e:
            logger.error(f"Error creating threads campaign entry: {e}")
            await self.session.rollback()
            return False, 'invalid_format'

    def validate_threads_username(self, text: str) -> Optional[str]:
        """
        Validate and extract Threads username from input text.
        Returns cleaned username or None if invalid.
        """
        logger.debug(f"Starting validate_threads_username with text: '{text}'")
        
        # Handle None or empty string
        if not text:
            logger.debug("Empty text input")
            return None
            
        # Remove all kinds of whitespace from both ends
        text = ' '.join(text.split()).strip()
        if not text:
            logger.debug("Text is only whitespace")
            return None
        
        # Handle direct username input
        if text.startswith('@'):
            username = text[1:]  # Remove @
            logger.debug(f"Direct username input: {username}")
        # Handle full URL
        elif text.startswith(('http://', 'https://')):
            try:
                from urllib.parse import urlparse
                parsed = urlparse(text)
                logger.debug(f"Parsed URL: netloc={parsed.netloc}, path={parsed.path}")
                
                # Verify it's a threads.net URL (with or without www)
                if not any(parsed.netloc.endswith(domain) for domain in ['threads.net', 'www.threads.net']):
                    logger.debug(f"Invalid domain: {parsed.netloc}")
                    return None
                    
                # Get path without leading/trailing slashes
                path = parsed.path.strip('/')
                
                # Path should start with @ for username
                if not path.startswith('@'):
                    logger.debug(f"Path doesn't start with @: {path}")
                    return None
                    
                # Get username part (before any query params or additional path segments)
                username = path[1:].split('?')[0].split('/')[0]
                logger.debug(f"Extracted username from URL: {username}")
                
            except Exception as e:
                logger.error(f"Error parsing Threads URL: {e}")
                return None
        else:
            logger.debug("Text is not a username (@) or URL (http)")
            return None
            
        # Clean username from any remaining whitespace
        username = username.strip()
        if not username:
            logger.debug("Username is empty after cleaning")
            return None
            
        # Validate username format (letters, numbers, underscores, dots, no spaces)
        import re
        if not re.match(r'^[a-zA-Z0-9_.]+$', username):
            logger.debug(f"Username contains invalid characters: {username}")
            return None
            
        logger.debug(f"Successfully validated username: {username}")
        return username

    async def analyze_threads_profile(self, telegram_id: int) -> bool:
        """Analyze user's Threads profile"""
        try:
            # Get campaign entry
            campaign = await self.get_threads_campaign_entry(telegram_id)
            if not campaign:
                logger.error(f"No campaign entry found for user {telegram_id}")
                return False

            # Get user language
            language = await self.get_user_language(telegram_id)
            
            # Initialize threads service
            threads_service = ThreadsService()

            # If we have posts but no analysis, resume analysis
            if campaign.posts_json and not campaign.analysis_report:
                logger.info(f"Resuming analysis for user {telegram_id} with existing posts")
                threads_data = json.loads(campaign.posts_json)
                posts = threads_service.extract_posts_from_json(threads_data)
                analysis_report = await self.llm_service.analyze_threads_profile(posts, telegram_id, language)
                if analysis_report:
                    campaign.analysis_report = json.dumps(analysis_report, ensure_ascii=False)
                    await self.session.commit()
                    return True
                return False
            
            # If we have both posts and analysis, just send the formatted report
            if campaign.posts_json and campaign.analysis_report:
                logger.info(f"Sending existing analysis for user {telegram_id}")
                analysis_report = json.loads(campaign.analysis_report)
                await self.llm_service.send_analysis_to_user(telegram_id, analysis_report, language)
                return True

            # This should never happen since we now get posts data during campaign creation
            logger.error(f"Campaign found without posts_json for user {telegram_id}")
            return False

        except Exception as e:
            logger.error(f"Error in analyze_threads_profile: {e}")
            return False