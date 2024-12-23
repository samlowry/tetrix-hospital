import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import json

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, redis: Redis, session: AsyncSession = None):
        self.redis = redis
        self.session = session
        self.tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._last_execution: Dict[str, datetime] = {}

    async def start(self):
        """Start the scheduler"""
        if self._running:
            return
        self._running = True
        logger.info("Starting scheduler service...")
        
        # Initial sequential execution of all tasks
        logger.info("Executing initial tasks sequentially...")
        tasks_to_init = [
            ("leaderboard", self._update_leaderboard),  # Move leaderboard first
            ("price_and_cap", self._fetch_price_and_cap),
            ("holders", self._fetch_holders),
            ("volume", self._fetch_volume)
        ]
        
        for name, func in tasks_to_init:
            logger.info(f"Initial execution of {name}")
            await self._execute_task(name, func)
            logger.info(f"Initial {name} task completed")
        
        logger.info("All initial tasks completed, starting periodic scheduling...")
        
        # Start periodic tasks
        self.tasks["price_and_cap"] = asyncio.create_task(self._schedule_task(
            "price_and_cap", self._fetch_price_and_cap, timedelta(minutes=1)
        ))
        self.tasks["holders"] = asyncio.create_task(self._schedule_task(
            "holders", self._fetch_holders, timedelta(minutes=1)
        ))
        self.tasks["volume"] = asyncio.create_task(self._schedule_task(
            "volume", self._fetch_volume, timedelta(minutes=10)
        ))
        self.tasks["leaderboard"] = asyncio.create_task(self._schedule_task(
            "leaderboard", self._update_leaderboard, timedelta(hours=1)
        ))

    async def stop(self):
        """Stop the scheduler"""
        self._running = False
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
        logger.info("Scheduler service stopped")

    async def _schedule_task(self, name: str, func: Callable, interval: timedelta):
        """Schedule a periodic task"""
        while self._running:
            try:
                last_run = self._last_execution.get(name)
                now = datetime.utcnow()
                
                if last_run:
                    # Calculate number of missed intervals
                    time_since_last = now - last_run
                    missed_intervals = time_since_last.total_seconds() / interval.total_seconds()
                    
                    if missed_intervals > 1:
                        # If multiple intervals missed, log it and execute only once
                        logger.info(f"Task {name} missed {int(missed_intervals)} intervals, executing latest")
                        await self._execute_task(name, func)
                    else:
                        # Calculate time until next run
                        next_run = last_run + interval
                        if next_run > now:
                            delay = (next_run - now).total_seconds()
                            if delay > 0:
                                await asyncio.sleep(delay)
                        await self._execute_task(name, func)
                else:
                    # First run
                    await self._execute_task(name, func)
                
                # Sleep for the interval
                await asyncio.sleep(interval.total_seconds())
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduled task {name}: {e}", exc_info=True)
                await asyncio.sleep(30)  # Wait before retry

    async def _execute_task(self, name: str, func: Callable):
        """Execute a task and update its last execution time"""
        try:
            start_time = datetime.utcnow()
            logger.info(f"Executing task {name} at {start_time}")
            await func()
            self._last_execution[name] = start_time
            logger.info(f"Task {name} completed successfully")
        except Exception as e:
            logger.error(f"Failed to execute task {name}: {e}", exc_info=True)

    async def _fetch_price_and_cap(self):
        """Fetch price and market cap with extended cache time"""
        from .tetrix_service import TetrixService
        tetrix = TetrixService(self.redis, self.session)
        data = await tetrix._fetch_price_and_cap()
        await self.redis.setex("tetrix:price", 90, json.dumps(data))  # 90 seconds cache

    async def _fetch_holders(self):
        """Fetch holders count with extended cache time"""
        from .tetrix_service import TetrixService
        tetrix = TetrixService(self.redis, self.session)
        data = await tetrix._fetch_holders()
        await self.redis.setex("tetrix:holders", 90, json.dumps(data))  # 90 seconds cache

    async def _fetch_volume(self):
        """Fetch volume with extended cache time"""
        from .tetrix_service import TetrixService
        tetrix = TetrixService(self.redis, self.session)
        data = await tetrix._fetch_volume()
        await self.redis.setex("tetrix:volume", 660, json.dumps(data))  # 11 minutes cache

    async def _update_leaderboard(self):
        """Update leaderboard snapshot"""
        from .leaderboard_service import LeaderboardService
        leaderboard_service = LeaderboardService(self.session)
        await leaderboard_service.ensure_populated()  # Check and populate if empty
        await leaderboard_service.update_leaderboard()