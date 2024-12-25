from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Float, DateTime, func, text
from .database import Base
from typing import List, Dict

class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshots"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    rank = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False)
    total_invites = Column(Integer, nullable=False)
    telegram_name = Column(String(255))
    telegram_username = Column(String(255))
    wallet_address = Column(String(255))
    is_early_backer = Column(Boolean, nullable=False, default=False)
    percentile = Column(Float, nullable=False)
    total_users = Column(Integer, nullable=False)
    snapshot_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @classmethod
    async def get_latest_rank(cls, session, telegram_id: int) -> dict:
        """Get user's latest rank information"""
        result = await session.execute(
            text("""
            SELECT rank, percentile, total_users 
            FROM leaderboard_snapshots 
            WHERE telegram_id = :telegram_id 
            ORDER BY snapshot_time DESC 
            LIMIT 1
            """),
            {"telegram_id": telegram_id}
        )
        row = result.first()
        if row:
            return {
                "rank": row.rank,
                "percentile": row.percentile,
                "total_users": row.total_users
            }
        return None

    @classmethod
    async def get_combined_stats(cls, session) -> Dict:
        """Get combined leaderboard statistics"""
        query = text("""
            SELECT 
                COUNT(*) as total_users,
                SUM(points) as total_points,
                SUM(CASE WHEN is_early_backer THEN 1 ELSE 0 END) as total_early_backers,
                SUM(total_invites) as total_invited_users
            FROM leaderboard_snapshots
            WHERE snapshot_time = (
                SELECT MAX(snapshot_time)
                FROM leaderboard_snapshots
            )
        """)
        
        result = await session.execute(query)
        row = result.first()
        return {
            "total_users": row.total_users,
            "total_points": row.total_points,
            "total_early_backers": row.total_early_backers,
            "total_invited_users": row.total_invited_users
        }

    @classmethod
    async def get_leaderboard(cls, session, limit: int = 100, offset: int = 0) -> Dict:
        """Get leaderboard with combined statistics"""
        users = await cls._get_leaderboard_users(session, limit, offset)
        stats = await cls.get_combined_stats(session)
        
        return {
            "stats": stats,
            "users": users
        }

    @classmethod
    async def _get_leaderboard_users(cls, session, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get leaderboard users list"""
        query = text("""
            SELECT 
                telegram_id,
                rank,
                points,
                total_invites,
                telegram_name,
                telegram_username,
                wallet_address,
                is_early_backer,
                percentile,
                total_users
            FROM leaderboard_snapshots
            WHERE snapshot_time = (
                SELECT MAX(snapshot_time)
                FROM leaderboard_snapshots
            )
            ORDER BY rank
            LIMIT :limit OFFSET :offset
        """)

        result = await session.execute(query, {"limit": limit, "offset": offset})
        rows = result.fetchall()
        return [
            {
                "telegram_id": row.telegram_id,
                "rank": row.rank,
                "points": row.points,
                "total_invites": row.total_invites,
                "telegram_name": row.telegram_name,
                "telegram_username": row.telegram_username,
                "wallet_address": row.wallet_address,
                "is_early_backer": row.is_early_backer,
                "percentile": row.percentile,
                "total_users": row.total_users
            }
            for row in rows
        ] 