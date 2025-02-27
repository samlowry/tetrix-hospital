# Import necessary FastAPI components for routing and security
from fastapi import APIRouter, Depends, HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader

# Database and ORM related imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import get_session

# Service layer imports for business logic
from services.user_service import UserService
from services.tetrix_service import TetrixService
from services.telegram_service import get_telegram_name

# Data models
from models.user import User
from models.leaderboard import LeaderboardSnapshot

# Utility imports
from typing import List, Dict
from pydantic import BaseModel
from redis.asyncio import Redis
from core.deps import get_redis
import os
import logging

# our app API security configuration
API_KEY = os.getenv("API_KEY", "your-api-key")  # Environment variable for our app API authentication
api_key_header = APIKeyHeader(name="X-API-Key")  # Header configuration for our app API key
logger = logging.getLogger(__name__)  # Logger instance for this module

# Request model for user-related operations
class UserRequest(BaseModel):
    telegram_id: int  # Telegram user identifier

# Security middleware function to validate API key
async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return api_key

# Main API router with prefix and tags for swagger documentation
router = APIRouter(prefix="/api", tags=["api"])

# Endpoint to retrieve user information
@router.post("/users", response_model=Dict)
async def get_user(
    request: UserRequest,
    request_obj: Request,
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(get_api_key)
):
    """
    Get user information and statistics from the database
    Returns user profile and related data if user exists
    """
    # Get cache from app state
    cache = request_obj.app.state.cache
    
    # Initialize service with cache
    user_service = UserService(session)
    user_service.cache = cache  # Set cache instance
    
    user = await user_service.get_user_by_telegram_id(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.registration_phase != 'active':
        return {
            "status": "need_invite",
            "message": "User needs to enter an invite code to complete registration",
            "registration_phase": user.registration_phase
        }
        
    user_stats = await user_service.get_user_stats(user)
    return {
        'telegram_id': user.telegram_id,
        'telegram_display_name': user.telegram_display_name,
        'telegram_username': user.telegram_username,
        'registration_date': user.registration_date.isoformat(),
        'is_early_backer': user.is_early_backer,
        'registration_phase': user.registration_phase,
        'language': user.language,
        'stats': user_stats
    }

class LeaderboardStats(BaseModel):
    total_users: int
    total_points: int
    total_early_backers: int
    total_invited_users: int

class LeaderboardResponse(BaseModel):
    stats: LeaderboardStats
    users: List[Dict]

@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    session: AsyncSession = Depends(get_session),
    number: int = 10,
    offset: int = 0,
    api_key: str = Depends(get_api_key)
):
    """
    Get leaderboard of top users by points from snapshots with combined statistics.
    Maximum number of users returned is 1000.
    """
    # Enforce maximum limit of 1000
    if number > 1000:
        number = 1000
    return await LeaderboardSnapshot.get_leaderboard(session, limit=number, offset=offset)

@router.post("/leaderboard/rebuild", response_model=Dict)
async def rebuild_leaderboard(
    request: Request,
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(get_api_key)
):
    """
    Force rebuild of the leaderboard, ignoring the hourly schedule.
    Uses cached telegram names from the database.
    """
    # Get cache from app state
    cache = request.app.state.cache
    
    from services.leaderboard_service import LeaderboardService
    leaderboard_service = LeaderboardService(session, cache)
    await leaderboard_service.update_leaderboard(force=True)  # Always force update when called via API
    return {"status": "success", "message": "Leaderboard rebuilt successfully"}

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
    request_obj: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    api_key: str = Depends(get_api_key)
):
    """
    Get combined user statistics, leaderboard position and TETRIX metrics
    """
    # Get cache from app state
    cache = request_obj.app.state.cache
    
    # Initialize services with cache
    user_service = UserService(session)
    user_service.cache = cache  # Set cache instance
    tetrix_service = TetrixService(redis, session)
    
    # Get user stats
    user = await user_service.get_user_by_telegram_id(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.registration_phase != 'active':
        return {
            "status": "need_invite",
            "message": "User needs to enter an invite code to complete registration",
            "registration_phase": user.registration_phase
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
            'telegram_display_name': user.telegram_display_name,
            'telegram_username': user.telegram_username,
            'registration_date': user.registration_date.isoformat(),
            'is_early_backer': user.is_early_backer,
            'registration_phase': user.registration_phase,
            'language': user.language,
            'stats': user_stats
        },
        'ranking': rank_info,
        'leaderboard': leaderboard,
        'tetrix': tetrix_metrics
    } 

@router.post("/user/stats", dependencies=[Depends(get_api_key)])
async def get_user_stats(
    user_request: UserRequest,
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Dict:
    """Get user statistics"""
    try:
        # Get cache from app state
        cache = request.app.state.cache
        
        # Initialize service with cache
        user_service = UserService(session)
        user_service.cache = cache  # Set cache instance
        
        # Get user and their stats
        user = await user_service.get_user_by_telegram_id(user_request.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.registration_phase != 'active':
            return {
                "status": "need_invite",
                "message": "User needs to enter an invite code to complete registration",
                "registration_phase": user.registration_phase
            }
        
        user_stats = await user_service.get_user_stats(user)
        return {
            'telegram_id': user.telegram_id,
            'telegram_display_name': user.telegram_display_name,
            'telegram_username': user.telegram_username,
            'registration_date': user.registration_date.isoformat(),
            'is_early_backer': user.is_early_backer,
            'registration_phase': user.registration_phase,
            'language': user.language,
            'stats': user_stats
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Error getting user stats") 