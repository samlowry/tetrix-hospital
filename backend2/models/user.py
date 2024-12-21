from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    address = Column(String, unique=True, nullable=False, index=True)
    is_early_backer = Column(Boolean, default=False)
    is_fully_registered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    wallet_data = Column(JSONB, nullable=True)  # Store additional wallet info
    settings = Column(JSONB, nullable=True, default=dict)  # User preferences/settings

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, address={self.address})>" 