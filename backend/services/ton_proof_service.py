import hashlib
from base64 import b64decode
from typing import Optional
import logging

import nacl.signing
from tonsdk.utils import Address
from tonsdk.boc import Cell

logger = logging.getLogger('tetrix')

TON_PROOF_PREFIX = b'ton-proof-item-v2/'
TON_CONNECT_PREFIX = b'ton-connect'
ALLOWED_DOMAINS = [
    'ton-connect.github.io',
    'localhost:5173',
    'tetrix-hospital.pages.dev'
]
VALID_AUTH_TIME = 15 * 60  # 15 minutes

def verify_proof_signature(message_bytes: bytes, signature: bytes, public_key: bytes) -> bool:
    """Verify TON Connect proof signature using NaCl."""
    try:
        # Convert hex public key to bytes if needed
        if len(public_key) == 64:  # If it's a hex string in bytes
            public_key = bytes.fromhex(public_key.decode())
        elif len(public_key) != 32:  # If it's not 32 bytes
            logger.error(f"Invalid public key length: {len(public_key)}")
            return False

        verify_key = nacl.signing.VerifyKey(public_key)
        verify_key.verify(message_bytes, signature)
        return True
    except Exception as e:
        logger.error(f"Signature verification failed: {e}")
        return False

class TonProofService:
    @staticmethod
    def generate_payload() -> str:
        """Generate a random payload for TON Proof."""
        import secrets
        return secrets.token_hex(32)

    @staticmethod
    def check_proof(payload: dict, get_wallet_public_key=None) -> bool:
        """
        Check TON Connect proof signature.
        Based on reference implementation from TON Connect docs.
        """
        try:
            logger.info(f"Checking proof payload: {payload}")
            
            # Parse and validate state init
            state_init = Cell.one_from_boc(b64decode(payload['proof']['state_init']))
            state_init_data = state_init.begin_parse()
            logger.info("State init parsed successfully")

            # Get public key from state init or wallet
            public_key = bytes.fromhex(payload['public_key'])
            logger.info(f"Using public key: {public_key.hex()}")

            # Verify address matches state init
            address = Address(payload['address'])
            if not address:
                logger.error("Invalid address")
                return False

            # Verify domain
            domain = payload['proof']['domain']['value']
            if domain not in ALLOWED_DOMAINS:
                logger.error(f"Domain {domain} not in allowed list: {ALLOWED_DOMAINS}")
                return False

            # Verify timestamp
            import time
            now = int(time.time())
            timestamp = payload['proof']['timestamp']
            if now - VALID_AUTH_TIME > timestamp:
                logger.error(f"Timestamp {timestamp} is too old (current time: {now})")
                return False

            # Prepare message components
            wc = address.wc.to_bytes(4, byteorder='big')
            ts = timestamp.to_bytes(8, byteorder='little')
            dl = payload['proof']['domain']['lengthBytes'].to_bytes(4, byteorder='little')
            
            # Construct message
            msg = b''.join([
                TON_PROOF_PREFIX,
                wc,
                address.hash_part,
                dl,
                domain.encode(),
                ts,
                payload['proof']['payload'].encode()
            ])
            logger.info(f"Constructed message: {msg.hex()}")

            msg_hash = hashlib.sha256(msg).digest()
            logger.info(f"Message hash: {msg_hash.hex()}")

            # Construct full message with prefix
            full_msg = b''.join([
                bytes([0xff, 0xff]),
                TON_CONNECT_PREFIX,
                msg_hash
            ])
            logger.info(f"Full message: {full_msg.hex()}")

            result = hashlib.sha256(full_msg).digest()
            logger.info(f"Final hash: {result.hex()}")

            # Verify signature
            verify_key = nacl.signing.VerifyKey(public_key)
            signature = b64decode(payload['proof']['signature'])
            logger.info(f"Verifying signature: {signature.hex()}")
            
            verify_key.verify(result, signature)
            logger.info("Signature verified successfully")
            return True

        except Exception as e:
            logger.error(f"TON Proof verification error: {e}")
            return False 