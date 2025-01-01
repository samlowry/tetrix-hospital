"""Service for working with OpenAI API"""

import os
import logging
import openai
from typing import List, Dict

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for interacting with OpenAI API"""
    
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
    async def analyze_threads_profile(self, posts: List[Dict]) -> str:
        """Analyze user's Threads posts and generate personality report"""
        try:
            # Prepare posts for analysis
            posts_text = []
            for post in posts:
                posts_text.append(f"Post: {post['text']}\nLikes: {post['likes']}, Replies: {post['replies']}\n")
            
            # Create prompt for analysis
            prompt = f"""Analyze these Threads posts and create a fun, engaging personality report. 
            Focus on:
            1. Writing style and tone
            2. Main topics and interests
            3. Engagement with others
            4. Unique personality traits
            5. Potential fit for representing TETRIX

            Posts to analyze:
            {"".join(posts_text)}

            Write the analysis in a friendly, personal tone, as if TETRIX AI is excited to learn about this person.
            Make it engaging and fun, but also professional and respectful.
            Keep the length to about 3-4 paragraphs.
            """
            
            # Get analysis from OpenAI
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are TETRIX, an AI memecoin analyzing potential representatives."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error analyzing Threads profile: {e}")
            return None 