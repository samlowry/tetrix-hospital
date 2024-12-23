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

STON_API_URL = "https://api.ston.fi/v1"
TON_API_URL = "https://tonapi.io/v2"
TON_API_KEY = "AHK6ZFZUS4TIGHQAAAAH3XFVS5TRIQABRO6J2HZ6ST4N43ZQTXHAYBBQ2IETD54M4PSRYBQ"

TETRIX_ADDRESS = "EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C"
TETRIX_POOL = "EQDzf3WUJvNqlXnzggvxTDweWW7l7DaZ68qyvRVx1a2xm0Zy"
TOTAL_SUPPLY = 1_000_000_000

# Constants for 100% values
MAX_HOLDERS = 100_000  # 100K holders = 100% health
MAX_CAP = 1_000_000  # $1M cap = 100% strength
INITIAL_MAX_VOLUME = 100_000  # Initial max volume is 100K
CACHE_TIME = 60  # 1 minute cache for most metrics
VOLUME_CACHE_TIME = 600  # 10 minutes cache for volume

class TetrixService:
    def __init__(self, redis: Redis, session: AsyncSession = None):
        self.redis = redis
        self.session = session

    async def _ensure_max_volume_exists(self):
        """Ensure max volume exists in database with initial value"""
        if not self.session:
            return INITIAL_MAX_VOLUME

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

    async def _update_max_volume(self, new_volume: float):
        """Update max volume in database if needed"""
        if not self.session:
            return

        result = await self.session.execute(
            select(TetrixMetrics).where(TetrixMetrics.key == "max_volume")
        )
        max_volume = result.scalar_one_or_none()
        
        if max_volume and new_volume > max_volume.value:
            max_volume.value = new_volume
            await self.session.commit()

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

    async def _fetch_price_and_cap(self):
        """Fetch current price and calculate market cap"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{STON_API_URL}/assets/search?search_string={TETRIX_ADDRESS}",
                headers={
                    "accept": "application/json",
                    "Content-Type": "application/json"
                },
                data=""
            ) as response:
                data = await response.json()
                price = float(data["asset_list"][0]["dex_price_usd"])
                cap = price * TOTAL_SUPPLY
                return {"price": price, "cap": cap}

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

    async def _fetch_volume(self):
        """Fetch trading volume"""
        today = datetime.utcnow()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{STON_API_URL}/stats/pool",
                headers={
                    "Content-Type": "application/json",
                    "accept": "application/json"
                },
                params={
                    "since": today.strftime("%Y-%m-%dT00:00:00"),
                    "until": today.strftime("%Y-%m-%dT23:59:59")
                }
            ) as response:
                try:
                    text = await response.text()
                    # Remove any BOM or whitespace
                    text = text.strip().lstrip('\ufeff')
                    data = json.loads(text)
                    
                    # Find TETRIX pool
                    if isinstance(data, dict) and "stats" in data:
                        for pool in data["stats"]:
                            if isinstance(pool, dict) and pool.get("pool_address") == TETRIX_POOL:
                                volume_tokens = float(pool["base_volume"])
                                # Get current price to calculate USD volume
                                price_data = await self._get_cached_or_fetch(
                                    "tetrix:price",
                                    self._fetch_price_and_cap,
                                    CACHE_TIME
                                )
                                volume_usd = volume_tokens * price_data["price"]
                                
                                # Get max volume from database
                                max_volume = await self._ensure_max_volume_exists()
                                
                                # Update max volume if needed
                                if volume_usd > max_volume:
                                    await self._update_max_volume(volume_usd)
                                    max_volume = volume_usd
                                
                                return {
                                    "volume": volume_usd,
                                    "max_volume": max_volume
                                }
                    logger.warning(f"TETRIX pool not found in response: {text[:200]}...")
                    return {"volume": 0, "max_volume": await self._ensure_max_volume_exists()}
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing pool stats: {e}. Response: {text[:200]}...")
                    return {"volume": 0, "max_volume": await self._ensure_max_volume_exists()}
                except Exception as e:
                    logger.error(f"Error fetching volume: {e}", exc_info=True)
                    return {"volume": 0, "max_volume": await self._ensure_max_volume_exists()}

    async def get_metrics(self):
        """Get all TETRIX metrics from cache"""
        try:
            # Get cached values
            price_data = await self._get_cached_or_fetch("tetrix:price", self._fetch_price_and_cap, CACHE_TIME)
            holders_data = await self._get_cached_or_fetch("tetrix:holders", self._fetch_holders, CACHE_TIME)
            volume_data = await self._get_cached_or_fetch("tetrix:volume", self._fetch_volume, VOLUME_CACHE_TIME)
            
            if not all([price_data, holders_data, volume_data]):
                logger.error("Some metrics are not available: price=%s, holders=%s, volume=%s", 
                           bool(price_data), bool(holders_data), bool(volume_data))
                raise ValueError("Some metrics are not available in cache")
            
            # Calculate percentages
            health_percent = min(100, (holders_data["holders_count"] / MAX_HOLDERS) * 100)
            strength_percent = min(100, (price_data["cap"] / MAX_CAP) * 100)
            mood_percent = min(100, (volume_data["volume"] / volume_data["max_volume"]) * 100) if volume_data["max_volume"] > 0 else 0
            
            # Get average percentage for emotion
            avg_percent = (health_percent + strength_percent + mood_percent) / 3
            emotion = get_emotion_by_percentage(avg_percent)
            
            logger.debug("Calculated metrics: health=%.2f%%, strength=%.2f%%, mood=%.2f%%, avg=%.2f%%",
                      health_percent, strength_percent, mood_percent, avg_percent)
            
            return {
                "health": {
                    "value": holders_data["holders_count"],
                    "percent": health_percent,
                    "bar": self._generate_bar(health_percent)
                },
                "strength": {
                    "value": price_data["cap"],
                    "percent": strength_percent,
                    "bar": self._generate_bar(strength_percent)
                },
                "mood": {
                    "value": volume_data["volume"],
                    "percent": mood_percent,
                    "bar": self._generate_bar(mood_percent)
                },
                "emotion": emotion,
                "raw": {
                    "price": price_data["price"],
                    "market_cap": price_data["cap"],
                    "holders": holders_data["holders_count"],
                    "volume_24h": volume_data["volume"],
                    "max_volume": volume_data["max_volume"]
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