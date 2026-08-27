"""Tests for grounding_engine service (GroundingService caching and propagation)."""

import time
from unittest import mock

import pytest

from grounding_engine.grounding_client import GroundingClient, StubGroundingClient
from grounding_engine.grounding_models import GroundingFetchError, GroundingResult
from grounding_engine.grounding_service import GroundingService


class TestGroundingService:
    """Tests for GroundingService caching behavior."""

    def test_cache_hit_avoids_second_fetch(self) -> None:
        """A cache hit should not call client.fetch a second time."""
        result = GroundingResult(topic="algebra", query_used="algebra")
        client = StubGroundingClient(canned_responses={"algebra": result})
        service = GroundingService(client, cache_ttl_seconds=3600)

        # First call should hit the client
        r1 = service.get_grounding("algebra")
        assert r1 is result

        # Second call should be a cache hit — use a spy to verify
        with mock.patch.object(client, "fetch", wraps=client.fetch) as spy:
            r2 = service.get_grounding("algebra")
            assert r2 is result
            spy.assert_not_called()

    def test_different_topics_are_cached_independently(self) -> None:
        """Different topics should have independent cache entries."""
        r1 = GroundingResult(topic="algebra", query_used="algebra")
        r2 = GroundingResult(topic="geometry", query_used="geometry")
        client = StubGroundingClient(canned_responses={"algebra": r1, "geometry": r2})
        service = GroundingService(client, cache_ttl_seconds=3600)

        service.get_grounding("algebra")
        service.get_grounding("geometry")

        # Both are cached now; fetching each should not call client.fetch
        with mock.patch.object(client, "fetch", wraps=client.fetch) as spy:
            service.get_grounding("algebra")
            service.get_grounding("geometry")
            spy.assert_not_called()

    def test_different_max_chunks_separate_cache_keys(self) -> None:
        """Different max_chunks values should produce separate cache entries."""
        result = GroundingResult(topic="t", query_used="q")
        client = StubGroundingClient(canned_responses={"t": result})
        service = GroundingService(client, cache_ttl_seconds=3600)

        service.get_grounding("t", max_chunks=3)
        service.get_grounding("t", max_chunks=5)

        with mock.patch.object(client, "fetch", wraps=client.fetch) as spy:
            service.get_grounding("t", max_chunks=3)
            service.get_grounding("t", max_chunks=5)
            spy.assert_not_called()

    def test_cache_expiry_triggers_refetch(self) -> None:
        """After cache_ttl_seconds elapses, a re-fetch should occur."""
        result = GroundingResult(topic="algebra", query_used="algebra")
        client = StubGroundingClient(canned_responses={"algebra": result})
        # Use a very short TTL for testing
        service = GroundingService(client, cache_ttl_seconds=1)

        # First call caches the result
        service.get_grounding("algebra")

        # Wait for expiry
        time.sleep(1.1)

        # Second call should re-fetch
        with mock.patch.object(client, "fetch", wraps=client.fetch) as spy:
            r2 = service.get_grounding("algebra")
            assert r2 is result
            spy.assert_called_once()

    def test_fetch_error_propagates(self) -> None:
        """GroundingFetchError from the client should propagate through the service uncaught."""
        client = StubGroundingClient(canned_responses={})
        service = GroundingService(client, cache_ttl_seconds=3600)

        with pytest.raises(GroundingFetchError):
            service.get_grounding("unknown_topic")

    def test_cache_does_not_mask_failure_on_expired_entry(self) -> None:
        """If a cached entry has expired and the re-fetch fails, the error must propagate."""
        # Create a client that succeeds once then fails
        success_result = GroundingResult(topic="t", query_used="q")

        class FlippingClient(GroundingClient):
            def __init__(self) -> None:
                self.call_count = 0

            def fetch(self, topic: str, max_chunks: int = 5) -> GroundingResult:
                self.call_count += 1
                if self.call_count == 1:
                    return success_result
                raise GroundingFetchError("backend unavailable")

        client = FlippingClient()
        service = GroundingService(client, cache_ttl_seconds=1)

        # First call succeeds and caches
        r1 = service.get_grounding("t")
        assert r1 is success_result

        # Wait for expiry
        time.sleep(1.1)

        # Second call should attempt re-fetch and propagate the error
        with pytest.raises(GroundingFetchError, match="backend unavailable"):
            service.get_grounding("t")

    def test_clear_cache(self) -> None:
        """Clearing the cache should force re-fetch on next call."""
        result = GroundingResult(topic="algebra", query_used="algebra")
        client = StubGroundingClient(canned_responses={"algebra": result})
        service = GroundingService(client, cache_ttl_seconds=3600)

        # Cache it
        service.get_grounding("algebra")

        # Clear
        service.clear_cache()

        # Should re-fetch
        with mock.patch.object(client, "fetch", wraps=client.fetch) as spy:
            service.get_grounding("algebra")
            spy.assert_called_once()
