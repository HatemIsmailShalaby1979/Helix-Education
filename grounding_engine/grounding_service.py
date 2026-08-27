"""Grounding service — public facade with in-memory caching.

This is the ONLY public entry point other code should use. QuizModule,
ContentService, or future Cognitive Agent code calls GroundingService,
never GroundingClient directly.
"""

import time

from .grounding_client import GroundingClient
from .grounding_models import GroundingResult


class GroundingService:
    """Public facade for fetching and caching grounding material.

    Wraps a GroundingClient with a plain in-memory cache. Cache entries
    expire after cache_ttl_seconds and are re-fetched on next access
    past expiry. The cache is NOT event-sourced — retrieved source
    material is regenerable input data, not durable learner history.

    Args:
        client: A GroundingClient implementation (stub or real).
        cache_ttl_seconds: Time-to-live for cache entries in seconds.
            Default 3600 (1 hour).
    """

    def __init__(self, client: GroundingClient, cache_ttl_seconds: int = 3600) -> None:
        self._client = client
        self._cache_ttl = cache_ttl_seconds
        # _cache: dict[(topic, max_chunks), (timestamp, GroundingResult)]
        self._cache: dict[tuple[str, int], tuple[float, GroundingResult]] = {}

    def get_grounding(self, topic: str, max_chunks: int = 5) -> GroundingResult:
        """Fetch grounding material for a topic, using in-memory cache.

        Cache key is a tuple of (topic, max_chunks). If a valid
        (non-expired) entry exists it is returned without calling the
        underlying client. Expired entries are re-fetched transparently.
        Fetch failures (GroundingFetchError) propagate uncaught — the
        cache never masks a real failure by returning stale data.

        Args:
            topic: The topic to search for.
            max_chunks: Maximum number of chunks to return.

        Returns:
            A GroundingResult containing retrieved source chunks.

        Raises:
            GroundingFetchError: If the underlying client fails to fetch.
        """
        cache_key = (topic, max_chunks)
        now = time.time()

        cached_entry = self._cache.get(cache_key)
        if cached_entry is not None:
            cached_time, cached_result = cached_entry
            if now - cached_time < self._cache_ttl:
                return cached_result

        # Cache miss or expired — fetch fresh
        result = self._client.fetch(topic, max_chunks)
        self._cache[cache_key] = (now, result)
        return result

    def clear_cache(self) -> None:
        """Clear all cached grounding results."""
        self._cache.clear()
