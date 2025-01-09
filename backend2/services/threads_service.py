"""Service for working with Threads API via RapidAPI"""

import aiohttp
import logging
from typing import Optional, Dict, List
import json
import os
import asyncio

logger = logging.getLogger(__name__)

class ThreadsService:
    """Service for interacting with Threads API"""
    
    def __init__(self):
        self.base_url = "https://threads-api4.p.rapidapi.com/api"
        self.headers = {
            "x-rapidapi-host": "threads-api4.p.rapidapi.com",
            "x-rapidapi-key": os.getenv("RAPIDAPI_KEY")
        }
        self.max_retries = 4
        self.retry_delay = 1  # seconds

    async def _make_request(self, session: aiohttp.ClientSession, url: str, params: Dict) -> Optional[Dict]:
        """Make request with retry logic for rate limits"""
        retries = 0
        while retries <= self.max_retries:
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 429:  # Rate limit error
                        if retries == self.max_retries:
                            logger.error(f"Rate limit reached after {retries} retries")
                            return None
                        retries += 1
                        logger.warning(f"Rate limit hit, retry {retries} of {self.max_retries}")
                        await asyncio.sleep(self.retry_delay)
                        continue
                        
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error(f"Error response: status={response.status}, body={response_text}")
                        return None
                        
                    return await response.json()
                    
            except Exception as e:
                logger.error(f"Request error: {str(e)}")
                return None
        return None

    async def get_user_data(self, username: str) -> Optional[Dict]:
        """Get user data by username, including ID and posts"""
        logger.debug(f"Starting get_user_data for username: {username}")
        async with aiohttp.ClientSession() as session:
            try:
                # First get user info
                url = f"{self.base_url}/user/info"
                params = {"username": username}
                logger.debug(f"Making request to {url} with params: {params}")
                
                user_data = await self._make_request(session, url, params)
                if not user_data:
                    logger.error(f"Failed to get user data for {username}")
                    return None
                    
                logger.debug(f"Got user data response: {json.dumps(user_data, indent=2)}")
                
                user = user_data.get("data", {}).get("user")
                if not user:
                    logger.error(f"User {username} not found in response data")
                    return None
                    
                user_id = user.get("id")
                if not user_id:
                    logger.error(f"No user ID found for {username}")
                    return None

                logger.debug(f"Successfully got user_id: {user_id}")
                
                # Then get posts data
                url = f"{self.base_url}/user/posts"
                params = {"user_id": user_id}
                logger.debug(f"Making request to {url} with params: {params}")
                
                posts_data = await self._make_request(session, url, params)
                if not posts_data:
                    logger.error(f"Failed to get posts for user {user_id}")
                    return None
                    
                logger.debug(f"Got posts data response: {json.dumps(posts_data, indent=2)}")
                
                # Check for errors
                if posts_data.get("errors") or not posts_data.get("data"):
                    error = posts_data.get("errors", [{}])[0]
                    logger.error(f"API error for user {user_id}: {error.get('description', 'Unknown error')}")
                    return None
                
                # Return combined data
                return {
                    "user": user_data,
                    "posts": posts_data
                }
                    
            except Exception as e:
                logger.error(f"Error getting user data: {str(e)}")
                return None

    def extract_posts_from_json(self, data: Dict) -> List[str]:
        """Extract post texts from API response JSON"""
        try:
            posts = []
            for edge in data['posts']['data']['mediaData']['edges']:
                post = edge['node']['thread_items'][0]['post']
                
                # Try to get text from text_post_app_info first
                text = None
                if post.get('text_post_app_info'):
                    fragments = post['text_post_app_info'].get('text_fragments', {}).get('fragments', [])
                    if fragments and fragments[0].get('plaintext'):
                        text = fragments[0]['plaintext']
                
                # Fallback to caption if no text in text_post_app_info
                if not text and post.get('caption'):
                    text = post['caption'].get('text', '')
                
                if text:  # Save only non-empty texts
                    posts.append(text)
                    
            return posts
            
        except (KeyError, IndexError) as e:
            logger.error(f"Error extracting posts from data: {str(e)}")
            logger.error(f"Data structure: {json.dumps(data, indent=2)}")
            return [] 