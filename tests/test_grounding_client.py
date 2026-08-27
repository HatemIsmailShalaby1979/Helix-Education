"""Tests for grounding_engine clients (StubGroundingClient, HttpGroundingClient).

All tests use deterministic/mocked data — zero live network calls.
"""

from unittest import mock

import pytest

from grounding_engine.grounding_client import (
    GroundingClient,
    GroundingConfig,
    HttpGroundingClient,
    StubGroundingClient,
)
from grounding_engine.grounding_models import (
    GroundingFetchError,
    GroundingResult,
    SourceChunk,
)


class TestStubGroundingClient:
    """Tests for the deterministic StubGroundingClient."""

    def test_returns_canned_response(self) -> None:
        """Stub should return the exact GroundingResult for a mapped topic."""
        expected = GroundingResult(
            topic="algebra",
            query_used="algebra fundamentals",
            chunks=[
                SourceChunk(
                    content="Algebra is the study of variables.",
                    source_url="https://example.com/algebra",
                    source_title="Algebra 101",
                    retrieved_at="2025-01-15T10:00:00+00:00",
                    citation_text="Algebra 101 (https://example.com/algebra, retrieved 2025-01-15)",
                ),
            ],
        )
        client = StubGroundingClient(canned_responses={"algebra": expected})
        result = client.fetch("algebra")
        assert result is expected  # Same object identity

    def test_respects_max_chunks_truncation(self) -> None:
        """When max_chunks is smaller than the canned response's chunk count, truncate."""
        chunks = [
            SourceChunk(
                content=f"Chunk {i}",
                source_url="https://example.com",
                source_title="Title",
                retrieved_at="2025-01-15T10:00:00+00:00",
                citation_text="citation",
            )
            for i in range(10)
        ]
        result = GroundingResult(topic="t", query_used="q", chunks=chunks)
        client = StubGroundingClient(canned_responses={"t": result})
        fetched = client.fetch("t", max_chunks=3)
        assert len(fetched.chunks) == 3

    def test_raises_for_unmapped_topic_no_default(self) -> None:
        """Unmapped topic with no default should raise GroundingFetchError."""
        client = StubGroundingClient(canned_responses={})
        with pytest.raises(GroundingFetchError, match="No canned response configured"):
            client.fetch("unknown_topic")

    def test_uses_default_for_unmapped_topic(self) -> None:
        """If a default_response is provided, unmapped topics should use it."""
        default = GroundingResult(topic="default", query_used="default query")
        client = StubGroundingClient(
            canned_responses={"existing": GroundingResult(topic="e", query_used="e")},
            default_response=default,
        )
        result = client.fetch("unknown")
        assert result.topic == "default"
        assert result.query_used == "default query"

    def test_default_respects_max_chunks(self) -> None:
        """Default response should also respect max_chunks truncation."""
        chunks = [
            SourceChunk(
                content=f"C{i}",
                source_url="https://example.com",
                source_title="T",
                retrieved_at="2025-01-15T10:00:00+00:00",
                citation_text="cit",
            )
            for i in range(10)
        ]
        default = GroundingResult(topic="d", query_used="d", chunks=chunks)
        client = StubGroundingClient(
            canned_responses={},
            default_response=default,
        )
        result = client.fetch("anything", max_chunks=2)
        assert len(result.chunks) == 2

    def test_implements_abc(self) -> None:
        """StubGroundingClient is a GroundingClient."""
        client = StubGroundingClient(canned_responses={})
        assert isinstance(client, GroundingClient)


