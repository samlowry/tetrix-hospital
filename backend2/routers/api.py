from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import get_session
from services.user_service import UserService
from typing import Dict, Any

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/user/{telegram_id}")
async def get_user_info(
    telegram_id: int,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get user information"""
    try:
        user_service = UserService(session)
        user = await user_service.get_user_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        stats = await user_service.get_user_stats(user)
        return stats
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leaderboard")
async def get_leaderboard(
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Get leaderboard"""
    # TODO: Implement leaderboard retrieval
    try:
        user_service = UserService(session)
        top_users = await user_service.get_top_inviters()
        return {"leaderboard": top_users}
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))