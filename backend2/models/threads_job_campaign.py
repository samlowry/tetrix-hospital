from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, text, select
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base

class ThreadsJobCampaign(Base):
    """
    Model for storing Threads job campaign data and analysis results
    """
    __tablename__ = "threads_job_campaign"

    # Primary identifier
    id = Column(Integer, primary_key=True)
    # Link to user table
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    # Threads username (can be with or without @)
    threads_username = Column(String, nullable=True)
    # Threads user ID from API
    threads_user_id = Column(String, nullable=True)
    # JSON with user's posts texts
    posts_json = Column(JSONB, nullable=True)
    # Analysis report text
    analysis_report = Column(String, nullable=True)
    # Timestamp of record creation
    created_at = Column(DateTime, server_default=func.now())

    # Relationship to User model
    user = relationship("User", back_populates="threads_campaign")

    @classmethod
    async def get_by_telegram_id(cls, session, telegram_id: int):
        """Get campaign record by telegram ID"""
        from models.user import User
        stmt = (
            select(cls)
            .join(User, User.id == cls.user_id)
            .where(User.telegram_id == telegram_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def get_by_threads_username(cls, session, threads_username: str):
        """Get campaign record by threads username"""
        result = await session.execute(
            text("""
            SELECT * FROM threads_job_campaign 
            WHERE threads_username = :threads_username
            """),
            {"threads_username": threads_username}
        )
        return result.first() 