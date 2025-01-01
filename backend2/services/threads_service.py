"""Service for working with Threads API"""

import aiohttp
import logging
from typing import Optional, Dict, List
import json
import os

logger = logging.getLogger(__name__)

class ThreadsService:
    """Service for interacting with Threads API"""
    
    def __init__(self):
        self.base_url = "https://www.threads.net/api/graphql"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "X-IG-App-ID": "238260118697367"  # Threads web app ID
        }

    async def get_user_id(self, username: str) -> Optional[str]:
        """Get user ID by username"""
        async with aiohttp.ClientSession() as session:
            try:
                # First get user ID from username
                params = {
                    "q": f"""
                    query SearchBarQuery($username: String!) {{
                        one_to_one_threads_user(username: $username) {{
                            id
                            username
                        }}
                    }}
                    """,
                    "variables": json.dumps({"username": username})
                }
                
                async with session.get(
                    self.base_url,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error getting user ID for {username}: {response.status}")
                        return None
                        
                    data = await response.json()
                    user = data.get("data", {}).get("one_to_one_threads_user")
                    if not user:
                        logger.error(f"User {username} not found")
                        return None
                        
                    return user.get("id")
                    
            except Exception as e:
                logger.error(f"Error getting user ID: {e}")
                return None

    async def get_user_posts(self, user_id: str, limit: int = 25) -> List[Dict]:
        """Get user's posts"""
        async with aiohttp.ClientSession() as session:
            try:
                params = {
                    "q": f"""
                    query ThreadsProfileQuery($userId: String!, $first: Int!) {{
                        mediaData: one_to_one_threads_media(userID: $userId, first: $first) {{
                            edges {{
                                node {{
                                    id
                                    caption
                                    taken_at
                                    like_count
                                    reply_count
                                }}
                            }}
                        }}
                    }}
                    """,
                    "variables": json.dumps({
                        "userId": user_id,
                        "first": limit
                    })
                }
                
                async with session.get(
                    self.base_url,
                    headers=self.headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        logger.error(f"Error getting posts for user {user_id}: {response.status}")
                        return []
                        
                    data = await response.json()
                    edges = data.get("data", {}).get("mediaData", {}).get("edges", [])
                    
                    posts = []
                    for edge in edges:
                        node = edge.get("node", {})
                        if node and node.get("caption"):
                            posts.append({
                                "id": node.get("id"),
                                "text": node.get("caption"),
                                "timestamp": node.get("taken_at"),
                                "likes": node.get("like_count"),
                                "replies": node.get("reply_count")
                            })
                    
                    return posts
                    
            except Exception as e:
                logger.error(f"Error getting user posts: {e}")
                return [] 