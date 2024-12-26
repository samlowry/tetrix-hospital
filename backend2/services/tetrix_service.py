from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiohttp
import logging
import json
from datetime import datetime, timedelta
from models.metrics import TetrixMetrics
from typing import Optional
from locales.emotions import get_emotion_by_percentage

logger = logging.getLogger(__name__)

TON_API_URL = "https://tonapi.io/v2"
TON_API_KEY = "AHK6ZFZUS4TIGHQAAAAH3XFVS5TRIQABRO6J2HZ6ST4N43ZQTXHAYBBQ2IETD54M4PSRYBQ"
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex"

TETRIX_ADDRESS = "EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C"
TETRIX_POOL = "EQDzf3WUJvNqlXnzggvxTDweWW7l7DaZ68qyvRVx1a2xm0Zy"
TOTAL_SUPPLY = 1_000_000_000

# Constants for 100% values
MAX_HOLDERS = 100_000  # 100K holders = 100% health
MAX_CAP = 1_000_000  # $1M cap = 100% strength
INITIAL_MAX_VOLUME = 0  # Initial max volume is 0
CACHE_TIME = 60  # 1 minute cache for all metrics
VOLUME_CACHE_TIME = 600  # 10 minutes cache for volume

class TetrixService:
    def __init__(self, redis: Redis, session: AsyncSession = None):
        self.redis = redis
        self.session = session

    async def _ensure_max_volume_exists(self):
        """Ensure max volume exists in database with initial value"""
        if not self.session:
            return INITIAL_MAX_VOLUME

        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(TetrixMetrics).where(TetrixMetrics.key == "max_volume")
                )
                max_volume = result.scalar_one_or_none()
                
                if not max_volume:
                    max_volume = TetrixMetrics(
                        key="max_volume",
                        value=INITIAL_MAX_VOLUME
                    )
                    self.session.add(max_volume)
                    await self.session.commit()
                    return INITIAL_MAX_VOLUME
                
                return max_volume.value
        except Exception as e:
            logger.error(f"Error in ensure_max_volume: {e}")
            await self.session.rollback()
            raise

    async def _update_max_volume(self, new_volume: float):
        """Update max volume in database if needed"""
        if not self.session:
            return

        try:
            async with self.session.begin():
                result = await self.session.execute(
                    select(TetrixMetrics).where(TetrixMetrics.key == "max_volume")
                )
                max_volume = result.scalar_one_or_none()
                
                if max_volume and new_volume > max_volume.value:
                    max_volume.value = new_volume
                    await self.session.commit()
        except Exception as e:
            logger.error(f"Error in update_max_volume: {e}")
            await self.session.rollback()
            raise

    def _generate_bar(self, percentage: float) -> str:
        """Generate ASCII progress bar"""
        bar_length = 20
        filled = max(1, int((percentage / 100) * bar_length))  # At least 1 bar if percentage > 0
        return f"[{'█' * filled}{'░' * (bar_length - filled)}] {percentage:.1f}%"

    async def _get_cached_or_fetch(self, key: str, fetch_func, cache_time: int):
        """Get data from cache or fetch and cache it"""
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        data = await fetch_func()
        await self.redis.setex(key, cache_time, json.dumps(data))
        return data

    async def _fetch_holders(self):
        """Fetch current holders count"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TON_API_URL}/jettons/{TETRIX_ADDRESS}",
                headers={
                    "Authorization": f"Bearer {TON_API_KEY}",
                    "accept": "application/json"
                }
            ) as response:
                data = await response.json()
                return {"holders_count": data["holders_count"]}

    async def _fetch_dexscreener_data(self):
        """Fetch price and volume data from DexScreener"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{DEXSCREENER_API_URL}/pairs/ton/{TETRIX_POOL}",
                headers={"accept": "application/json"}
            ) as response:
                data = await response.json()
                pair = data["pairs"][0]  # Get the first pair (should be only one)
                
                volume_usd = float(pair["volume"]["h24"])
                price = float(pair["priceUsd"])
                cap = price * TOTAL_SUPPLY

                # Get max volume from database
                max_volume = await self._ensure_max_volume_exists()
                
                # Update max volume if needed
                if volume_usd > max_volume:
                    await self._update_max_volume(volume_usd)
                    max_volume = volume_usd

                return {
                    "price": price,
                    "cap": cap,
                    "volume": volume_usd,
                    "max_volume": max_volume
                }

    async def get_metrics(self):
        """Get all TETRIX metrics from cache"""
        try:
            # Get cached values
            dex_data = await self._get_cached_or_fetch("tetrix:dexscreener", self._fetch_dexscreener_data, CACHE_TIME)
            holders_data = await self._get_cached_or_fetch("tetrix:holders", self._fetch_holders, CACHE_TIME)
            
            if not all([dex_data, holders_data]):
                logger.error("Some metrics are not available: dex=%s, holders=%s", 
                           bool(dex_data), bool(holders_data))
                raise ValueError("Some metrics are not available in cache")
            
            # Calculate percentages
            health_percent = min(100, (holders_data["holders_count"] / MAX_HOLDERS) * 100)
            strength_percent = min(100, (dex_data["cap"] / MAX_CAP) * 100)
            mood_percent = min(100, (dex_data["volume"] / dex_data["max_volume"]) * 100) if dex_data["max_volume"] > 0 else 0
            
            # Get average percentage for emotion with weights
            # Health and Strength have weight 2.5, Mood has weight 1
            # Total denominator is 2.5 + 2.5 + 1 = 6
            avg_percent = (2.5 * health_percent + 2.5 * strength_percent + mood_percent) / 6
            emotion = get_emotion_by_percentage(avg_percent)
            
            logger.debug("Calculated metrics: health=%.2f%%, strength=%.2f%%, mood=%.2f%%, weighted_avg=%.2f%%",
                      health_percent, strength_percent, mood_percent, avg_percent)
            
            return {
                "health": {
                    "value": holders_data["holders_count"],
                    "percent": health_percent,
                    "bar": self._generate_bar(health_percent)
                },
                "strength": {
                    "value": dex_data["cap"],
                    "percent": strength_percent,
                    "bar": self._generate_bar(strength_percent)
                },
                "mood": {
                    "value": dex_data["volume"],
                    "percent": mood_percent,
                    "bar": self._generate_bar(mood_percent)
                },
                "emotion": emotion,
                "raw": {
                    "price": dex_data["price"],
                    "market_cap": dex_data["cap"],
                    "holders": holders_data["holders_count"],
                    "volume_24h": dex_data["volume"],
                    "max_volume": dex_data["max_volume"]
                }
            }
        except Exception as e:
            logger.error("Error getting metrics: %s", str(e), exc_info=True)
            raise

    async def _get_cached_value(self, key: str) -> Optional[dict]:
        """Get cached value from Redis"""
        cached = await self.redis.get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode cached value for {key}")
        return None