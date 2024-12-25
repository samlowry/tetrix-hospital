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

        # If force=True, update all telegram names
        if force:
            logger.info("Force update requested - updating all telegram names")
            user_service = UserService(self.session)
            result = await self.session.execute(select(User))
            users = result.scalars().all()
            for user in users:
                name = await get_telegram_name(user.telegram_id)
                user.telegram_display_name = name
            await self.session.commit()

        # Create temp table
        await self.session.execute(
            text("CREATE TEMP TABLE temp_leaderboard (LIKE leaderboard_snapshots INCLUDING ALL) ON COMMIT DROP")
        )

        # Get all users and calculate their stats
        users = await self._get_users_with_stats()
        
        # Sort users by points only
        users.sort(key=lambda x: x[1]['points'], reverse=True)
        total_users = len(users)

        # Insert into temp table with ranks matching the sorted order
        for idx, (user, stats, telegram_name) in enumerate(users, 1):
            percentile = ((total_users - idx + 1) / total_users) * 100
            logger.info(f"Assigning rank {idx} to {telegram_name} with {stats['points']} points")
            await self.session.execute(
                text("INSERT INTO temp_leaderboard (telegram_id, rank, points, total_invites, telegram_name, wallet_address, is_early_backer, percentile, total_users) VALUES (:telegram_id, :rank, :points, :total_invites, :telegram_name, :wallet_address, :is_early_backer, :percentile, :total_users)"),
                {
                    "telegram_id": user.telegram_id,
                    "rank": idx,
                    "points": stats["points"],
                    "total_invites": stats["total_invites"],
                    "telegram_name": telegram_name,
                    "wallet_address": user.wallet_address,
                    "is_early_backer": user.is_early_backer,
                    "percentile": percentile,
                    "total_users": total_users
                }
            )

        # Replace main table contents
        await self.session.execute(text("DELETE FROM leaderboard_snapshots"))
        await self.session.execute(text("INSERT INTO leaderboard_snapshots SELECT * FROM temp_leaderboard"))
        
        logger.info("Leaderboard updated successfully")

    async def _get_users_with_stats(self):
        user_service = UserService(self.session)
        result = await self.session.execute(select(User))
        users = result.scalars().all()
        stats = [await user_service.get_user_stats(user) for user in users]
        
        # Use cached telegram names from database
        telegram_names = []
        for user in users:
            if user.telegram_display_name:
                telegram_names.append(user.telegram_display_name)
            else:
                # Only fetch from API if name is missing
                name = await get_telegram_name(user.telegram_id)
                # Update in database for future use
                user.telegram_display_name = name
                telegram_names.append(name)
        
        # Commit any name updates
        if any(not user.telegram_display_name for user in users):
            await self.session.commit()
            
        return list(zip(users, stats, telegram_names))