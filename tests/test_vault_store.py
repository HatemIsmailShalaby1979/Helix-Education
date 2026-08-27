from unittest.mock import patch

import requests

from state_core.scoring_engine import AnswerKey
from state_core.vault_store import VaultSealedAnswerKeyStore


class MockResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"Status {self.status_code}")


def test_store_and_retrieve_roundtrip():
    addr = "http://vault.test:8200"
    mount = "secret"
    qid = "qi_123"
    key = AnswerKey(required_keywords=["x"], forbidden_keywords=[], min_length_chars=0)

    write_url = f"{addr}/v1/{mount}/data/helix/sealed_keys/{qid}"
    read_url = write_url

    # Patch requests.Session.request used by the adapter
    def mock_request(method, url, timeout=None, **kwargs):
        if method.upper() == "POST":
            return MockResponse(200, {"data": {}})
        if method.upper() == "GET":
            return MockResponse(
                200, {"data": {"data": {"required_keywords": ["x"], "forbidden_keywords": [], "min_length_chars": 0}}}
            )
        return MockResponse(404, {})

    with patch("requests.Session.request", side_effect=mock_request):
        store = VaultSealedAnswerKeyStore(addr, token="t", kv_mount=mount)
        h = store.store(qid, key)
        assert isinstance(h, str) and len(h) == 64
        got = store.retrieve(qid)
        assert got is not None
        assert got.required_keywords == ["x"]
