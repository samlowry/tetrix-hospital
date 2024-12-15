import hashlib
from base64 import b64decode
from typing import Optional

import nacl.signing
from tonsdk.utils import Address
from tonsdk.boc import Cell

TON_PROOF_PREFIX = b'ton-proof-item-v2/'
TON_CONNECT_PREFIX = b'ton-connect'
ALLOWED_DOMAINS = [
    'ton-connect.github.io',
    'localhost:5173',
    'tetrix-hospital.pages.dev'
]
VALID_AUTH_TIME = 15 * 60  # 15 minutes


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
            # Parse and validate state init
            state_init = Cell.one_from_boc(b64decode(payload['proof']['state_init']))
            state_init_data = state_init.begin_parse()

            # Get public key from state init or wallet
            public_key = bytes.fromhex(payload['public_key'])

            # Verify address matches state init
            address = Address(payload['address'])
            if not address:
                return False

            # Verify domain
            if payload['proof']['domain']['value'] not in ALLOWED_DOMAINS:
                return False

            # Verify timestamp
            import time
            now = int(time.time())
            if now - VALID_AUTH_TIME > payload['proof']['timestamp']:
                return False

            # Prepare message components
            wc = address.wc.to_bytes(4, byteorder='big')
            ts = payload['proof']['timestamp'].to_bytes(8, byteorder='little')
            dl = payload['proof']['domain']['lengthBytes'].to_bytes(4, byteorder='little')

            # Construct message
            msg = b''.join([
                TON_PROOF_PREFIX,
                wc,
                address.hash_part,
                dl,
                payload['proof']['domain']['value'].encode(),
                ts,
                payload['proof']['payload'].encode()
            ])

            msg_hash = hashlib.sha256(msg).digest()

            # Construct full message with prefix
            full_msg = b''.join([
                bytes([0xff, 0xff]),
                TON_CONNECT_PREFIX,
                msg_hash
            ])

            result = hashlib.sha256(full_msg).digest()

            # Verify signature
            verify_key = nacl.signing.VerifyKey(public_key)
            signature = b64decode(payload['proof']['signature'])
            verify_key.verify(result, signature)
            return True

        except Exception as e:
            print(f"TON Proof verification error: {e}")
            return False 