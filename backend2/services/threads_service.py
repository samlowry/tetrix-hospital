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
            "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
        }

    async def get_user_id(self, username: str) -> Optional[str]:
        """Get user ID by username"""
        logger.debug(f"Starting get_user_id for username: {username}")
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/user/info"
                params = {"username": username}
                logger.debug(f"Making request to {url} with params: {params}")
                
                async with session.get(
                    url,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error getting user ID for {username}: status={response.status}")
                        response_text = await response.text()
                        logger.error(f"Response body: {response_text}")
                        return None
                        
                    data = await response.json()
                    logger.debug(f"Got response data: {json.dumps(data, indent=2)}")
                    
                    user = data.get("data", {}).get("user")
                    if not user:
                        logger.error(f"User {username} not found in response data")
                        return None
                        
                    user_id = user.get("id")
                    logger.debug(f"Successfully got user_id: {user_id}")
                    return user_id  # или user.get("pk") - они одинаковые
                    
            except Exception as e:
                logger.error(f"Error getting user ID: {str(e)}")
                return None

    async def get_user_posts(self, user_id: str, limit: int = 25) -> List[str]:
        """Get user's posts texts"""
        logger.debug(f"Starting get_user_posts for user_id: {user_id}, limit: {limit}")
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/user/posts"
                params = {"user_id": user_id}
                logger.debug(f"Making request to {url} with params: {params}")
                
                async with session.get(
                    url,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error getting posts for user {user_id}: status={response.status}")
                        response_text = await response.text()
                        logger.error(f"Response body: {response_text}")
                        return []
                        
                    data = await response.json()
                    logger.debug(f"Got response data: {json.dumps(data, indent=2)}")
                    
                    # Check for errors
                    if data.get("errors") or not data.get("data"):
                        error = data.get("errors", [{}])[0]
                        logger.error(f"API error for user {user_id}: {error.get('description', 'Unknown error')}")
                        return []
                    
                    # Extract only post texts
                    try:
                        posts = []
                        for edge in data['data']['mediaData']['edges']:
                            text = edge['node']['thread_items'][0]['post'].get('caption', {}).get('text', '')
                            if text:  # Сохраняем только непустые тексты
                                posts.append(text)
                        logger.debug(f"Successfully extracted {len(posts)} posts")
                        return posts[:limit]
                        
                    except (KeyError, IndexError) as e:
                        logger.error(f"Error parsing posts data: {str(e)}")
                        return []
                        
            except Exception as e:
                logger.error(f"Error getting user posts: {str(e)}")
                return [] 