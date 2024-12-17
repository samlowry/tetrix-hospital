from models import db, User
from utils.redis_service import redis_client

class UserService:
    def is_early_backer(self, address: str) -> bool:
        """Check if address is in early backers list."""
        # Check Redis cache first
        cache_key = f'early_backer:{address}'
        cached = redis_client.get(cache_key)
        if cached is not None:
            return bool(int(cached))

        # Check database
        user = User.query.filter_by(address=address).first()
        is_early = bool(user and user.is_early_backer)
        
        # Cache result
        redis_client.setex(cache_key, 3600, int(is_early))
        return is_early

    def register_user(self, address: str, is_early_backer: bool = False) -> None:
        """Register new user."""
        user = User.query.filter_by(address=address).first()
        if not user:
            user = User(address=address, is_early_backer=is_early_backer)
            db.session.add(user)
            db.session.commit()
            
            # Update cache
            redis_client.setex(f'early_backer:{address}', 3600, int(is_early_backer)) 