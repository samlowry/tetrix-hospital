from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
import secrets
import logging
import os
import aiohttp

from models.user import User
from models.invite_code import InviteCode
from typing import Optional, List, Dict, Tuple

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
        self.redis = None  # Will be set externally

    async def set_redis(self, redis):
        """Set Redis client instance"""
        self.redis = redis

    async def create_user(
        self,
        telegram_id: int,
        wallet_address: str
    ) -> User:
        """Create a new user"""
        # Check early_backer status
        is_early_backer = False
        try:
            logger.info(f"[USER_SERVICE] Starting create_user for telegram_id={telegram_id}, wallet={wallet_address}")
            
            # Check if user already exists
            existing_user = await self.get_user_by_telegram_id(telegram_id)
            if existing_user:
                logger.info(f"[USER_SERVICE] User already exists with telegram_id={telegram_id}")
                return existing_user

            # Get Telegram info
            display_name, username = await get_telegram_info(telegram_id)
            logger.info(f"[USER_SERVICE] Got Telegram info: display_name={display_name}, username={username}")

            # Get user's current language preference
            language = await self.get_user_locale(telegram_id)
            logger.info(f"[USER_SERVICE] Got user language: {language}")

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
                is_fully_registered=is_early_backer,  # Early backers are automatically fully registered
                language=language,  # Save the language preference
                registration_phase='active' if is_early_backer else 'pending'  # Set registration phase based on early_backer status
            )
            
            logger.info("[USER_SERVICE] Adding user to session")
            self.session.add(user)
            
            logger.info("[USER_SERVICE] Committing session")
            await self.session.commit()
            
            logger.info("[USER_SERVICE] Refreshing user object")
            await self.session.refresh(user)
            
            logger.info(f"[USER_SERVICE] User created successfully: telegram_id={telegram_id}, is_early_backer={is_early_backer}, language={language}")
            return user
            
        except Exception as e:
            logger.error(f"[USER_SERVICE] Error in create_user: {e}", exc_info=True)
            raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by telegram_id"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

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
        user.is_fully_registered = True  # Keep this for backward compatibility
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

    async def get_user_locale(self, telegram_id: int) -> str:
        """
        Get user's locale. Check Redis first for performance,
        if not found - check DB and cache in Redis,
        if nowhere - return 'ru'
        """
        # Try Redis first for performance
        if self.redis:
            redis_key = f"user:{telegram_id}:language"
            lang = await self.redis.get(redis_key)
            logger.debug(f"Got language from Redis for {telegram_id}: {lang}")
            if lang:
                return lang  # Redis already returns decoded string

        # If not in Redis, try DB and cache result
        user = await self.get_user_by_telegram_id(telegram_id)
        if user and user.language:
            # Cache in Redis for future fast access
            if self.redis:
                redis_key = f"user:{telegram_id}:language"
                await self.redis.set(redis_key, user.language)
                logger.debug(f"Cached language in Redis for {telegram_id}: {user.language}")
            return user.language

        # Default to Russian
        logger.debug(f"Using default language for {telegram_id}")
        return 'ru'

    async def set_user_locale(self, telegram_id: int, language: str) -> None:
        """Set user's preferred language"""
        logger.debug(f"Setting language for {telegram_id} to {language}")
        if self.redis:
            redis_key = f"user:{telegram_id}:language"
            await self.redis.set(redis_key, language)
            logger.debug(f"Set language in Redis for {telegram_id}: {language}")

        # Additionally update in DB if user exists
        user = await self.get_user_by_telegram_id(telegram_id)
        if user:
            user.language = language
            await self.session.commit()
            logger.debug(f"Updated language in DB for {telegram_id}: {language}")
        else:
            logger.debug(f"User {telegram_id} not found in DB")

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