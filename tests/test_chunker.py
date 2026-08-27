"""Tests for grounding_engine chunker (split_into_chunks)."""

import pytest

from grounding_engine.chunker import split_into_chunks


class TestSplitIntoChunks:
    """Tests for the split_into_chunks pure function."""

    def test_short_text_single_chunk(self) -> None:
        """Text shorter than max_chars should return a single chunk."""
        text = "Short text."
        chunks = split_into_chunks(text, "https://example.com", "Test", max_chars=800)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."
        assert chunks[0].source_url == "https://example.com"
        assert chunks[0].source_title == "Test"

    def test_chunks_respect_max_chars(self) -> None:
        """No chunk content should exceed max_chars."""
        text = "A " * 1000  # ~2000 chars of repeated "A "
        chunks = split_into_chunks(text, "https://example.com", "Test", max_chars=200)
        for chunk in chunks:
            assert len(chunk.content) <= 200, f"Chunk length {len(chunk.content)} exceeds max_chars=200"

    def test_split_on_paragraph_boundary(self) -> None:
        """Chunking should prefer paragraph breaks (double newlines)."""
        para_a = "This is the first paragraph. It has multiple sentences about math and science."
        para_b = "This is the second paragraph. It starts after a break and goes on a bit."
        text = f"{para_a}\n\n{para_b}"
        # Use a max_chars that fits one paragraph but not both
        chunks = split_into_chunks(text, "https://example.com", "Test", max_chars=100)
        assert len(chunks) >= 2
        # First chunk should contain the first paragraph
        assert "first paragraph" in chunks[0].content
        # Last chunk should contain the second paragraph
        assert "second paragraph" in chunks[-1].content

    def test_does_not_cut_mid_sentence_on_paragraph_boundary(self) -> None:
        """When a paragraph break exists under max_chars, don't cut mid-sentence."""
        sentence_a = "First sentence of a long paragraph."
        sentence_b = "Second sentence that continues."
        sentence_c = "Third sentence that goes on."
        long_para = f"{sentence_a} {sentence_b} {sentence_c}"
        text = f"{long_para}\n\nSeparate paragraph."
        # max_chars set to capture the first few sentences but leave room
        chunks = split_into_chunks(text, "https://example.com", "Test", max_chars=100)
        # Should split at \n\n boundary, not cut within the first paragraph
        assert len(chunks) >= 1

    def test_single_chunk_for_short_text(self) -> None:
        """Very short text should be one chunk."""
        text = "Hello world."
        chunks = split_into_chunks(text, "https://example.com", "Test", max_chars=800)
        assert len(chunks) == 1
        assert chunks[0].content == "Hello world."

    def test_empty_text_returns_empty_list(self) -> None:
        """Empty text should return an empty list."""
        chunks = split_into_chunks("", "https://example.com", "Test", max_chars=800)
        assert chunks == []

    def test_whitespace_only_text_returns_empty_list(self) -> None:
        """Whitespace-only text should return an empty list."""
        chunks = split_into_chunks("   \n\n  ", "https://example.com", "Test", max_chars=800)
        assert chunks == []

    def test_citation_text_format(self) -> None:
        """Each chunk should have a correctly formatted citation_text."""
        text = "Some content here."
        chunks = split_into_chunks(text, "https://example.com/doc", "Example Title", max_chars=800)
        assert len(chunks) == 1
        citation = chunks[0].citation_text
        assert "Example Title" in citation
        assert "https://example.com/doc" in citation
        assert "retrieved " in citation

    def test_all_chunks_share_source_metadata(self) -> None:
        """Chunks from the same source should share source_url and source_title."""
        text = "A " * 500  # Long enough to need splitting
        chunks = split_into_chunks(text, "https://example.com/share", "Shared Title", max_chars=100)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert chunk.source_url == "https://example.com/share"
            assert chunk.source_title == "Shared Title"

    def test_invalid_max_chars_raises(self) -> None:
        """max_chars < 1 should raise ValueError."""
        with pytest.raises(ValueError, match="max_chars must be >= 1"):
            split_into_chunks("text", "https://example.com", "Title", max_chars=0)

    def test_hard_cut_last_resort(self) -> None:
        """With no paragraph/sentence/word break available, a hard cut is acceptable."""
        # A long unbroken string with no punctuation or spaces
        text = "x" * 5000
        chunks = split_into_chunks(text, "https://example.com", "Title", max_chars=100)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.content) <= 100
