"""Vault-backed SealedAnswerKeyStore adapter using Vault KV v2 HTTP API.

This hardened adapter adds timeouts, retries with exponential backoff, and improved
error handling to be more resilient in real networks and CI.
"""

from __future__ import annotations

import logging
import time

import requests
from requests.exceptions import HTTPError, RequestException

from .event_store import compute_key_hash
from .scoring_engine import AnswerKey

LOG = logging.getLogger(__name__)


class VaultAdapterError(Exception):
    pass


class VaultSealedAnswerKeyStore:
    def __init__(
        self,
        vault_addr: str,
        token: str,
        kv_mount: str = "secret",
        timeout: float = 5.0,
        retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.vault_addr = vault_addr.rstrip("/")
        self.token = token
        self.kv_mount = kv_mount.strip("/")
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.backoff_factor = float(backoff_factor)
        self.session = requests.Session()
        self.session.headers.update({"X-Vault-Token": self.token})

    def _write_path(self, quiz_item_id: str) -> str:
        return f"/v1/{self.kv_mount}/data/helix/sealed_keys/{quiz_item_id}"

    def _read_path(self, quiz_item_id: str) -> str:
        return f"/v1/{self.kv_mount}/data/helix/sealed_keys/{quiz_item_id}"

    def _request(self, method: str, url: str, **kwargs):
        last_exc = None
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.request(method, url, timeout=self.timeout, **kwargs)
                # For 5xx errors, consider retrying
                if 500 <= getattr(resp, "status_code", 500) < 600:
                    LOG.warning("Vault %s returned %s on %s (attempt %d)", method, resp.status_code, url, attempt)
                    last_exc = HTTPError(f"status {resp.status_code}")
                    # fall through to retry
                else:
                    resp.raise_for_status()
                    return resp
            except RequestException as e:
                last_exc = e
                LOG.debug("Vault request error on attempt %d: %s", attempt, e)
            # backoff before next attempt
            if attempt < self.retries:
                sleep_time = self.backoff_factor * (2**attempt)
                time.sleep(sleep_time)
        raise VaultAdapterError(f"Vault request failed after {self.retries + 1} attempts: {last_exc}")

    def store(self, quiz_item_id: str, key: AnswerKey) -> str:
        payload = {
            "data": {
                "required_keywords": list(key.required_keywords),
                "forbidden_keywords": list(key.forbidden_keywords),
                "min_length_chars": int(key.min_length_chars),
            }
        }
        url = self.vault_addr + self._write_path(quiz_item_id)
        try:
            resp = self._request("POST", url, json=payload)
            # successful write
            return compute_key_hash(key)
        except VaultAdapterError as e:
            LOG.error("Failed to store key %s: %s", quiz_item_id, e)
            raise

    def retrieve(self, quiz_item_id: str) -> AnswerKey | None:
        url = self.vault_addr + self._read_path(quiz_item_id)
        try:
            resp = self._request("GET", url)
        except VaultAdapterError:
            LOG.exception("Failed to retrieve key %s from Vault", quiz_item_id)
            raise
        if resp.status_code == 404:
            return None
        try:
            data = resp.json()
            d = data.get("data", {}).get("data", {})
            return AnswerKey(
                required_keywords=d.get("required_keywords", []),
                forbidden_keywords=d.get("forbidden_keywords", []),
                min_length_chars=d.get("min_length_chars", 0),
            )
        except Exception as e:
            LOG.error("Malformed Vault response for %s: %s", quiz_item_id, e)
            return None
