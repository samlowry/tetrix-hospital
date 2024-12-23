from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import get_session
from services.user_service import UserService
from services.tetrix_service import TetrixService
from services.telegram_service import get_telegram_name
from models.user import User
from models.leaderboard import LeaderboardSnapshot
from typing import List, Dict
from pydantic import BaseModel
from redis.asyncio import Redis
from core.deps import get_redis
import os
import logging

API_KEY = os.getenv("API_KEY", "your-api-key")
api_key_header = APIKeyHeader(name="X-API-Key")
logger = logging.getLogger(__name__)

class UserRequest(BaseModel):
    telegram_id: int

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return api_key

router = APIRouter(prefix="/api", tags=["api"])

@router.post("/users", response_model=Dict)
async def get_user(
    request: UserRequest,
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(get_api_key)
):
    """
    Get user information and statistics
    """
    user_service = UserService(session)
    user = await user_service.get_user_by_telegram_id(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_fully_registered:
        return {
            "status": "need_invite",
            "message": "User needs to enter an invite code to complete registration"
        }
        
    return await user_service.get_user_stats(user)

@router.get("/leaderboard", response_model=List[Dict])
async def get_leaderboard(
    session: AsyncSession = Depends(get_session),
    limit: int = 10,
    api_key: str = Depends(get_api_key)
):
    """
    Get leaderboard of top users by points from snapshots
    """
    return await LeaderboardSnapshot.get_leaderboard(session, limit=limit)

@router.get("/tetrix-state", response_model=Dict)
async def get_tetrix_state(
    redis: Redis = Depends(get_redis),
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(get_api_key)
):
    """
    Get TETRIX token metrics
    """
    tetrix_service = TetrixService(redis, session)
    return await tetrix_service.get_metrics()

@router.post("/combined", response_model=Dict)
async def get_combined_stats(
    request: UserRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    api_key: str = Depends(get_api_key)
):
    """
    Get combined user statistics, leaderboard position and TETRIX metrics
    """
    user_service = UserService(session)
    tetrix_service = TetrixService(redis, session)
    
    # Get user stats
    user = await user_service.get_user_by_telegram_id(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.is_fully_registered:
        return {
            "status": "need_invite",
            "message": "User needs to enter an invite code to complete registration"
        }
        
    user_stats = await user_service.get_user_stats(user)
    
    # Get user's rank from leaderboard
    rank_info = await LeaderboardSnapshot.get_latest_rank(session, request.telegram_id)
    if not rank_info:
        raise HTTPException(status_code=404, detail="User rank not found")
    
    # Get top 10 from leaderboard
    leaderboard = await LeaderboardSnapshot.get_leaderboard(session, limit=10)
    
    # Get TETRIX metrics
    tetrix_metrics = await tetrix_service.get_metrics()
    
    # Combine all information
    return {
        'user': {
            'telegram_id': user.telegram_id,
            'wallet_address': user.wallet_address,
            'registration_date': user.registration_date.isoformat(),
            'is_early_backer': user.is_early_backer,
            'is_fully_registered': user.is_fully_registered,
            **user_stats
        },
        'ranking': rank_info,
        'leaderboard': leaderboard,
        'tetrix': tetrix_metrics
    } 