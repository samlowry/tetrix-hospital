from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import secrets
import logging

from models.database import get_session
from services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ton-connect", tags=["ton-connect"])

class ProofRequest(BaseModel):
    telegram_id: int
    wallet_address: str
    payload: str

@router.get("/get-message")
async def get_message(telegram_id: int):
    """Get message for wallet signature"""
    try:
        # Generate message for signing
        payload = secrets.token_hex(32)
        return {"message": payload}
    except Exception as e:
        logger.error(f"Error generating message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proof")
async def verify_proof(
    request: ProofRequest,
    session: AsyncSession = Depends(get_session)
):
    """Verify TON Connect signature and create/update user"""
    try:
        user_service = UserService(session)
        
        # Verify signature
        if not verify_ton_proof_signature(
            request.wallet_address,
            request.proof.signature,
            request.proof.payload
        ):
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Create or update user
        user = await user_service.get_user_by_wallet_address(request.wallet_address)
        
        if not user:
            # Create new user
            user = await user_service.create_user(
                telegram_id=request.telegram_id,
                wallet_address=request.wallet_address
            )
        else:
            # Update existing user
            user = await user_service.update_user(
                user,
                telegram_id=request.telegram_id
            )

        # Update Redis state
        redis_service = RedisService(redis)
        if user.is_early_backer:
            await redis_service.set_status_registered(request.telegram_id)
        else:
            await redis_service.set_status_waiting_invite(request.telegram_id)

        return {
            "success": True,
            "is_early_backer": user.is_early_backer,
            "is_fully_registered": user.is_fully_registered
        }
    except Exception as e:
        logger.error(f"Error verifying signature: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 