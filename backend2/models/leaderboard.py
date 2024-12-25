from sqlalchemy import Column, Integer, String, BigInteger, Boolean, Float, DateTime, func, text
from .database import Base

class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshots"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    rank = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False)
    total_invites = Column(Integer, nullable=False)
    telegram_name = Column(String(255))
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
    async def get_leaderboard(cls, session, limit: int = 10, offset: int = 0) -> list:
        """Get latest leaderboard entries"""
        result = await session.execute(
            text("""
                WITH latest_snapshot AS (
                    SELECT MAX(snapshot_time) as max_time 
                    FROM leaderboard_snapshots
                ) 
                SELECT telegram_id, telegram_name, points, total_invites, rank 
                FROM leaderboard_snapshots ls 
                WHERE snapshot_time = (SELECT max_time FROM latest_snapshot) 
                ORDER BY points DESC, total_invites DESC 
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset}
        )
        return [
            {
                "telegram_id": row.telegram_id,
                "telegram_name": row.telegram_name,
                "points": row.points,
                "total_invites": row.total_invites,
                "rank": row.rank
            }
            for row in result
        ] 