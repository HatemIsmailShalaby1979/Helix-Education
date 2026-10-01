"""Tests for the KMS-backed encrypted sealed answer-key store.

Covers the fail-closed contract (no master key configured) and both
configured paths (explicit argument, environment variable), plus the
timezone-aware timestamp.
"""

from datetime import datetime

import pytest
from cryptography.fernet import InvalidToken

from state_core.security.encrypted_key_store import (
    ENV_MASTER_KEY,
    EncryptedSealedKeyStore,
    MissingMasterKeyError,
)


@pytest.fixture(autouse=True)
def _clear_master_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure HELIX_KMS_MASTER_KEY is absent unless a test sets it."""
    monkeypatch.delenv(ENV_MASTER_KEY, raising=False)


# ── Not configured: fail closed ──────────────────────────────────────


def test_missing_master_key_raises(tmp_path) -> None:
    with pytest.raises(MissingMasterKeyError):
        EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"))


def test_missing_master_key_is_a_value_error(tmp_path) -> None:
    with pytest.raises(ValueError):
        EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"))


def test_missing_master_key_message_names_the_fix(tmp_path) -> None:
    with pytest.raises(MissingMasterKeyError) as excinfo:
        EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"))
    message = str(excinfo.value)
    assert ENV_MASTER_KEY in message
    assert "kms_master_key" in message


def test_empty_or_whitespace_master_key_raises(tmp_path) -> None:
    for bad_key in ("", "   "):
        with pytest.raises(MissingMasterKeyError):
            EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"), bad_key)


def test_no_file_is_created_when_not_configured(tmp_path) -> None:
    target = tmp_path / "keys.jsonl"
    with pytest.raises(MissingMasterKeyError):
        EncryptedSealedKeyStore(str(target))
    assert not target.exists()


# ── Configured ───────────────────────────────────────────────────────


def test_master_key_from_argument_roundtrips(tmp_path) -> None:
    store = EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"), "unit-test-master-key")
    store.store_key("qi_1", {"required_keywords": ["x"]})
    assert store.retrieve_key("qi_1") == {"required_keywords": ["x"]}


def test_master_key_from_environment_roundtrips(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_MASTER_KEY, "env-master-key")
    store = EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"))
    store.store_key("qi_2", {"required_keywords": ["y"]})
    assert store.retrieve_key("qi_2") == {"required_keywords": ["y"]}


def test_argument_takes_precedence_over_environment(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(ENV_MASTER_KEY, "env-master-key")
    store = EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"), "arg-master-key")
    assert store._master_key == "arg-master-key"


def test_stored_key_is_not_plaintext_on_disk(tmp_path) -> None:
    path = tmp_path / "keys.jsonl"
    store = EncryptedSealedKeyStore(str(path), "unit-test-master-key")
    store.store_key("qi_3", {"required_keywords": ["secret-marker"]})
    assert "secret-marker" not in path.read_text(encoding="utf-8")


def test_wrong_master_key_cannot_decrypt(tmp_path) -> None:
    path = tmp_path / "keys.jsonl"
    EncryptedSealedKeyStore(str(path), "master-key-a").store_key("qi_4", {"required_keywords": ["z"]})
    with pytest.raises(InvalidToken):
        EncryptedSealedKeyStore(str(path), "master-key-b").retrieve_key("qi_4")


def test_retrieve_missing_id_returns_none(tmp_path) -> None:
    store = EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"), "unit-test-master-key")
    assert store.retrieve_key("absent") is None


def test_retrieve_missing_file_returns_none(tmp_path) -> None:
    store = EncryptedSealedKeyStore(str(tmp_path / "absent.jsonl"), "unit-test-master-key")
    assert store.retrieve_key("absent") is None


# ── Timestamp ────────────────────────────────────────────────────────


def test_timestamp_is_timezone_aware(tmp_path) -> None:
    store = EncryptedSealedKeyStore(str(tmp_path / "keys.jsonl"), "unit-test-master-key")
    parsed = datetime.fromisoformat(store._get_timestamp())
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() is not None
