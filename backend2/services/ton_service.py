import logging
from typing import Optional, Dict, Any
from .ton_client import TonClient

logger = logging.getLogger(__name__)

class TonService:
    def __init__(self):
        self.client = TonClient()
        
    async def verify_proof(self, address: str, proof: Dict[str, Any]) -> bool:
        """Verify TON Connect proof"""
        try:
            return await self.client.verify_proof(address, proof)
        except Exception as e:
            logger.error(f"Error verifying TON proof: {e}")
            return False
            
    async def get_wallet_info(self, address: str) -> Optional[Dict[str, Any]]:
        """Get wallet information"""
        try:
            return await self.client.get_wallet_info(address)
        except Exception as e:
            logger.error(f"Error getting wallet info: {e}")
            return None
            
    async def check_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Check transaction status"""
        try:
            return await self.client.check_transaction(tx_hash)
        except Exception as e:
            logger.error(f"Error checking transaction: {e}")
            return None 