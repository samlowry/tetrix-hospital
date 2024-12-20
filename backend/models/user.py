from datetime import datetime, time, timedelta
import secrets
from sqlalchemy import text
from flask_sqlalchemy import SQLAlchemy
import logging
import os
import requests

db = SQLAlchemy()
logger = logging.getLogger(__name__)

def get_telegram_name(telegram_id: int) -> str:
    """Get user's current display name via Bot API"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return str(telegram_id)  # Fallback to ID if no token
            
        url = f"https://api.telegram.org/bot{bot_token}/getChat"
        response = requests.get(url, params={'chat_id': telegram_id})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                result = data['result']
                # Get first_name + last_name if available, otherwise just first_name
                first_name = result.get('first_name', '')
                last_name = result.get('last_name', '')
                full_name = f"{first_name} {last_name}".strip()
                return full_name or str(telegram_id)
        
        logger.error(f"Failed to get Telegram name: {response.text}")
        return str(telegram_id)  # Fallback to ID if request failed
        
    except Exception as e:
        logger.error(f"Error getting Telegram name: {e}")
        return str(telegram_id)  # Fallback to ID if any error

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
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    last_slot_reset = db.Column(db.DateTime)  # Will be set in __init__
    max_invite_slots = db.Column(db.Integer, default=5)  # Custom slot number
    ignore_slot_reset = db.Column(db.Boolean, default=False)  # Option to ignore daily reset
    is_early_backer = db.Column(db.Boolean, default=False)  # Early backer status
    is_fully_registered = db.Column(db.Boolean, default=False)  # Registration status
    
    def __init__(self, **kwargs):
        if 'wallet_address' not in kwargs:
            raise ValueError("wallet_address is required")
        if 'telegram_id' not in kwargs:
            raise ValueError("telegram_id is required")
            
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
        points_per_invite = 420  # Points per successful invite
        invite_points = total_invites * points_per_invite
        early_backer_bonus = 4200 if self.is_early_backer else 0
        
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
            'points_per_invite': points_per_invite,
            'invite_codes': codes,
            'max_invite_slots': self.max_invite_slots,
            'ignore_slot_reset': self.ignore_slot_reset,
            'telegram_name': get_telegram_name(self.telegram_id)
        }

    @classmethod
    def get_top_inviters(cls, limit: int = 10):
        """Get users with most successful invites"""
        users_with_invites = db.session.query(
            cls,
            db.func.count(InviteCode.id).label('invite_count')
        ).join(InviteCode, InviteCode.creator_id == cls.id
        ).filter(InviteCode.used_by_id.isnot(None)
        ).group_by(cls.id
        ).order_by(db.text('invite_count DESC')
        ).limit(limit).all()
        
        # Get Telegram names for each user
        return [(user, get_telegram_name(user.telegram_id), invite_count) 
                for user, invite_count in users_with_invites]