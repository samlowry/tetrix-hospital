from tonsdk.contract.wallet import WalletVersionEnum, Wallets
from tonsdk.utils import to_nano
import os
from loguru import logger

class TonClient:
    def __init__(self):
        self.tetrix_contract = os.getenv('TETRIX_CONTRACT_ADDRESS')

    async def get_balance(self, wallet_address: str) -> float:
        try:
            # Using tonsdk to get balance
            wallet = Wallets.create(
                version=WalletVersionEnum.v3r2,
                workchain=0,
                public_key=wallet_address
            )
            balance = wallet.balance
            return float(balance) / 1e9  # Convert from nanotons to TON
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0.0

    async def get_tetrix_balance(self, wallet_address: str) -> float:
        try:
            # TODO: Replace with actual contract call
            contract = await self.client.get_contract(self.tetrix_contract)
            balance = await contract.methods.balanceOf(wallet_address).call()
            return float(balance) / 1e9
        except Exception as e:
            logger.error(f"Error getting TETRIX balance: {e}")
            return 0.0

    async def transfer_tetrix(self, to_address: str, amount: float) -> bool:
        try:
            # TODO: Replace with actual contract interaction
            contract = await self.client.get_contract(self.tetrix_contract)
            tx = await contract.methods.transfer(to_address, int(amount * 1e9)).send()
            return bool(tx)
        except Exception as e:
            logger.error(f"Error transferring TETRIX: {e}")
            return False

    async def check_transaction_status(self, tx_hash: str) -> bool:
        try:
            # TODO: Implement transaction status check
            return True
        except Exception as e:
            print(f"Error checking transaction: {e}")
            return False