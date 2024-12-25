import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import json

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, redis: Redis, session_factory: async_sessionmaker):
        self.redis = redis
        self.session_factory = session_factory
        self.tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._last_execution: Dict[str, datetime] = {}

    async def _execute_task(self, task_name: str):
        """Execute a task and log its execution"""
        logger.info(f"Executing task {task_name} at {datetime.now()}")
        
        async with self.session_factory() as session:
            try:
                if task_name == "leaderboard":
                    from .leaderboard_service import LeaderboardService
                    leaderboard_service = LeaderboardService(session)
                    await leaderboard_service.ensure_populated()
                    await leaderboard_service.update_leaderboard()
                elif task_name == "price_and_cap":
                    await self._fetch_price_and_cap(session)
                elif task_name == "holders":
                    await self._fetch_holders(session)
                elif task_name == "volume":
                    await self._fetch_volume(session)
                    
                await session.commit()
                logger.info(f"Task {task_name} completed successfully")
            except Exception as e:
                logger.error(f"Error in task {task_name}: {e}", exc_info=True)
                await session.rollback()
                raise

    async def _fetch_price_and_cap(self, session: AsyncSession):
        """Fetch price and market cap with extended cache time"""
        from .tetrix_service import TetrixService
        tetrix = TetrixService(self.redis, session)
        data = await tetrix._fetch_price_and_cap()
        await self.redis.setex("tetrix:price", 90, json.dumps(data))  # 90 seconds cache

    async def _fetch_holders(self, session: AsyncSession):
        """Fetch holders count with extended cache time"""
        from .tetrix_service import TetrixService
        tetrix = TetrixService(self.redis, session)
        data = await tetrix._fetch_holders()
        await self.redis.setex("tetrix:holders", 90, json.dumps(data))  # 90 seconds cache

    async def _fetch_volume(self, session: AsyncSession):
        """Fetch volume with extended cache time"""
        from .tetrix_service import TetrixService
        tetrix = TetrixService(self.redis, session)
        data = await tetrix._fetch_volume()
        await self.redis.setex("tetrix:volume", 660, json.dumps(data))  # 11 minutes cache

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
            "price_and_cap": {"interval": 60, "last_execution": None},  # Every minute
            "holders": {"interval": 60, "last_execution": None},        # Every minute
            "volume": {"interval": 600, "last_execution": None}         # Every 10 minutes
        }

        for task_name in self.tasks:
            asyncio.create_task(self._schedule_task(task_name))

    async def _ensure_metrics_populated(self):
        """Check if metrics exist in Redis and populate if missing"""
        async with self.session_factory() as session:
            # Check price and cap
            price = await self.redis.get("tetrix:price")
            cap = await self.redis.get("tetrix:cap")
            if not price or not cap:
                logger.info("Price or cap missing in Redis, fetching...")
                await self._fetch_price_and_cap(session)
            else:
                logger.info("Price and cap exist in Redis, skipping initial fetch")

            # Check holders
            holders = await self.redis.get("tetrix:holders")
            if not holders:
                logger.info("Holders count missing in Redis, fetching...")
                await self._fetch_holders(session)
            else:
                logger.info("Holders count exists in Redis, skipping initial fetch")

            # Check volume
            volume = await self.redis.get("tetrix:volume")
            if not volume:
                logger.info("Volume missing in Redis, fetching...")
                await self._fetch_volume(session)
            else:
                logger.info("Volume exists in Redis, skipping initial fetch")

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