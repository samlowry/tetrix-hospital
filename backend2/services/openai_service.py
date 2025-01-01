"""Service for working with OpenAI API using LangGraph for flow control"""

import os
import logging
from typing import List, Optional, TypedDict, Annotated
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolExecutor
import openai
from operator import itemgetter
from locales.i18n import get_strings

logger = logging.getLogger(__name__)

class ThreadsAnalysisState(TypedDict):
    """State for threads analysis flow"""
    posts: List[str]
    language: str
    vibe_check: Optional[str]
    content_gems: Optional[str]
    social_energy: Optional[str]
    character_arc: Optional[str]
    final_report: Optional[str]

class OpenAIService:
    """Service for interacting with OpenAI API"""
    
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.workflow = self._create_analysis_workflow()
        
    def _analyze_vibe(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Do a vibe check of the profile"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": strings.THREADS_SYSTEM_VIBE},
                    {"role": "user", "content": strings.THREADS_PROMPT_VIBE.format(posts_text=posts_text)}
                ],
                temperature=0.9
            )
            state['vibe_check'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing vibe: {e}")
            state['vibe_check'] = "Could not analyze vibe"
            return state

    def _analyze_content(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Find the best content gems"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": strings.THREADS_SYSTEM_CONTENT},
                    {"role": "user", "content": strings.THREADS_PROMPT_CONTENT.format(posts_text=posts_text)}
                ],
                temperature=0.9
            )
            state['content_gems'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            state['content_gems'] = "Could not analyze content"
            return state

    def _analyze_social(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Analyze social energy and interaction style"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": strings.THREADS_SYSTEM_SOCIAL},
                    {"role": "user", "content": strings.THREADS_PROMPT_SOCIAL.format(posts_text=posts_text)}
                ],
                temperature=0.9
            )
            state['social_energy'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing social style: {e}")
            state['social_energy'] = "Could not analyze social style"
            return state

    def _analyze_character(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Create a character profile"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": strings.THREADS_SYSTEM_CHARACTER},
                    {"role": "user", "content": strings.THREADS_PROMPT_CHARACTER.format(posts_text=posts_text)}
                ],
                temperature=0.9
            )
            state['character_arc'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing character: {e}")
            state['character_arc'] = "Could not analyze character"
            return state

    def _create_final_report(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Create final viral-worthy report"""
        try:
            strings = get_strings(state['language'])
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": strings.THREADS_SYSTEM_FINAL},
                    {"role": "user", "content": strings.THREADS_PROMPT_FINAL.format(
                        vibe_check=state['vibe_check'],
                        content_gems=state['content_gems'],
                        social_energy=state['social_energy'],
                        character_arc=state['character_arc']
                    )}
                ],
                temperature=0.9
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
        workflow.add_node("analyze_vibe", self._analyze_vibe)
        workflow.add_node("analyze_content", self._analyze_content)
        workflow.add_node("analyze_social", self._analyze_social)
        workflow.add_node("analyze_character", self._analyze_character)
        workflow.add_node("create_report", self._create_final_report)
        
        # Define edges
        workflow.add_edge("analyze_vibe", "analyze_content")
        workflow.add_edge("analyze_content", "analyze_social")
        workflow.add_edge("analyze_social", "analyze_character")
        workflow.add_edge("analyze_character", "create_report")
        
        # Set entry and end nodes
        workflow.set_entry_point("analyze_vibe")
        workflow.set_finish_point("create_report")
        
        return workflow.compile()
        
    async def analyze_threads_profile(self, posts: List[str], language: str = 'en') -> Optional[str]:
        """Analyze user's Threads posts and generate personality report"""
        try:
            # Initialize state
            state = ThreadsAnalysisState(
                posts=posts,
                language=language,
                vibe_check=None,
                content_gems=None,
                social_energy=None,
                character_arc=None,
                final_report=None
            )
            
            # Run workflow
            final_state = self.workflow.invoke(state)
            
            return final_state.get('final_report')
            
        except Exception as e:
            logger.error(f"Error in analysis workflow: {e}")
            return None 