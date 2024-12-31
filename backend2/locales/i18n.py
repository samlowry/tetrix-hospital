import functools
from typing import Callable, Any
from . import ru, en
from services.user_service import UserService
import logging

# Mapping of language codes to modules
LANGUAGE_MODULES = {
    'ru': ru,
    'en': en
}

def with_locale(func: Callable) -> Callable:
    """
    Decorator that injects localized strings based on user's language.
    Expects telegram_id as a keyword argument.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get user service from first argument (self)
        if not args:
            raise ValueError("No arguments provided")
            
        # Get user_service from self
        if not hasattr(args[0], 'user_service'):
            raise ValueError("First argument must have user_service attribute")
        
        user_service = args[0].user_service
        
        # Get telegram_id from kwargs
        telegram_id = kwargs.get('telegram_id')
        if not telegram_id:
            raise ValueError("telegram_id must be provided as keyword argument")

        # Get user's language
        language = await get_language(telegram_id, user_service)
        
        # Get corresponding language module
        strings = LANGUAGE_MODULES.get(language, ru)  # Default to Russian if language not found
        
        # Add strings to kwargs
        kwargs['strings'] = strings
        
        return await func(*args, **kwargs)
    
    return wrapper 

async def get_language(telegram_id: int, user_service: UserService) -> str:
    """Get user's preferred language or default to Russian"""
    try:
        language = await user_service.get_user_language(telegram_id)
        return language or 'ru'  # Default to Russian if no language set
    except Exception as e:
        logger.error(f"Failed to get language for user {telegram_id}: {e}")
        return 'ru'  # Default to Russian on error 