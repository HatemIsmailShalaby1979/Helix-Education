"""Tests for grounding_engine models (SourceChunk, GroundingResult, GroundingFetchError)."""

from datetime import datetime

import pytest

from grounding_engine.grounding_models import (
    GroundingFetchError,
    GroundingResult,
    SourceChunk,
)


class TestSourceChunk:
    """Tests for SourceChunk validation and citation_text format."""

    def test_valid_source_chunk(self) -> None:
        """A fully populated SourceChunk should be created without error."""
        chunk = SourceChunk(
            content="This is some source content.",
            source_url="https://example.com/doc",
            source_title="Example Doc",
            retrieved_at="2025-01-15T10:00:00+00:00",
            citation_text="Example Doc (https://example.com/doc, retrieved 2025-01-15)",
        )
        assert chunk.content == "This is some source content."
        assert chunk.source_url == "https://example.com/doc"
        assert chunk.source_title == "Example Doc"
        assert chunk.citation_text == "Example Doc (https://example.com/doc, retrieved 2025-01-15)"

    def test_empty_source_url_raises(self) -> None:
        """source_url must not be empty."""
        with pytest.raises(ValueError, match="source_url must not be empty"):
            SourceChunk(
                content="content",
                source_url="",
                source_title="Title",
                retrieved_at="2025-01-15T10:00:00+00:00",
                citation_text="citation",
            )

    def test_blank_source_url_raises(self) -> None:
        """source_url with only whitespace must be rejected."""
        with pytest.raises(ValueError, match="source_url must not be empty"):
            SourceChunk(
                content="content",
                source_url="   ",
                source_title="Title",
                retrieved_at="2025-01-15T10:00:00+00:00",
                citation_text="citation",
            )

    def test_empty_source_title_raises(self) -> None:
        """source_title must not be empty."""
        with pytest.raises(ValueError, match="source_title must not be empty"):
            SourceChunk(
                content="content",
                source_url="https://example.com",
                source_title="",
                retrieved_at="2025-01-15T10:00:00+00:00",
                citation_text="citation",
            )

    def test_empty_content_raises(self) -> None:
        """content must not be empty."""
        with pytest.raises(ValueError, match="content must not be empty"):
            SourceChunk(
                content="",
                source_url="https://example.com",
                source_title="Title",
                retrieved_at="2025-01-15T10:00:00+00:00",
                citation_text="citation",
            )

    def test_empty_citation_text_raises(self) -> None:
        """citation_text must not be empty."""
        with pytest.raises(ValueError, match="citation_text must not be empty"):
            SourceChunk(
                content="content",
                source_url="https://example.com",
                source_title="Title",
                retrieved_at="2025-01-15T10:00:00+00:00",
                citation_text="",
            )


class TestGroundingResult:
    """Tests for GroundingResult construction and defaults."""

    def test_valid_grounding_result(self) -> None:
        """A GroundingResult should set fetched_at automatically if not provided."""
        result = GroundingResult(
            topic="algebra",
            query_used="algebra fundamentals",
        )
        assert result.topic == "algebra"
        assert result.query_used == "algebra fundamentals"
        assert result.chunks == []
        # fetched_at should be set to current ISO8601
        assert result.fetched_at != ""
        # Should be parseable as ISO8601
        datetime.fromisoformat(result.fetched_at)

    def test_grounding_result_with_chunks(self) -> None:
        """A GroundingResult can hold SourceChunks."""
        chunk = SourceChunk(
            content="Content",
            source_url="https://example.com",
            source_title="Title",
            retrieved_at="2025-01-15T10:00:00+00:00",
            citation_text="citation",
        )
        result = GroundingResult(
            topic="algebra",
            query_used="algebra",
            chunks=[chunk],
        )
        assert len(result.chunks) == 1
        assert result.chunks[0].source_url == "https://example.com"

    def test_grounding_result_explicit_fetched_at(self) -> None:
        """Explicit fetched_at should be preserved."""
        result = GroundingResult(
            topic="t",
            query_used="q",
            fetched_at="2025-06-01T12:00:00+00:00",
        )
        assert result.fetched_at == "2025-06-01T12:00:00+00:00"


class TestGroundingFetchError:
    """Tests for GroundingFetchError exception."""

    def test_is_exception(self) -> None:
        """GroundingFetchError should be an Exception subclass."""
        err = GroundingFetchError("something broke")
        assert isinstance(err, Exception)
        assert str(err) == "something broke"

    def test_can_chain_cause(self) -> None:
        """GroundingFetchError supports exception chaining with __cause__."""
        try:
            raise RuntimeError("underlying issue")
        except RuntimeError as e:
            with pytest.raises(GroundingFetchError) as exc_info:
                raise GroundingFetchError("fetch failed") from e
            assert exc_info.value.__cause__ is e
