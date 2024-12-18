from datetime import datetime, time, timedelta
import secrets
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy
import logging

db = SQLAlchemy()
logger = logging.getLogger(__name__)

class InviteCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    used_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(255), unique=True, nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_slot_reset = db.Column(db.DateTime)  # Will be set in __init__
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=True)
    max_invite_slots = db.Column(db.Integer, default=5)  # Custom slot number
    ignore_slot_reset = db.Column(db.Boolean, default=False)  # Option to ignore daily reset
    is_early_backer = db.Column(db.Boolean, default=False)  # Early backer status
    is_fully_registered = db.Column(db.Boolean, default=False)  # Registration status
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set last_slot_reset to 25 hours ago to ensure first invites are available
        self.last_slot_reset = datetime.utcnow() - timedelta(hours=25)
        # Early backers are automatically fully registered
        if kwargs.get('is_early_backer'):
            self.is_fully_registered = True
        
    # Relationships
    created_codes = db.relationship('InviteCode', 
                                  foreign_keys='InviteCode.creator_id',
                                  backref='creator')
    joined_with_code = db.relationship('InviteCode',
                                     foreign_keys='InviteCode.used_by_id',
                                     backref='used_by',
                                     uselist=False)

    def get_invite_codes(self):
        """Get current invite codes with their status"""
        # Only generate codes for fully registered users
        if not self.is_fully_registered:
            return []
            
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)
        
        # Get all unused codes
        unused_codes = InviteCode.query.filter_by(
            creator_id=self.id,
            used_by_id=None
        ).all()
        
        # Get codes used today
        used_today = InviteCode.query.filter(
            InviteCode.creator_id == self.id,
            InviteCode.used_by_id.isnot(None),
            InviteCode.used_at.between(today_start, today_end)
        ).all()
        
        # Always generate codes if we have less than max_invite_slots
        should_generate = len(unused_codes) < self.max_invite_slots
        
        if should_generate:
            codes_needed = self.max_invite_slots - len(unused_codes)
            
            if codes_needed > 0:
                for _ in range(codes_needed):
                    while True:
                        code = secrets.token_hex(8)
                        if not InviteCode.query.filter_by(code=code).first():
                            break
                    
                    invite = InviteCode(
                        code=code,
                        creator_id=self.id
                    )
                    db.session.add(invite)
                
                db.session.commit()
                # Refresh unused codes list
                unused_codes = InviteCode.query.filter_by(
                    creator_id=self.id,
                    used_by_id=None
                ).all()
        
        # Format codes with status
        code_list = []
        
        # Add unused codes
        for code in unused_codes:
            code_list.append({
                'code': code.code,
                'status': 'active'
            })
        
        # Add used today codes
        for code in used_today:
            code_list.append({
                'code': code.code,
                'status': 'used_today',
                'used_at': code.used_at
            })
        
        # Sort by creation date
        code_list.sort(key=lambda x: x.get('used_at', datetime.max))
        
        return code_list

    @classmethod
    def verify_invite_code(cls, code):
        """Verify if invite code is valid and unused"""
        logger.info(f"Verifying invite code: {code}")
        invite = InviteCode.query.filter_by(
            code=code,
            used_by_id=None
        ).first()
        logger.info(f"Found invite code: {invite is not None}")
        return invite

    @classmethod
    def use_invite_code(cls, code, user_id):
        """Mark invite code as used by user"""
        logger.info(f"Using invite code {code} for user {user_id}")
        invite = InviteCode.query.filter_by(
            code=code,
            used_by_id=None
        ).first()
        
        if invite:
            logger.info(f"Found valid invite code {code}, marking as used")
            invite.used_by_id = user_id
            invite.used_at = datetime.utcnow()
            
            # Mark user as fully registered
            user = cls.query.get(user_id)
            if user:
                logger.info(f"User {user_id} before update - Early Backer: {user.is_early_backer}, Fully Registered: {user.is_fully_registered}")
                user.is_fully_registered = True
                db.session.commit()
                logger.info(f"User {user_id} after update - Early Backer: {user.is_early_backer}, Fully Registered: {user.is_fully_registered}")
                
            logger.info(f"Successfully used invite code {code}")
            return True
        logger.warning(f"Invite code {code} not found or already used")
        return False

    def get_stats(self):
        """Get user statistics"""
        # Count successful invites (used codes)
        total_invites = InviteCode.query.filter(
            InviteCode.creator_id == self.id,
            InviteCode.used_by_id.isnot(None)
        ).count()
        
        # Get current codes with status
        codes = self.get_invite_codes()
        
        # Calculate points
        holding_points = 420  # Dummy value for now
        invite_points = total_invites * 420
        early_backer_bonus = 4200 if self.is_early_backer else 0  # Use field instead of file check
        
        total_points = holding_points + invite_points + early_backer_bonus
        
        return {
            'points': total_points,
            'total_invites': total_invites,
            'registration_date': self.registration_date.isoformat(),
            'points_breakdown': {
                'holding': holding_points,
                'invites': invite_points,
                'early_backer_bonus': early_backer_bonus
            },
            'invite_codes': codes,
            'max_invite_slots': self.max_invite_slots,
            'ignore_slot_reset': self.ignore_slot_reset
        }

    @classmethod
    def get_top_inviters(cls, limit: int = 10):
        """Get users with most successful invites"""
        return db.session.query(
            cls,
            db.func.count(InviteCode.id).label('invite_count')
        ).join(InviteCode, InviteCode.creator_id == cls.id
        ).filter(InviteCode.used_by_id.isnot(None)
        ).group_by(cls.id
        ).order_by(db.text('invite_count DESC')
        ).limit(limit).all()