from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from pydantic import BaseModel
import secrets
import logging

from models.database import get_session
from services.user_service import UserService
from services.redis_service import RedisService
from core.deps import get_redis
from locales.i18n import with_locale
from routers.telegram import send_telegram_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ton-connect", tags=["ton-connect"])

class MessageRequest(BaseModel):
    telegram_id: int

class ProofRequest(BaseModel):
    telegram_id: int
    wallet_address: str
    payload: str

class TonConnectHandler:
    def __init__(self, user_service: UserService, redis_service: RedisService):
        self.user_service = user_service
        self.redis_service = redis_service

    @with_locale
    async def send_welcome_message(self, strings, telegram_id: int, is_early_backer: bool) -> bool:
        """Send welcome message based on user type"""
        if is_early_backer:
            # Early backer - show special welcome message
            logger.info(f"[TON_CONNECT] Setting status registered for early backer telegram_id={telegram_id}")
            await self.redis_service.set_status_registered(telegram_id)
            
            logger.info(f"[TON_CONNECT] Sending WELCOME_EARLY_BACKER message to telegram_id={telegram_id}")
            message_sent = await send_telegram_message(
                telegram_id,
                text=strings.WELCOME_EARLY_BACKER,
                parse_mode="Markdown",
                reply_markup={
                    "inline_keyboard": [[{
                        "text": strings.BUTTONS["stats"],
                        "callback_data": "check_stats"
                    }]]
                }
            )
            logger.info(f"[TON_CONNECT] WELCOME_EARLY_BACKER message sent: {message_sent}")
        else:
            # Regular user - request invite code
            logger.info(f"[TON_CONNECT] Setting status waiting_invite for regular user telegram_id={telegram_id}")
            await self.redis_service.set_status_waiting_invite(telegram_id)
            
            logger.info(f"[TON_CONNECT] Sending WELCOME_NEED_INVITE message to telegram_id={telegram_id}")
            message_sent = await send_telegram_message(
                telegram_id,
                text=strings.WELCOME_NEED_INVITE,
                parse_mode="Markdown"
            )
            logger.info(f"[TON_CONNECT] WELCOME_NEED_INVITE message sent: {message_sent}")
        return True

@router.post("/get-message")
async def get_message(request: MessageRequest):
    """
    Get message for wallet signature
    """
    try:
        logger.info(f"[TON_CONNECT] Received get_message request for telegram_id={request.telegram_id}")
        # Generate random payload
        payload = secrets.token_hex(32)
        logger.info(f"[TON_CONNECT] Generated payload={payload} for telegram_id={request.telegram_id}")
        return {"message": payload}
    except Exception as e:
        logger.error(f"[TON_CONNECT] Error generating message for telegram_id={request.telegram_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proof")
async def verify_proof(
    proof_data: ProofRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis)
):
    """Handle TON Connect proof verification"""
    try:
        # Get cache from app state
        cache = request.app.state.cache
        
        # Initialize services with cache
        user_service = UserService(session)
        user_service.cache = cache  # Set cache instance
        redis_service = RedisService(redis, cache)  # Pass cache to RedisService
        # Set Redis client in user_service
        user_service.redis = redis
        handler = TonConnectHandler(user_service, redis_service)
        
        # Get or update user
        try:
            logger.info(f"[TON_CONNECT] Looking up user with telegram_id={proof_data.telegram_id}")
            user = await user_service.get_user_by_telegram_id(proof_data.telegram_id)
            
            if user:
                if user.registration_phase != 'preregistered':
                    logger.error(f"[TON_CONNECT] User {proof_data.telegram_id} is in {user.registration_phase} state, cannot update wallet")
                    raise HTTPException(
                        status_code=400,
                        detail="User is not in preregistration state"
                    )
                    
                # Check if wallet is already registered to another user
                existing_wallet_user = await user_service.get_user_by_wallet_address(proof_data.wallet_address)
                if existing_wallet_user:
                    logger.error(f"[TON_CONNECT] Wallet {proof_data.wallet_address} already registered to telegram_id={existing_wallet_user.telegram_id}")
                    raise HTTPException(
                        status_code=400,
                        detail="This wallet is already registered to another user"
                    )
                
                logger.info(f"[TON_CONNECT] Updating preregistered user with telegram_id={proof_data.telegram_id}, wallet={proof_data.wallet_address}")
                # Update wallet address and phase
                await user_service.update_user(
                    user,
                    wallet_address=proof_data.wallet_address,
                    registration_phase='pending'
                )
            else:
                logger.info(f"[TON_CONNECT] Creating new user with telegram_id={proof_data.telegram_id}, wallet={proof_data.wallet_address}")
                user = await user_service.create_user(
                    telegram_id=proof_data.telegram_id,
                    wallet_address=proof_data.wallet_address
                )
            
            logger.info(f"[TON_CONNECT] User processed successfully: telegram_id={proof_data.telegram_id}, is_early_backer={user.is_early_backer}")
            
            # Send welcome message based on user type
            try:
                await handler.send_welcome_message(telegram_id=proof_data.telegram_id, is_early_backer=user.is_early_backer)
            except Exception as e:
                logger.error(f"[TON_CONNECT] Error sending welcome message: {e}")
            
            return {"success": True}
        except Exception as e:
            logger.error(f"[TON_CONNECT] Error processing user: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TON_CONNECT] Error in verify_proof: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 