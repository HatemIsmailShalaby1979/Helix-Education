"""
KMS-Backed Encrypted Sealed Answer Key Store.

Implements envelope encryption for answer keys using a master key from a KMS.
This replaces the plaintext JSONL storage with a secure, auditable alternative.
"""

import base64
import json
import logging
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class EncryptedSealedKeyStore:
    def __init__(self, storage_path: str, kms_master_key: str = None):
        """
        Initialize the encrypted store.

        Args:
            storage_path: Path to the encrypted JSONL file.
            kms_master_key: The master key from KMS (or a local secret for dev).
        """
        self.storage_path = storage_path
        # In production, this would interact with Azure Key Vault or AWS KMS
        # For this implementation, we use the provided key to derive a Fernet key
        self._master_key = kms_master_key or os.getenv("HELIX_KMS_MASTER_KEY", "dev-secret-key")
        self._fernet = self._derive_fernet_key()

    def _derive_fernet_key(self) -> Fernet:
        """Derives a 32-byte url-safe base64-encoded key for Fernet."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"helix_salt_v1",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._master_key.encode()))
        return Fernet(key)

    def store_key(self, assessment_id: str, answer_key: dict):
        """Encrypts and appends an answer key to the store."""
        plaintext = json.dumps(answer_key).encode()
        ciphertext = self._fernet.encrypt(plaintext)

        entry = {"id": assessment_id, "data": base64.b64encode(ciphertext).decode(), "timestamp": self._get_timestamp()}

        with open(self.storage_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info(f"Encrypted key stored for assessment {assessment_id}")

    def retrieve_key(self, assessment_id: str) -> dict:
        """Retrieves and decrypts an answer key by ID."""
        if not os.path.exists(self.storage_path):
            return None

        with open(self.storage_path) as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry["id"] == assessment_id:
                    ciphertext = base64.b64decode(entry["data"])
                    plaintext = self._fernet.decrypt(ciphertext)
                    return json.loads(plaintext)
        return None

    def _get_timestamp(self):
        from datetime import datetime

        return datetime.utcnow().isoformat()
