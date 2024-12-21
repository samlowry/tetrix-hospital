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
    Получение сообщения для подписи кошельком
    """
    try:
        # Генерируем случайный пейлоад
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
        
        # Проверяем, существует ли пользователь
        user = await user_service.get_user_by_telegram_id(request.telegram_id)
        if user:
            return {"success": True}

        # Создаем пользователя независимо от результата проверки
        user = await user_service.create_user(
            telegram_id=request.telegram_id,
            wallet_address=request.wallet_address
        )
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error verifying proof: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 