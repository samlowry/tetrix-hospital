from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
import logging
from models.leaderboard import LeaderboardSnapshot
from models.user import User
from services.user_service import UserService
from services.telegram_service import get_telegram_name
from datetime import datetime

logger = logging.getLogger(__name__)

class LeaderboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_populated(self):
        """Check if leaderboard is populated and fill it if empty"""
        try:
            result = await self.session.execute(text("SELECT COUNT(*) FROM leaderboard_snapshots"))
            count = result.scalar()
            
            if count == 0:
                logger.info("Leaderboard table is empty, performing initial population")
                await self.update_leaderboard(force=True)
                logger.info("Initial leaderboard population completed")
            else:
                logger.info(f"Leaderboard table already contains {count} records, skipping update")
        except Exception as e:
            logger.error(f"Error in ensure_populated: {e}")
            raise

    async def update_leaderboard(self, force: bool = False):
        """Update leaderboard snapshot"""
        if not force:
            # Check if update is needed (last update was less than an hour ago)
            result = await self.session.execute(
                text("SELECT MAX(snapshot_time) FROM leaderboard_snapshots")
            )
            last_update = result.scalar()
            if last_update and (datetime.now(last_update.tzinfo) - last_update).total_seconds() < 3600:
                logger.info("Skipping leaderboard update - last update was less than an hour ago")
                return

        # Get all users and calculate their stats
        users = await self._get_users_with_stats()
        
        # Sort users by points in descending order
        users.sort(key=lambda x: x[1]['points'], reverse=True)
        total_users = len(users)

        # Clear old snapshot
        await self.session.execute(text("DELETE FROM leaderboard_snapshots"))
        
        # Track current rank and points for handling ties
        current_rank = 1
        current_points = None
        rank_offset = 0

        # Insert users with ranks matching their sorted position
        for idx, (user, stats, telegram_name) in enumerate(users, 1):
            # If points changed, update rank (handling ties)
            if current_points != stats['points']:
                current_points = stats['points']
                current_rank = idx
                rank_offset = 0
            else:
                rank_offset += 1

            percentile = ((total_users - idx + 1) / total_users) * 100
            params = {
                "telegram_id": user.telegram_id,
                "rank": current_rank,  # Same rank for same points
                "points": stats["points"],
                "total_invites": stats["total_invites"],
                "telegram_name": user.telegram_display_name or str(user.telegram_id),
                "telegram_username": user.telegram_username,
                "wallet_address": user.wallet_address,
                "is_early_backer": user.is_early_backer,
                "percentile": percentile,
                "total_users": total_users
            }
            logger.info(f"SQL params: {params}")
            
            await self.session.execute(
                text("""
                    INSERT INTO leaderboard_snapshots 
                    (telegram_id, rank, points, total_invites, telegram_name, telegram_username, wallet_address, is_early_backer, percentile, total_users) 
                    VALUES (:telegram_id, :rank, :points, :total_invites, :telegram_name, :telegram_username, :wallet_address, :is_early_backer, :percentile, :total_users)
                """),
                params
            )
        
        await self.session.commit()

    async def _get_users_with_stats(self):
        user_service = UserService(self.session)
        result = await self.session.execute(select(User))
        users = result.scalars().all()
        stats = [await user_service.get_user_stats(user) for user in users]
        
        # Just use whatever name is in the database, no API calls
        telegram_names = [user.telegram_display_name or str(user.telegram_id) for user in users]
            
        return list(zip(users, stats, telegram_names))