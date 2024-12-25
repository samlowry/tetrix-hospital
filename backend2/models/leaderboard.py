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
    def get_leaderboard(cls, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Получение лидерборда"""
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

        with engine.connect() as conn:
            result = conn.execute(query, {"limit": limit, "offset": offset})
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
                for row in result
            ] 