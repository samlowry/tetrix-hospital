from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models.user import User
from typing import Optional, Dict, Any

class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, telegram_id: int, address: str, 
                         wallet_data: Optional[Dict] = None) -> User:
        user = User(
            telegram_id=telegram_id,
            address=address,
            wallet_data=wallet_data
        )
        self.session.add(user)
        try:
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except IntegrityError:
            await self.session.rollback()
            raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_address(self, address: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.address == address)
        )
        return result.scalar_one_or_none()

    async def update_user(self, user: User, **kwargs) -> User:
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

    async def delete_user(self, user: User) -> bool:
        try:
            await self.session.delete(user)
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            raise 