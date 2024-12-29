import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import json

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Service responsible for scheduling and executing periodic tasks like 
    updating leaderboards, fetching metrics, and holder information
    """
    def __init__(self, redis: Redis, session_factory: async_sessionmaker):
        """
        Initialize scheduler service with Redis connection and database session factory
        
        Args:
            redis: Redis connection instance for caching
            session_factory: SQLAlchemy async session maker for database operations
        """
        self.redis = redis  # Redis instance for caching
        self.session_factory = session_factory  # Database session factory
        self.tasks: Dict[str, asyncio.Task] = {}  # Dictionary to store running tasks
        self._running = False  # Flag to track scheduler running state
        self._last_execution: Dict[str, datetime] = {}  # Track last execution time of tasks

    async def _execute_task(self, task_name: str):
        """
        Execute a scheduled task and handle its lifecycle
        
        Args:
            task_name: Name of the task to execute (leaderboard/metrics/holders)
        """
        logger.info(f"Executing task {task_name} at {datetime.now()}")
        
        async with self.session_factory() as session:
            try:
                if task_name == "leaderboard":
                    from .leaderboard_service import LeaderboardService
                    leaderboard_service = LeaderboardService(session)
                    await leaderboard_service.ensure_populated()
                    await leaderboard_service.update_leaderboard()
                elif task_name == "metrics":
                    await self._fetch_metrics(session)
                elif task_name == "holders":
                    await self._fetch_holders(session)
                    
                await session.commit()
                logger.info(f"Task {task_name} completed successfully")
            except Exception as e:
                logger.error(f"Error in task {task_name}: {e}", exc_info=True)
                await session.rollback()
                raise

    async def _fetch_metrics(self, session: AsyncSession):
        """
        Fetch and cache price and volume data from DexScreener
        
        Args:
            session: Active database session for the operation
        """
        from .tetrix_service import TetrixService
        tetrix = TetrixService(self.redis, session)
        data = await tetrix._fetch_dexscreener_data()
        await self.redis.setex("tetrix:dexscreener", 90, json.dumps(data))  # Cache for 90 seconds

    async def _fetch_holders(self, session: AsyncSession):
        """
        Fetch and cache the current count of token holders
        
        Args:
            session: Active database session for the operation
        """
        from .tetrix_service import TetrixService
        tetrix = TetrixService(self.redis, session)
        data = await tetrix._fetch_holders()
        await self.redis.setex("tetrix:holders", 90, json.dumps(data))  # 90 seconds cache

    async def start(self):
        """Start the scheduler"""
        logger.info("Starting scheduler service...")
        logger.info("Executing initial tasks sequentially...")

        # First update leaderboard
        logger.info("Initial execution of leaderboard")
        await self._execute_task("leaderboard")
        logger.info("Initial leaderboard task completed")

        # Then ensure metrics are populated
        await self._ensure_metrics_populated()

        logger.info("All initial tasks completed, starting periodic scheduling...")

        # Schedule periodic tasks
        self.tasks = {
            "leaderboard": {"interval": 3600, "last_execution": None},  # Every hour
            "metrics": {"interval": 60, "last_execution": None},        # Every minute
            "holders": {"interval": 60, "last_execution": None}         # Every minute
        }

        for task_name in self.tasks:
            asyncio.create_task(self._schedule_task(task_name))

    async def _ensure_metrics_populated(self):
        """Check if metrics exist in Redis and populate if missing"""
        async with self.session_factory() as session:
            # Check DexScreener data
            dex_data = await self.redis.get("tetrix:dexscreener")
            if not dex_data:
                logger.info("DexScreener data missing in Redis, fetching...")
                await self._fetch_metrics(session)
            else:
                logger.info("DexScreener data exists in Redis, skipping initial fetch")

            # Check holders
            holders = await self.redis.get("tetrix:holders")
            if not holders:
                logger.info("Holders count missing in Redis, fetching...")
                await self._fetch_holders(session)
            else:
                logger.info("Holders count exists in Redis, skipping initial fetch")

    async def _schedule_task(self, task_name: str):
        """Schedule a task to run periodically"""
        while True:
            try:
                await self._execute_task(task_name)
                self.tasks[task_name]["last_execution"] = datetime.now()
                await asyncio.sleep(self.tasks[task_name]["interval"])
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in task {task_name}: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait a minute before retrying