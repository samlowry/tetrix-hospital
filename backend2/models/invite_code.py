from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class InviteCode(Base):
    __tablename__ = "invite_code"

    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)
    creator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    used_by_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    created_at = Column(DateTime, nullable=True)
    used_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_codes")
    used_by = relationship("User", foreign_keys=[used_by_id], back_populates="used_codes") 