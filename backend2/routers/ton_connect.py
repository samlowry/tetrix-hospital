from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from pydantic import BaseModel
import secrets
import logging

from models.database import get_session
from services.user_service import UserService
from services.redis_service import RedisService
from core.deps import get_redis
from locales.ru import WELCOME_EARLY_BACKER, WELCOME_NEED_INVITE, BUTTONS
from routers.telegram import send_telegram_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ton-connect", tags=["ton-connect"])

class ProofRequest(BaseModel):
    telegram_id: int
    wallet_address: str
    payload: str

@router.get("/get-message")
async def get_message(telegram_id: int):
    """
    Get message for wallet signature
    """
    try:
        logger.info(f"[TON_CONNECT] Received get_message request for telegram_id={telegram_id}")
        # Generate random payload
        payload = secrets.token_hex(32)
        logger.info(f"[TON_CONNECT] Generated payload={payload} for telegram_id={telegram_id}")
        return {"message": payload}
    except Exception as e:
        logger.error(f"[TON_CONNECT] Error generating message for telegram_id={telegram_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proof")
async def verify_proof(
    request: ProofRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis)
):
    """
    Verify TON Connect signature and create/update user
    """
    try:
        logger.info(f"[TON_CONNECT] Starting verify_proof for telegram_id={request.telegram_id}, wallet={request.wallet_address}")
        user_service = UserService(session)
        redis_service = RedisService(redis)
        
        # Check if user exists with this telegram_id
        user = await user_service.get_user_by_telegram_id(request.telegram_id)
        if user:
            logger.info(f"[TON_CONNECT] User already exists with telegram_id={request.telegram_id}")
            return {"success": True}

        # Check if user exists with this wallet
        user = await user_service.get_user_by_wallet_address(request.wallet_address)
        if user:
            logger.error(f"[TON_CONNECT] Wallet {request.wallet_address} already registered to telegram_id={user.telegram_id}")
            raise HTTPException(
                status_code=400,
                detail="This wallet is already registered to another user"
            )

        # Create user
        try:
            logger.info(f"[TON_CONNECT] Creating new user with telegram_id={request.telegram_id}, wallet={request.wallet_address}")
            user = await user_service.create_user(
                telegram_id=request.telegram_id,
                wallet_address=request.wallet_address
            )
            logger.info(f"[TON_CONNECT] User created successfully: telegram_id={request.telegram_id}, is_early_backer={user.is_early_backer}")
            
            # Send welcome message based on user type
            if user.is_early_backer:
                # Early backer - show special welcome message
                logger.info(f"[TON_CONNECT] Setting status registered for early backer telegram_id={request.telegram_id}")
                await redis_service.set_status_registered(request.telegram_id)
                
                logger.info(f"[TON_CONNECT] Sending WELCOME_EARLY_BACKER message to telegram_id={request.telegram_id}")
                message_sent = await send_telegram_message(
                    request.telegram_id,
                    text=WELCOME_EARLY_BACKER,
                    parse_mode="Markdown",
                    reply_markup={
                        "inline_keyboard": [[{
                            "text": BUTTONS["stats"],
                            "callback_data": "check_stats"
                        }]]
                    }
                )
                logger.info(f"[TON_CONNECT] WELCOME_EARLY_BACKER message sent: {message_sent}")
            else:
                # Regular user - request invite code
                logger.info(f"[TON_CONNECT] Setting status waiting_invite for regular user telegram_id={request.telegram_id}")
                await redis_service.set_status_waiting_invite(request.telegram_id)
                
                logger.info(f"[TON_CONNECT] Sending WELCOME_NEED_INVITE message to telegram_id={request.telegram_id}")
                message_sent = await send_telegram_message(
                    request.telegram_id,
                    text=WELCOME_NEED_INVITE,
                    parse_mode="Markdown"
                )
                logger.info(f"[TON_CONNECT] WELCOME_NEED_INVITE message sent: {message_sent}")
            
            return {"success": True}
        except Exception as e:
            logger.error(f"[TON_CONNECT] Error creating user: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TON_CONNECT] Error in verify_proof: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 