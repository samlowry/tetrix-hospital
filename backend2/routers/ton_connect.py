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
    """
    Get message for wallet signature
    """
    try:
        # Generate random payload
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
    """
    Проверка TON Connect подписи и создание/обновление пользователя
    """
    try:
        user_service = UserService(session)
        
        # Проверяем, существует ли пользователь с таким telegram_id
        user = await user_service.get_user_by_telegram_id(request.telegram_id)
        if user:
            return {"success": True}

        # Проверяем, существует ли пользователь с таким кошельком
        user = await user_service.get_user_by_wallet_address(request.wallet_address)
        if user:
            logger.error(f"Wallet {request.wallet_address} already registered to telegram_id {user.telegram_id}")
            raise HTTPException(
                status_code=400,
                detail="This wallet is already registered to another user"
            )

        # Создаем пользователя
        try:
            user = await user_service.create_user(
                telegram_id=request.telegram_id,
                wallet_address=request.wallet_address
            )
            logger.info(f"Created user with telegram_id={request.telegram_id}, wallet={request.wallet_address}, early_backer={user.is_early_backer}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying proof: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 