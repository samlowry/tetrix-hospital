from models import db, User
from flask import current_app
import os

class UserService:
    def is_early_backer(self, address: str) -> bool:
        """Check if address is in early backers list."""
        # Check Redis cache first
        cache_key = f'early_backer:{address.upper()}'
        cached = current_app.extensions['redis'].get(cache_key)
        if cached is not None:
            print(f"Found in cache: {address} -> {bool(int(cached))}")
            return bool(int(cached))

        # Check first_backers.txt
        try:
            print(f"Checking first_backers.txt for {address}")
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            backers_file = os.path.join(script_dir, 'first_backers.txt')
            with open(backers_file, 'r') as f:
                backers = [line.strip().upper() for line in f]
                is_early = address.upper() in backers
                print(f"Found in file: {address} -> {is_early}")
                
                # Cache result
                current_app.extensions['redis'].setex(cache_key, 3600, int(is_early))
                return is_early
        except FileNotFoundError:
            print("Warning: first_backers.txt not found")
            return False

    def register_user(self, address: str, is_early_backer: bool = False, telegram_id: int = None) -> None:
        """Register new user."""
        print(f"Registering user - Address: {address}, Early Backer: {is_early_backer}, Telegram ID: {telegram_id}")
        
        user = User.query.filter_by(wallet_address=address).first()
        if not user:
            # Create new user with proper flags
            user = User(
                wallet_address=address,
                telegram_id=telegram_id,
                is_early_backer=is_early_backer,
                is_fully_registered=is_early_backer  # Early backers are automatically fully registered
            )
            db.session.add(user)
            db.session.commit()
            print(f"Created new user - Early Backer: {user.is_early_backer}, Fully Registered: {user.is_fully_registered}")
            
            # Cache early backer status with uppercase address
            current_app.extensions['redis'].setex(f'early_backer:{address.upper()}', 3600, int(is_early_backer))
        elif telegram_id and user.telegram_id != telegram_id:
            # Update telegram_id if it's provided and different
            user.telegram_id = telegram_id
            # Make sure early backer flags are set correctly
            if is_early_backer:
                user.is_early_backer = True
                user.is_fully_registered = True
                print(f"Updated user flags - Early Backer: {user.is_early_backer}, Fully Registered: {user.is_fully_registered}")
            db.session.commit()
        
        # Log final state
        user = User.query.filter_by(wallet_address=address).first()
        print(f"Final user state - Early Backer: {user.is_early_backer}, Fully Registered: {user.is_fully_registered}")
        return user

    def get_user_by_address(self, address: str) -> User:
        """Get user by wallet address."""
        return User.query.filter_by(wallet_address=address).first()