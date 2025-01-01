# Required SQLAlchemy imports for database model definition
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

# InviteCode model represents invitation codes used for user registration
class InviteCode(Base):
    __tablename__ = "invite_code"

    # Primary key identifier for the invite code
    id = Column(Integer, primary_key=True)
    # Unique 16-character string that serves as the actual invitation code
    code = Column(String(16), unique=True, nullable=False)
    # Foreign key reference to the user who created this invite code
    creator_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    # Foreign key reference to the user who used this invite code (if used)
    used_by_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    # Timestamp when the invite code was created
    created_at = Column(DateTime, nullable=True)
    # Timestamp when the invite code was used
    used_at = Column(DateTime, nullable=True)

    # Relationships
    # Reference to the User model for the creator of this invite code
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_codes")
    # Reference to the User model for the person who used this invite code
    used_by = relationship("User", foreign_keys=[used_by_id], back_populates="used_codes")