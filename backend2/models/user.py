from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    wallet_address = Column(String, unique=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    registration_date = Column(DateTime, server_default=func.now())
    last_slot_reset = Column(DateTime, server_default=func.now())
    max_invite_slots = Column(Integer, default=5)
    ignore_slot_reset = Column(Boolean, default=False)
    is_early_backer = Column(Boolean, default=False)
    is_fully_registered = Column(Boolean, default=False)

    # Relationships
    created_codes = relationship("InviteCode", foreign_keys="InviteCode.creator_id", back_populates="creator")
    used_codes = relationship("InviteCode", foreign_keys="InviteCode.used_by_id", back_populates="used_by")

    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, wallet_address={self.wallet_address})>" 