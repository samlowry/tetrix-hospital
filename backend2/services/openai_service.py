"""Service for working with OpenAI API using LangGraph for flow control"""

import os
import logging
from typing import List, Optional, TypedDict, Annotated
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolExecutor
import openai
from operator import itemgetter

logger = logging.getLogger(__name__)

class ThreadsAnalysisState(TypedDict):
    """State for threads analysis flow"""
    posts: List[str]
    writing_style: Optional[str]
    topics: Optional[str]
    engagement: Optional[str]
    personality: Optional[str]
    final_report: Optional[str]

class OpenAIService:
    """Service for interacting with OpenAI API"""
    
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.workflow = self._create_analysis_workflow()
        
    def _analyze_writing_style(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Analyze writing style and tone"""
        try:
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are TETRIX, analyzing writing style and tone."},
                    {"role": "user", "content": f"""Analyze the writing style and tone in these posts:
                    {posts_text}
                    
                    Focus on:
                    - Language formality/informality
                    - Use of humor/emojis
                    - Sentence structure
                    - Vocabulary choices
                    
                    Keep response focused and under 100 words."""}
                ],
                temperature=0.7
            )
            state['writing_style'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing writing style: {e}")
            state['writing_style'] = "Could not analyze writing style"
            return state

    def _analyze_topics(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Analyze main topics and interests"""
        try:
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are TETRIX, analyzing topics and interests."},
                    {"role": "user", "content": f"""Identify main topics and interests from these posts:
                    {posts_text}
                    
                    List key themes and subjects the person discusses.
                    Keep response focused and under 100 words."""}
                ],
                temperature=0.7
            )
            state['topics'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing topics: {e}")
            state['topics'] = "Could not analyze topics"
            return state

    def _analyze_engagement(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Analyze engagement with others"""
        try:
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are TETRIX, analyzing social engagement."},
                    {"role": "user", "content": f"""Analyze how this person engages with others:
                    {posts_text}
                    
                    Focus on:
                    - Response style to others
                    - Community interaction
                    - Conversation patterns
                    
                    Keep response focused and under 100 words."""}
                ],
                temperature=0.7
            )
            state['engagement'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing engagement: {e}")
            state['engagement'] = "Could not analyze engagement"
            return state

    def _analyze_personality(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Analyze personality traits"""
        try:
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are TETRIX, analyzing personality traits."},
                    {"role": "user", "content": f"""Identify key personality traits from these posts:
                    {posts_text}
                    
                    Focus on:
                    - Character strengths
                    - Communication style
                    - Values and beliefs
                    - Potential as TETRIX representative
                    
                    Keep response focused and under 100 words."""}
                ],
                temperature=0.7
            )
            state['personality'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing personality: {e}")
            state['personality'] = "Could not analyze personality"
            return state

    def _create_final_report(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Create final analysis report"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are TETRIX, creating final personality report."},
                    {"role": "user", "content": f"""Create an engaging final report based on these analyses:

                    Writing Style: {state['writing_style']}
                    Topics: {state['topics']}
                    Engagement: {state['engagement']}
                    Personality: {state['personality']}
                    
                    Write in a friendly, excited tone as TETRIX AI.
                    Make it fun and engaging while staying professional.
                    Keep it to 3-4 paragraphs."""}
                ],
                temperature=0.7
            )
            state['final_report'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error creating final report: {e}")
            state['final_report'] = "Could not create final report"
            return state

    def _create_analysis_workflow(self) -> Graph:
        """Create analysis workflow graph"""
        
        # Create workflow graph
        workflow = StateGraph(ThreadsAnalysisState)
        
        # Add nodes
        workflow.add_node("analyze_writing", self._analyze_writing_style)
        workflow.add_node("analyze_topics", self._analyze_topics)
        workflow.add_node("analyze_engagement", self._analyze_engagement)
        workflow.add_node("analyze_personality", self._analyze_personality)
        workflow.add_node("create_report", self._create_final_report)
        
        # Define edges
        workflow.add_edge("analyze_writing", "analyze_topics")
        workflow.add_edge("analyze_topics", "analyze_engagement")
        workflow.add_edge("analyze_engagement", "analyze_personality")
        workflow.add_edge("analyze_personality", "create_report")
        
        # Set entry and end nodes
        workflow.set_entry_point("analyze_writing")
        workflow.set_finish_point("create_report")
        
        return workflow.compile()
        
    async def analyze_threads_profile(self, posts: List[str]) -> Optional[str]:
        """Analyze user's Threads posts and generate personality report"""
        try:
            # Initialize state
            state = ThreadsAnalysisState(
                posts=posts,
                writing_style=None,
                topics=None,
                engagement=None,
                personality=None,
                final_report=None
            )
            
            # Run workflow
            final_state = self.workflow.invoke(state)
            
            return final_state.get('final_report')
            
        except Exception as e:
            logger.error(f"Error in analysis workflow: {e}")
            return None 