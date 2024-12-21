from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
from services.ton_service import TonService
from services.redis_service import RedisService
from services.ton_proof_service import TonProofService
import jwt
from datetime import datetime, timedelta
import os

router = APIRouter(prefix="/api", tags=["ton"])

# Dependency to get services
def get_ton_service():
    return TonService()

def get_redis_service():
    return RedisService()

def get_ton_proof_service():
    return TonProofService()

# Models for request/response
class ProofRequest(BaseModel):
    address: str
    proof: Dict[str, Any]
    tg_init_data: Optional[str] = None

class WalletRequest(BaseModel):
    address: str

class TransactionRequest(BaseModel):
    tx_hash: str

# Routes
@router.post("/generate_payload")
async def generate_payload(
    ton_proof_service: TonProofService = Depends(get_ton_proof_service)
):
    """Generate a random payload for TON Proof"""
    payload = ton_proof_service.generate_payload()
    return {"payload": payload}

@router.post("/check_proof")
async def check_proof(
    request: ProofRequest,
    ton_proof_service: TonProofService = Depends(get_ton_proof_service),
    redis_service: RedisService = Depends(get_redis_service)
):
    """Verify TON Connect proof"""
    try:
        # Verify proof
        is_valid = ton_proof_service.check_proof(request.dict())
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid proof")

        # Generate JWT token
        token = jwt.encode(
            {
                'address': request.address,
                'exp': datetime.utcnow() + timedelta(days=30)
            },
            os.getenv('JWT_SECRET_KEY', 'default-secret-key'),
            algorithm='HS256'
        )

        # For now, return simple response
        # TODO: Add user registration and early backer check
        return {
            "status": "registered",
            "message": "Proof verified successfully",
            "token": token
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/wallet/{address}")
async def get_wallet_info(
    address: str,
    ton_service: TonService = Depends(get_ton_service)
):
    """Get wallet information"""
    info = await ton_service.get_wallet_info(address)
    if not info:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return info

@router.get("/tx/{tx_hash}")
async def check_transaction(
    tx_hash: str,
    ton_service: TonService = Depends(get_ton_service)
):
    """Check transaction status"""
    status = await ton_service.check_transaction(tx_hash)
    if not status:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return status 