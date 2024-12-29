# TON Service module for handling TON blockchain interactions
# Provides functionality for proof verification, wallet info retrieval, and transaction checking

import logging
from typing import Optional, Dict, Any
from .ton_client import TonClient

# Logger instance for TON service operations
logger = logging.getLogger(__name__)

class TonService:
    """
    Service class for TON blockchain operations.
    Handles wallet verification, information retrieval, and transaction status checks.
    """
    
    def __init__(self):
        """
        Initialize TonService with a TonClient instance for blockchain interactions.
        """
        self.client = TonClient()
        
    async def verify_proof(self, address: str, proof: Dict[str, Any]) -> bool:
        """
        Verify TON Connect proof for wallet authentication.
        
        Args:
            address (str): The wallet address to verify
            proof (Dict[str, Any]): Proof data containing verification information
            
        Returns:
            bool: True if proof is valid, False otherwise
        """
        try:
            return await self.client.verify_proof(address, proof)
        except Exception as e:
            logger.error(f"Error verifying TON proof: {e}")
            return False
            
    async def get_wallet_info(self, address: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve wallet information from the TON blockchain.
        
        Args:
            address (str): The wallet address to query
            
        Returns:
            Optional[Dict[str, Any]]: Wallet information if successful, None if failed
        """
        try:
            return await self.client.get_wallet_info(address)
        except Exception as e:
            logger.error(f"Error getting wallet info: {e}")
            return None
            
    async def check_transaction(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """
        Check the status of a transaction on the TON blockchain.
        
        Args:
            tx_hash (str): Transaction hash to check
            
        Returns:
            Optional[Dict[str, Any]]: Transaction details if found, None if failed
        """
        try:
            return await self.client.check_transaction(tx_hash)
        except Exception as e:
            logger.error(f"Error checking transaction: {e}")
            return None