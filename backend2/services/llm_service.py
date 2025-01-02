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
    vibe_check: Optional[str]
    content_gems: Optional[str]
    social_energy: Optional[str]
    character_arc: Optional[str]
    final_report: Optional[str]

class LLMService:
    """Service for interacting with LLM APIs"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.workflow = self._create_analysis_workflow()
        
    async def _analyze_vibe(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Do a vibe check of the profile"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
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

    async def _analyze_content(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Find the best content gems"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
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

    async def _analyze_social(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Analyze social energy and interaction style"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
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

    async def _analyze_character(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Create a character profile"""
        try:
            strings = get_strings(state['language'])
            posts_text = "\n\n".join(f"Post: {post}" for post in state['posts'])
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
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

    async def _create_final_report(self, state: ThreadsAnalysisState) -> ThreadsAnalysisState:
        """Create final viral-worthy report"""
        try:
            strings = get_strings(state['language'])
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
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

    def _format_block(self, title: str, content: List[str]) -> str:
        """Format a single analysis block with ASCII frame"""
        width = 50  # Общая ширина блока
        
        # Получаем рамки из ascii_art
        top, title_template, bottom = get_block_border(width)
        title_line = title_template.format(title=title)
        
        # Форматируем контент без боковых рамок
        content_lines = []
        for line in content:
            content_lines.append(f"  {line}")  # Добавляем отступ в два пробела
        
        # Собираем блок
        return "\n".join([
            top,
            title_line,
            "",  # Пустая строка после заголовка
            *content_lines,
            "",  # Пустая строка перед нижней рамкой
            bottom
        ])

    def _format_header(self) -> str:
        """Create ASCII header for the report"""
        return REPORT_HEADER

    def _format_footer(self) -> str:
        """Create ASCII footer for the report"""
        return REPORT_FOOTER

    def format_report(self, state: Dict) -> str:
        """Format full analysis report with ASCII styling"""
        try:
            # Start with header
            sections = [self._format_header()]
            
            # Get the blocks from final_report if it exists, otherwise use direct state values
            if 'final_report' in state:
                try:
                    # Parse the JSON string if it's a string
                    if isinstance(state['final_report'], str):
                        report_data = json.loads(state['final_report'])
                    else:
                        report_data = state['final_report']
                        
                    blocks = report_data.get('blocks', {})
                    final_analysis = report_data.get('final_analysis', {})
                    
                    # Format blocks in order
                    ordered_blocks = sorted(
                        [(name, data) for name, data in blocks.items()],
                        key=lambda x: x[1].get('order', 999)
                    )
                    
                    for _, block_data in ordered_blocks:
                        title = block_data.get('title', '').upper()
                        content = block_data.get('content', [])
                        sections.append(self._format_block(
                            title,
                            content
                        ))
                    
                    # Add final analysis if exists
                    if final_analysis:
                        final_content = [
                            final_analysis.get('opener', ''),
                            *final_analysis.get('main_points', []),
                            '',
                            final_analysis.get('call_to_action', '')
                        ]
                        sections.append(self._format_block('FINAL THOUGHTS', final_content))
                        
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing final_report JSON: {e}")
                    # Fallback to direct state values
                    blocks = [
                        ("VIBE CHECK", state.get('vibe_check', 'Could not analyze vibe')),
                        ("CONTENT GEMS", state.get('content_gems', 'Could not analyze content')),
                        ("SOCIAL ENERGY", state.get('social_energy', 'Could not analyze social style')),
                        ("CHARACTER ARC", state.get('character_arc', 'Could not analyze character'))
                    ]
                    for title, content in blocks:
                        sections.append(self._format_block(
                            title,
                            content.split('\n') if content else ['Analysis not available']
                        ))
            else:
                # Use direct state values if no final_report
                blocks = [
                    ("VIBE CHECK", state.get('vibe_check', 'Could not analyze vibe')),
                    ("CONTENT GEMS", state.get('content_gems', 'Could not analyze content')),
                    ("SOCIAL ENERGY", state.get('social_energy', 'Could not analyze social style')),
                    ("CHARACTER ARC", state.get('character_arc', 'Could not analyze character'))
                ]
                for title, content in blocks:
                    sections.append(self._format_block(
                        title,
                        content.split('\n') if content else ['Analysis not available']
                    ))
            
            # Add footer
            sections.append(self._format_footer())
            
            # Add final message
            sections.append("\nЗнаешь, общение с тобой было таким вдохновляющим! 🌟")
            sections.append("Я обязательно свяжусь с тобой позже, чтобы сообщить о своём решении насчёт работы...")
            sections.append("\nА пока — спасибо за этот удивительный опыт! 💫")
            
            # Join all sections with single newlines to make it more compact
            return "\n".join(sections)
            
        except Exception as e:
            logger.error(f"Error formatting report: {e}")
            return "Error formatting report"

    async def send_analysis_to_user(self, telegram_id: int, json_report: Dict, language: str) -> bool:
        """Format and send analysis to user"""
        try:
            # Форматируем отчет
            formatted_report = self.format_report(json_report)
            
            # Получаем строки для нужного языка
            strings = get_strings(language)
            
            # Отправляем отчет пользователю
            from routers.telegram import split_and_send_message
            return await split_and_send_message(
                telegram_id=telegram_id,
                text=strings.THREADS_ANALYSIS_COMPLETE.format(analysis_text=formatted_report)
            )
        except Exception as e:
            logger.error(f"Error sending analysis: {e}")
            # Отправляем сообщение об ошибке
            strings = get_strings(language)
            await send_telegram_message(
                telegram_id=telegram_id,
                text=strings.THREADS_ANALYSIS_ERROR,
                parse_mode="Markdown"
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
                'vibe_check': None,
                'content_gems': None,
                'social_energy': None,
                'character_arc': None,
                'final_report': None
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