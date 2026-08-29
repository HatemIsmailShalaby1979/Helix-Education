"""Grounding models for the Learning Engine.

Defines the data structures for retrieved source material and grounding results.
"""

from dataclasses import dataclass, field
try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc


@dataclass
class SourceChunk:
    """A single chunk of source material with citation metadata.

    Inputs:
        content: The text content of this chunk.
        source_url: The URL where this content was retrieved from.
        source_title: The title of the source document/page.
        retrieved_at: ISO8601 timestamp when this chunk was retrieved.
        citation_text: Pre-formatted citation string for use in
            ContentService.commit_section's source_citations parameter.
            Format: "{source_title} ({source_url}, retrieved {date})"
    """

    content: str
    source_url: str
    source_title: str
    retrieved_at: str
    citation_text: str

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.source_url or not self.source_url.strip():
            raise ValueError("source_url must not be empty")
        if not self.source_title or not self.source_title.strip():
            raise ValueError("source_title must not be empty")
        if not self.content or not self.content.strip():
            raise ValueError("content must not be empty")
        if not self.citation_text or not self.citation_text.strip():
            raise ValueError("citation_text must not be empty")


@dataclass
class GroundingResult:
    """Result of a grounding fetch operation.

    Inputs:
        topic: The original topic that was grounded.
        query_used: The actual search query sent to the API (may differ
            from topic if query refinement was applied).
        chunks: List of SourceChunk objects retrieved.
        fetched_at: ISO8601 timestamp when the fetch completed.
    """

    topic: str
    query_used: str
    chunks: list[SourceChunk] = field(default_factory=list)
    fetched_at: str = ""

    def __post_init__(self) -> None:
        """Set fetched_at if not provided."""
        if not self.fetched_at:
            self.fetched_at = datetime.now(UTC).isoformat()


class GroundingFetchError(Exception):
    """Raised when a grounding fetch operation fails.

    This exception is raised for any fetch failure (timeout, non-200
    response, malformed response, network error). It is NOT raised for
    "no results found" â€” that case returns a GroundingResult with
    chunks=[].
    """

    pass
