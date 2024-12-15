from datetime import datetime
import secrets
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(255), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    invite_slots = db.Column(db.Integer, default=5)
    invited_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    invite_code = db.Column(db.String(16), unique=True)
    last_slot_reset = db.Column(db.DateTime, default=datetime.utcnow)
    tetrix_balance = db.Column(db.Float, default=0)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.invite_code:
            self.invite_code = secrets.token_hex(8)

    def reset_slots_if_needed(self):
        """Reset invite slots daily"""
        today = datetime.utcnow().date()
        if self.last_slot_reset.date() < today:
            self.invite_slots = 5
            self.last_slot_reset = datetime.utcnow()
            return True
        return False

    def get_stats(self):
        """Get user statistics"""
        return {
            'points': self.points,
            'tetrix_balance': self.tetrix_balance,
            'invite_slots': self.invite_slots,
            'total_invites': User.query.filter_by(invited_by=self.id).count(),
            'registration_date': self.registration_date.isoformat(),
            'is_holder': self.tetrix_balance >= 1.0,
            'point_multiplier': max(1, int(self.tetrix_balance))  # 1x per TETRIX token
        }

    @classmethod
    def get_top_holders(cls, limit: int = 10):
        """Get top TETRIX token holders"""
        return cls.query.order_by(cls.tetrix_balance.desc()).limit(limit).all()
    
    @classmethod
    def get_top_inviters(cls, limit: int = 10):
        """Get users with most successful invites"""
        return db.session.query(
            cls,
            db.func.count(User.invited_by).label('invite_count')
        ).group_by(cls.id).order_by(
            db.text('invite_count DESC')
        ).limit(limit).all() 