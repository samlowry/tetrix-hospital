from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import get_session
from services.user_service import UserService
from models.user import User
from typing import List, Dict
from pydantic import BaseModel
import os
import aiohttp
import logging

API_KEY = os.getenv("API_KEY", "your-api-key")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
api_key_header = APIKeyHeader(name="X-API-Key")
logger = logging.getLogger(__name__)

class UserRequest(BaseModel):
    telegram_id: int

async def get_telegram_name(telegram_id: int) -> str:
    """Get user's current display name via Bot API"""
    try:
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return str(telegram_id)
            
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={'chat_id': telegram_id}) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        result = data['result']
                        first_name = result.get('first_name', '')
                        last_name = result.get('last_name', '')
                        full_name = f"{first_name} {last_name}".strip()
                        return full_name or str(telegram_id)
        
        logger.error(f"Failed to get Telegram name for {telegram_id}")
        return str(telegram_id)
        
    except Exception as e:
        logger.error(f"Error getting Telegram name: {e}")
        return str(telegram_id)

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
    return await user_service.get_user_stats(user)

@router.get("/leaderboard", response_model=List[Dict])
async def get_leaderboard(
    session: AsyncSession = Depends(get_session),
    limit: int = 10,
    api_key: str = Depends(get_api_key)
):
    """
    Get leaderboard of top users by points
    """
    user_service = UserService(session)
    
    # Get all users
    result = await session.execute(select(User))
    users = result.scalars().all()
    
    # Get stats for each user and sort by points
    user_stats_list = []
    for user in users:
        stats = await user_service.get_user_stats(user)
        telegram_name = await get_telegram_name(user.telegram_id)
        user_stats_list.append((user, stats, telegram_name))
    
    # Sort by points in descending order
    user_stats_list.sort(key=lambda x: x[1]['points'], reverse=True)
    
    # Format response
    leaderboard = []
    for idx, (user, stats, telegram_name) in enumerate(user_stats_list[:limit]):
        leaderboard.append({
            'telegram_name': telegram_name,
            'points': stats['points'],
            'total_invites': stats['total_invites'],
            'rank': idx + 1
        })
    
    return leaderboard

@router.post("/combined", response_model=Dict)
async def get_combined_stats(
    request: UserRequest,
    session: AsyncSession = Depends(get_session),
    api_key: str = Depends(get_api_key)
):
    """
    Get combined user statistics and leaderboard position
    """
    user_service = UserService(session)
    
    # Get user stats
    user = await user_service.get_user_by_telegram_id(request.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user_stats = await user_service.get_user_stats(user)
    
    # Get all users for ranking
    result = await session.execute(select(User))
    users = result.scalars().all()
    
    # Get stats for each user and sort by points
    user_stats_list = []
    for u in users:
        stats = await user_service.get_user_stats(u)
        user_stats_list.append((u, stats))
    
    # Sort by points in descending order
    user_stats_list.sort(key=lambda x: x[1]['points'], reverse=True)
    
    # Find user's rank
    user_rank = next((idx + 1 for idx, (u, _) in enumerate(user_stats_list) if u.id == user.id), 0)
    total_users = len(user_stats_list)
    
    # Get top 10 for leaderboard section
    leaderboard = []
    for idx, (u, stats) in enumerate(user_stats_list[:10]):
        telegram_name = await get_telegram_name(u.telegram_id)
        leaderboard.append({
            'telegram_name': telegram_name,
            'points': stats['points'],
            'total_invites': stats['total_invites'],
            'rank': idx + 1
        })
    
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
        'ranking': {
            'rank': user_rank,
            'total_users': total_users,
            'percentile': round((total_users - user_rank + 1) / total_users * 100, 2)
        },
        'leaderboard': leaderboard
    } 