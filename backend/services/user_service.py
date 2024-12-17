from models import db, User
from utils.redis_service import redis_client
import os

class UserService:
    def is_early_backer(self, address: str) -> bool:
        """Check if address is in early backers list."""
        # Check Redis cache first
        cache_key = f'early_backer:{address}'
        cached = redis_client.get(cache_key)
        if cached is not None:
            print(f"Found in cache: {address} -> {bool(int(cached))}")
            return bool(int(cached))

        # Check first_backers.txt
        try:
            print(f"Checking first_backers.txt for {address}")
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            backers_file = os.path.join(script_dir, 'first_backers.txt')
            with open(backers_file, 'r') as f:
                backers = [line.strip().lower() for line in f]
                is_early = address.lower() in backers
                print(f"Found in file: {address} -> {is_early}")
                
                # Cache result
                redis_client.setex(cache_key, 3600, int(is_early))
                return is_early
        except FileNotFoundError:
            print("Warning: first_backers.txt not found")
            return False

    def register_user(self, address: str, is_early_backer: bool = False) -> None:
        """Register new user."""
        user = User.query.filter_by(wallet_address=address).first()
        if not user:
            user = User(wallet_address=address)
            db.session.add(user)
            db.session.commit()
            
            # Cache early backer status
            redis_client.setex(f'early_backer:{address}', 3600, int(is_early_backer))