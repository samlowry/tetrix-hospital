# Import necessary libraries for Redis, SQLAlchemy, HTTP requests, and other utilities
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiohttp
import logging
import json
from datetime import datetime, timedelta
from models.metrics import TetrixMetrics
from typing import Optional
from locales.emotions import get_emotion_by_percentage
from core.cache import cache_metrics, CacheKeys, Cache

# Initialize logger for this module
logger = logging.getLogger(__name__)

# API endpoints and authentication constants
TON_API_URL = "https://tonapi.io/v2"  # Base URL for TON blockchain API
#TODO: move into env vars (and github env secret)
TON_API_KEY = "AHK6ZFZUS4TIGHQAAAAH3XFVS5TRIQABRO6J2HZ6ST4N43ZQTXHAYBBQ2IETD54M4PSRYBQ"  # Authentication key for TON API
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex"  # API for fetching DEX related data

# Blockchain addresses for Tetrix token and pool
TETRIX_ADDRESS = "EQC-OHxhI9r5ojKf6QMLFjhQrKoawN1thhHFCvImINhfK40C"  # Main token contract address
TETRIX_POOL = "EQDzf3WUJvNqlXnzggvxTDweWW7l7DaZ68qyvRVx1a2xm0Zy"  # Liquidity pool address
TOTAL_SUPPLY = 1_000_000_000  # Total supply of Tetrix tokens

# Threshold constants for metrics calculations
MAX_HOLDERS = 100_000  # Maximum number of holders (100% health metric)
MAX_CAP = 1_000_000  # Maximum market cap in USD (100% strength metric)
INITIAL_MAX_VOLUME = 0  # Starting point for volume tracking
CACHE_TIME = 60  # Fin values cache duration for general metrics (in seconds)

class TetrixService:
    """Service class for handling Tetrix token-related operations and metrics"""
    
    def __init__(self, cache: Cache, session: AsyncSession = None):
        """
        Initialize TetrixService with cache connection and optional database session
        Args:
            cache (Cache): Cache instance for caching (aiocache)
            session (AsyncSession): SQLAlchemy session for database operations
        """
        self.cache = cache
        self.session = session

    async def _ensure_max_volume_exists(self):
        """
        Ensures that a maximum volume record exists in the database
        Returns the initial max volume if no database session is available
        """
        if not self.session:
            return INITIAL_MAX_VOLUME

        try:
            # Query max volume
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
            # Query max volume
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

    @cache_metrics(key_pattern=CacheKeys.HOLDERS)
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

    @cache_metrics(key_pattern=CacheKeys.DEX_SCREENER)
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

    @cache_metrics(key_pattern="tetrix:metrics")
    async def get_metrics(self):
        """Get all TETRIX metrics from cache"""
        try:
            # Get cached values using decorated methods
            dex_data = await self._fetch_dexscreener_data()
            holders_data = await self._fetch_holders()
            
            if not all([dex_data, holders_data]):
                logger.error("Some metrics are not available: dex=%s, holders=%s", 
                           bool(dex_data), bool(holders_data))
                raise ValueError("Some metrics are not available")
            
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
            
            metrics = {
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

            # If we got a string, try to deserialize it
            if isinstance(metrics, str):
                try:
                    metrics = json.loads(metrics)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode metrics from cache, raw value: {metrics[:100]}")
                    # Re-raise to trigger recalculation
                    raise

            return metrics
            
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