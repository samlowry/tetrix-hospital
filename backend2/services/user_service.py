from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
import secrets
import logging
import os

from models.user import User
from models.invite_code import InviteCode
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

def utc_now() -> datetime:
    """Returns current UTC time"""
    return datetime.utcnow()

class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(
        self,
        telegram_id: int,
        wallet_address: str
    ) -> User:
        """Create a new user"""
        # Check early_backer status
        is_early_backer = False
        try:
            logger.info(f"Checking early backer status for wallet: {wallet_address}")
            # Use relative path from app.py
            file_path = 'first_backers.txt'
            logger.info(f"Looking for first_backers.txt at: {file_path}")
            
            with open(file_path, 'r') as f:
                early_backers = f.read().splitlines()
                logger.info(f"Loaded {len(early_backers)} early backers")
                logger.info(f"First few backers: {early_backers[:5]}")
                # Normalize wallet address for comparison
                wallet_address = wallet_address.strip().lower()
                early_backers = [addr.strip().lower() for addr in early_backers]
                is_early_backer = wallet_address in early_backers
                logger.info(f"Is early backer: {is_early_backer}")
        except Exception as e:
            logger.error(f"Error checking early backer status: {e}")

        user = User(
            telegram_id=telegram_id,
            wallet_address=wallet_address,
            max_invite_slots=5,
            ignore_slot_reset=False,
            is_early_backer=is_early_backer,
            is_fully_registered=is_early_backer  # Early backers are automatically fully registered
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

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

    async def get_available_invite_slots(self, user: User) -> int:
        """Returns the number of available invite slots"""
        if not user.is_fully_registered:
            return 0

        if user.ignore_slot_reset:
            return user.max_invite_slots

        now = utc_now()
        # Check if slots need to be reset
        if user.last_slot_reset and (now - user.last_slot_reset > timedelta(days=1)):
            user.last_slot_reset = now
            await self.session.commit()
            return user.max_invite_slots

        # Count used slots in the last 24 hours
        result = await self.session.execute(
            select(func.count(InviteCode.id))
            .where(InviteCode.creator_id == user.id)
            .where(InviteCode.created_at >= now - timedelta(days=1))
        )
        used_slots = result.scalar_one()
        return max(0, user.max_invite_slots - used_slots)

    async def generate_invite_codes(self, user: User) -> List[Dict]:
        """Generate invite codes for user"""
        if not user.is_fully_registered:
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
        user.is_fully_registered = True

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

        # Calculate points
        holding_points = 420  # Placeholder
        points_per_invite = 420
        invite_points = total_invites * points_per_invite
        early_backer_bonus = 4200 if user.is_early_backer else 0

        total_points = holding_points + invite_points + early_backer_bonus

        return {
            'points': total_points,
            'total_invites': total_invites,
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