class TestHttpGroundingClient:
    """Tests for HttpGroundingClient using mocked requests calls."""

    @staticmethod
    def _make_result_item(title: str, url: str, content: str) -> dict:
        return {"title": title, "url": url, "content": content}

    def test_fetch_parses_valid_response(self) -> None:
        """A 200 response with valid JSON should be parsed into GroundingResult."""
        config = GroundingConfig(api_url="https://api.example.com/search")
        client = HttpGroundingClient(config)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                self._make_result_item(
                    "Algebra Basics",
                    "https://example.com/algebra",
                    "Algebra is a branch of mathematics. It deals with symbols.",
                ),
            ],
        }

        with mock.patch.object(client._session, "post", return_value=mock_response):
            result = client.fetch("algebra")

        assert result.topic == "algebra"
        assert result.query_used == "algebra"
        assert len(result.chunks) >= 1
        assert "Algebra is a branch" in result.chunks[0].content

    def test_fetch_uses_snippet_fallback(self) -> None:
        """If 'content' is absent, 'snippet' should be used as content."""
        config = GroundingConfig(api_url="https://api.example.com/search")
        client = HttpGroundingClient(config)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Doc",
                    "url": "https://example.com/doc",
                    "snippet": "Snippet content here.",
                },
            ],
        }

        with mock.patch.object(client._session, "post", return_value=mock_response):
            result = client.fetch("topic")

        assert len(result.chunks) >= 1
        assert "Snippet content here." in result.chunks[0].content

    def test_fetch_raises_on_timeout(self) -> None:
        """A timeout should raise GroundingFetchError with cause."""
        config = GroundingConfig(api_url="https://api.example.com/search", timeout_seconds=1)
        client = HttpGroundingClient(config)

        import requests

        with mock.patch.object(
            client._session,
            "post",
            side_effect=requests.Timeout("timed out"),
        ):
            with pytest.raises(GroundingFetchError) as exc_info:
                client.fetch("algebra")
            assert "timed out" in str(exc_info.value).lower()
            assert isinstance(exc_info.value.__cause__, requests.Timeout)

    def test_fetch_raises_on_non_200(self) -> None:
        """A non-200 response should raise GroundingFetchError."""
        config = GroundingConfig(api_url="https://api.example.com/search")
        client = HttpGroundingClient(config)

        mock_response = mock.MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with mock.patch.object(client._session, "post", return_value=mock_response):
            with pytest.raises(GroundingFetchError, match="API returned 500"):
                client.fetch("algebra")

    def test_fetch_raises_on_network_error(self) -> None:
        """A network error (ConnectionError) should raise GroundingFetchError."""
        config = GroundingConfig(api_url="https://api.example.com/search")
        client = HttpGroundingClient(config)

        import requests

        with mock.patch.object(
            client._session,
            "post",
            side_effect=requests.ConnectionError("connection refused"),
        ):
            with pytest.raises(GroundingFetchError) as exc_info:
                client.fetch("algebra")
            assert "Network error" in str(exc_info.value)

    def test_fetch_raises_on_invalid_json(self) -> None:
        """Non-JSON response should raise GroundingFetchError."""
        config = GroundingConfig(api_url="https://api.example.com/search")
        client = HttpGroundingClient(config)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with mock.patch.object(client._session, "post", return_value=mock_response):
            with pytest.raises(GroundingFetchError, match="not valid JSON"):
                client.fetch("algebra")

    def test_fetch_raises_on_non_list_results(self) -> None:
        """If 'results' is not a list, GroundingFetchError should be raised."""
        config = GroundingConfig(api_url="https://api.example.com/search")
        client = HttpGroundingClient(config)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": "not a list"}

        with mock.patch.object(client._session, "post", return_value=mock_response):
            with pytest.raises(GroundingFetchError, match="not a list"):
                client.fetch("algebra")

    def test_fetch_skips_invalid_items(self) -> None:
        """Items missing title/url/content should be silently skipped."""
        config = GroundingConfig(api_url="https://api.example.com/search")
        client = HttpGroundingClient(config)

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                self._make_result_item("Good", "https://good.com", "Good content."),
                {"title": "No URL"},  # missing url and content
                {"url": "https://nourl.com"},  # missing title and content
                self._make_result_item("Good2", "https://good2.com", "More good content."),
            ],
        }

        with mock.patch.object(client._session, "post", return_value=mock_response):
            result = client.fetch("topic")

        # Only the two valid items should produce chunks
        assert len(result.chunks) >= 2

    def test_implements_abc(self) -> None:
        """HttpGroundingClient is a GroundingClient."""
        config = GroundingConfig(api_url="https://api.example.com/search")
        client = HttpGroundingClient(config)
        assert isinstance(client, GroundingClient)
