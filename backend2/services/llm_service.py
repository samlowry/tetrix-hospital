"""Service for working with LLM APIs using LangGraph for flow control"""

import os
import logging
from typing import List, Optional, TypedDict, Annotated, Dict
from langgraph.graph import Graph, StateGraph
from langgraph.prebuilt import ToolExecutor
import openai
import json
from operator import itemgetter
from locales.i18n import get_strings
from locales.ascii_art import REPORT_HEADER, REPORT_FOOTER, get_block_border
from routers.telegram import send_telegram_message

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

class LLMService:
    """Service for interacting with LLM APIs"""
    
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

    def format_report(self, json_report: Dict) -> str:
        """Format full analysis report with ASCII styling"""
        try:
            # Начинаем с заголовка
            sections = [self._format_header()]
            
            # Сортируем и форматируем основные блоки
            blocks = json_report["blocks"]
            sorted_blocks = sorted(blocks.items(), key=lambda x: x[1]["order"])
            
            for _, block in sorted_blocks:
                sections.append(self._format_block(
                    block["title"],
                    block["content"]
                ))
            
            # Форматируем финальный анализ
            final = json_report["final_analysis"]
            final_text = [
                "🚀 FINAL ANALYSIS:",
                "",
                final["opener"],
                "",
                *final["main_points"],
                "",
                final["call_to_action"]
            ]
            sections.append("\n".join(final_text))
            
            # Добавляем футер
            sections.append(self._format_footer())
            
            # Соединяем все секции с двойным переносом строки
            return "\n\n".join(sections)
            
        except Exception as e:
            logger.error(f"Error formatting report: {e}")
            return "Error formatting report"

    async def send_analysis_to_user(self, telegram_id: int, json_report: Dict, language: str) -> bool:
        """Format and send analysis to user"""
        try:
            # Форматируем отчет
            formatted_report = self.format_report(json_report)
            
            # Отправляем сообщение пользователю
            await send_telegram_message(
                chat_id=telegram_id,
                text=formatted_report,
                parse_mode="Markdown"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending analysis: {e}")
            # Отправляем сообщение об ошибке
            strings = get_strings(language)
            await send_telegram_message(
                chat_id=telegram_id,
                text=strings.THREADS_ANALYSIS_ERROR,
                parse_mode="Markdown"
            )
            return False
        
    async def analyze_threads_profile(self, posts: List[str], telegram_id: int, language: str = 'en') -> bool:
        """Analyze user's Threads posts and generate personality report"""
        try:
            strings = get_strings(language)
            
            # Отправляем сообщение о начале анализа
            await send_telegram_message(
                chat_id=telegram_id,
                text=strings.THREADS_ANALYZING,
                parse_mode="Markdown"
            )
            
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
            
            # Get report
            report = final_state.get('final_report')
            if not report:
                await send_telegram_message(
                    chat_id=telegram_id,
                    text=strings.THREADS_ANALYSIS_ERROR,
                    parse_mode="Markdown"
                )
                return False
                
            # Parse JSON report
            try:
                json_report = json.loads(report)
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON report")
                await send_telegram_message(
                    chat_id=telegram_id,
                    text=strings.THREADS_ANALYSIS_ERROR,
                    parse_mode="Markdown"
                )
                return False
                
            # Send formatted report to user
            return await self.send_analysis_to_user(telegram_id, json_report, language)
            
        except Exception as e:
            logger.error(f"Error in analysis workflow: {e}")
            # Отправляем сообщение об ошибке
            strings = get_strings(language)
            await send_telegram_message(
                chat_id=telegram_id,
                text=strings.THREADS_ANALYSIS_ERROR,
                parse_mode="Markdown"
            )
            return False 