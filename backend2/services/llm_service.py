"""Service for working with LLM APIs using LangGraph for flow control"""

import os
import logging
from typing import List, Optional, TypedDict, Annotated, Dict
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolExecutor
from openai import AsyncOpenAI
import json
from operator import itemgetter
from locales.language_utils import get_strings
from locales.ascii_art import REPORT_HEADER, REPORT_FOOTER, get_block_border
from utils.telegram_utils import send_telegram_message

logger = logging.getLogger(__name__)

class ThreadsAnalysisState(TypedDict):
    """State for threads analysis flow"""
    posts: List[str]
    language: str
    telegram_id: int
    analysis: Optional[str]

class LLMService:
    """Service for interacting with LLM APIs"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.workflow = self._create_analysis_workflow()
        
    async def _analyze_profile(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Analyze profile with single comprehensive prompt"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            
            # Get the appropriate prompt from strings module
            system_prompt = strings.system_prompt

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": posts_text}
                ],
                temperature=0.89
            )
            state['analysis'] = response.choices[0].message.content
            return state
        except Exception as e:
            logger.error(f"Error analyzing profile: {e}")
            state['analysis'] = "Could not analyze profile"
            return state

    def _create_analysis_workflow(self) -> Graph:
        """Create analysis workflow graph"""
        
        # Create workflow graph
        workflow = StateGraph(ThreadsAnalysisState)
        
        # Add single analysis node
        workflow.add_node("analyze_profile", self._analyze_profile)
        
        # Set entry and end nodes
        workflow.set_entry_point("analyze_profile")
        workflow.set_finish_point("analyze_profile")
        
        return workflow.compile()

    def format_report(self, state: Dict) -> str:
        """Format full analysis report with ASCII styling and HTML tags"""
        try:
            # Start with header
            sections = [self._format_header()]
            
            # Add the analysis text
            if 'analysis' in state:
                analysis_text = state['analysis']
                sections.append(analysis_text)
            
            # Add footer
            sections.append(self._format_footer())
            
            # Join all sections with single newlines to make it more compact
            return "\n".join(sections)
            
        except Exception as e:
            logger.error(f"Error formatting report: {e}")
            logger.error(f"State: {state}")
            return "Error formatting report"

    def _format_header(self) -> str:
        """Create ASCII header for the report with HTML tags"""
        return "\n".join(f"<code>{line}</code>" for line in REPORT_HEADER.split("\n"))

    def _format_footer(self) -> str:
        """Create ASCII footer for the report with HTML tags"""
        return "\n".join(f"<code>{line}</code>" for line in REPORT_FOOTER.split("\n"))

    async def send_analysis_to_user(self, telegram_id: int, analysis_report: Dict, language: str) -> bool:
        """Format and send analysis to user"""
        try:
            # Format report
            formatted_report = self.format_report(analysis_report)
            
            # Get strings for language
            strings = get_strings(language)
            
            # Send report to user
            from routers.telegram import split_and_send_message
            return await split_and_send_message(
                telegram_id=telegram_id,
                text=strings.THREADS_ANALYSIS_COMPLETE.format(analysis_text=formatted_report),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending analysis: {e}")
            # Send error message
            strings = get_strings(language)
            await send_telegram_message(
                telegram_id=telegram_id,
                text=strings.THREADS_ANALYSIS_ERROR,
                parse_mode="HTML"
            )
            return False

    async def analyze_threads_profile(self, posts: List[str], telegram_id: int, language: str = 'ru') -> Optional[Dict]:
        """Run threads profile analysis workflow"""
        try:
            # Initialize state
            state = {
                'posts': posts,
                'language': language,
                'telegram_id': telegram_id,
                'analysis': None
            }
            
            # Run workflow with async nodes
            final_state = await self.workflow.ainvoke(state)
            
            # Remove posts from final state before returning
            analysis_report = {k: v for k, v in final_state.items() if k != 'posts'}
            
            # Send progress messages
            try:
                await send_telegram_message(
                    telegram_id=telegram_id,
                    text=get_strings(language).THREADS_ANALYSIS_COMPLETE.format(
                        analysis_text=self.format_report(analysis_report)
                    )
                )
            except Exception as e:
                logger.error(f"Error sending progress message: {e}")
            
            return analysis_report
        except Exception as e:
            logger.error(f"Error in analysis workflow: {e}")
            return None 