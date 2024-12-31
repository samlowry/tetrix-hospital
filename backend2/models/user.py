from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, func, CheckConstraint
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    """
    User model representing registered users in the system
    """
    __tablename__ = "user"

    # Primary identifier for the user
    id = Column(Integer, primary_key=True)
    # User's TON wallet address
    wallet_address = Column(String, unique=True, nullable=True)
    # Telegram user ID for authentication
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    # Display name shown in Telegram
    telegram_display_name = Column(String, nullable=True)
    # Username in Telegram (optional)
    telegram_username = Column(String, nullable=True)
    # Timestamp when user registered in the system
    registration_date = Column(DateTime, server_default=func.now())
    # Timestamp of last invite slot reset
    last_slot_reset = Column(DateTime, server_default=func.now())
    # Maximum number of slots of invites user reveive per day 
    max_invite_slots = Column(Integer, default=5)
    # Flag to bypass limitation of next generation of invites in the next day
    ignore_slot_reset = Column(Boolean, default=False)
    # Flag indicating if user is an early supporter, which  got into system w/o invites
    is_early_backer = Column(Boolean, default=False)
    # Flag indicating if registration process is complete
    is_fully_registered = Column(Boolean, default=False)
    # User's preferred language code
    language = Column(String(2), default='ru', nullable=False)
    # User's registration phase
    registration_phase = Column(String(20), nullable=False)

    # Database constraints for data validation
    __table_args__ = (
        CheckConstraint("wallet_address IS NULL OR wallet_address ~ '^0:[a-fA-F0-9]{64}$'", name='check_wallet_address'),
        CheckConstraint("telegram_id > 0", name='check_telegram_id'),
        CheckConstraint("language ~ '^[a-z]{2}$'", name='check_language_code'),
        CheckConstraint("registration_phase IN ('preregistered', 'pending', 'active')", name='check_registration_phase'),
    )

    # Relationship definitions
    # Tracks invite codes created by this user
    created_codes = relationship("InviteCode", foreign_keys="InviteCode.creator_id", back_populates="creator")
    # Tracks invite codes used by this user
    used_codes = relationship("InviteCode", foreign_keys="InviteCode.used_by_id", back_populates="used_by")

    def __repr__(self):
        """String representation of User object"""
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, wallet_address={self.wallet_address})>"