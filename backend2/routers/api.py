from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_session
from services.user_service import UserService

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/users/{telegram_id}")
async def get_user(
    telegram_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Get user information
    """
    user_service = UserService(session)
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/leaderboard")
async def get_leaderboard(
    session: AsyncSession = Depends(get_session)
):
    """
    Get leaderboard
    """
    # TODO: Implement leaderboard retrieval
    pass 