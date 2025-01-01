"""Service for working with Threads API via RapidAPI"""

import aiohttp
import logging
from typing import Optional, Dict, List
import json
import os

logger = logging.getLogger(__name__)

class ThreadsService:
    """Service for interacting with Threads API"""
    
    def __init__(self):
        self.base_url = "https://threads-api4.p.rapidapi.com/api"
        self.headers = {
            "x-rapidapi-host": "threads-api4.p.rapidapi.com",
            "x-rapidapi-key": os.getenv("RAPIDAPI_KEY", "260c39343cmsh06d5efb8c560088p1f376djsn74c2482ddaa9")
        }

    async def get_user_id(self, username: str) -> Optional[str]:
        """Get user ID by username"""
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/user/info"
                params = {"username": username}
                
                async with session.get(
                    url,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error getting user ID for {username}: {response.status}")
                        return None
                        
                    data = await response.json()
                    user = data.get("data", {}).get("user")
                    if not user:
                        logger.error(f"User {username} not found")
                        return None
                        
                    return user.get("id")  # или user.get("pk") - они одинаковые
                    
            except Exception as e:
                logger.error(f"Error getting user ID: {e}")
                return None

    async def get_user_posts(self, user_id: str, limit: int = 25) -> List[Dict]:
        """Get user's posts"""
        # TODO: Implement with RapidAPI
        # For now returning empty list
        return [] 