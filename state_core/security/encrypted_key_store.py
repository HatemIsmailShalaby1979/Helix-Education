"""
KMS-Backed Encrypted Sealed Answer Key Store.

Implements envelope encryption for answer keys using a master key from a KMS.
This replaces the plaintext JSONL storage with a secure, auditable alternative.
"""

import base64
import json
import logging
import os
from datetime import UTC, datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

ENV_MASTER_KEY = "HELIX_KMS_MASTER_KEY"


class MissingMasterKeyError(ValueError):
    """Raised when no KMS master key is configured.

    Fail-closed: the store refuses to derive an encryption key from a
    built-in default, because doing so would silently produce ciphertext
    that any reader of the source can decrypt.
    """


class EncryptedSealedKeyStore:
    def __init__(self, storage_path: str, kms_master_key: str | None = None) -> None:
        """Initialize the encrypted store.

        Inputs:
            storage_path: Path to the encrypted JSONL file.
            kms_master_key: The master key from KMS (or a local secret for dev).
                When None or empty, the HELIX_KMS_MASTER_KEY environment
                variable is used.
        Raises:
            MissingMasterKeyError: If neither argument nor environment
                supplies a non-empty master key.
        """
        self.storage_path = storage_path
        # In production, this would interact with Azure Key Vault or AWS KMS.
        # For this implementation, the provided key derives a Fernet key.
        master_key = kms_master_key or os.environ.get(ENV_MASTER_KEY) or ""
        if not master_key.strip():
            raise MissingMasterKeyError(
                "No KMS master key configured. Pass kms_master_key explicitly or set "
                f"{ENV_MASTER_KEY}. Refusing to fall back to a built-in default key."
            )
        self._master_key = master_key
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

    def store_key(self, assessment_id: str, answer_key: dict) -> None:
        """Encrypts and appends an answer key to the store."""
        plaintext = json.dumps(answer_key).encode()
        ciphertext = self._fernet.encrypt(plaintext)

        entry = {"id": assessment_id, "data": base64.b64encode(ciphertext).decode(), "timestamp": self._get_timestamp()}

        with open(self.storage_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info(f"Encrypted key stored for assessment {assessment_id}")

    def retrieve_key(self, assessment_id: str) -> dict | None:
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

    def _get_timestamp(self) -> str:
        """Return the current UTC time as a timezone-aware ISO 8601 string."""
        return datetime.now(UTC).isoformat()
