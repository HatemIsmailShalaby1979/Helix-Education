"""Text chunking for grounding source material.

Provides a pure function for splitting raw text into bounded,
citation-carrying chunks suitable for LLM grounding context.
"""

from datetime import UTC, datetime

from .grounding_models import SourceChunk


def _find_paragraph_break(text: str, max_pos: int) -> int | None:
    """Find the last paragraph break (double newline) before max_pos.

    Args:
        text: The text to search within.
        max_pos: The maximum position to search up to.

    Returns:
        The position after the paragraph break, or None if no break found.
    """
    # Search backwards from max_pos for \n\n
    # Use \r\n\r\n or \n\n (handles both Windows and Unix line endings)
    search_region = text[:max_pos]
    for pattern in ("\r\n\r\n", "\n\n", "\r\r"):
        idx = search_region.rfind(pattern)
        if idx != -1:
            return idx + len(pattern)
    return None


def _find_sentence_break(text: str, max_pos: int) -> int | None:
    """Find the last sentence-ending boundary before max_pos.

    Sentence boundaries are: periods, question marks, exclamation marks
    followed by whitespace or end of string.

    Args:
        text: The text to search within.
        max_pos: The maximum position to search up to.

    Returns:
        The position after the sentence-ending punctuation and whitespace,
        or None if no sentence break found.
    """
    search_region = text[:max_pos]
    # Match sentence-ending punctuation followed by space or end
    for pattern in (r"\. ", r"\? ", r"! ", r".\n", r"?\n", r"!\n"):
        # Find all occurrences and take the last one
        last_idx = -1
        start = 0
        while True:
            # Build a regex-free search for the literal pattern
            idx = search_region.find(pattern, start)
            if idx == -1:
                break
            last_idx = idx
            start = idx + 1

        if last_idx != -1:
            return last_idx + len(pattern)

    # Also check for period at end of max_pos region
    if max_pos > 0 and text[max_pos - 1] in ".!?":
        return max_pos

    return None


def _find_word_break(text: str, max_pos: int) -> int | None:
    """Find the last whitespace boundary before max_pos.

    Args:
        text: The text to search within.
        max_pos: The maximum position to search up to.

    Returns:
        The position after the last whitespace before max_pos,
        or None if no whitespace found.
    """
    search_region = text[:max_pos]
    idx = search_region.rfind(" ")
    if idx != -1:
        return idx + 1
    idx = search_region.rfind("\n")
    if idx != -1:
        return idx + 1
    idx = search_region.rfind("\t")
    if idx != -1:
        return idx + 1
    return None


def split_into_chunks(
    text: str,
    source_url: str,
    source_title: str,
    max_chars: int = 800,
) -> list[SourceChunk]:
    """Split raw text into bounded, citation-carrying chunks.

    Splits on paragraph boundaries where possible (preferred), then
    sentence boundaries, then word boundaries, and finally hard-cuts
    only as a last resort. Every returned chunk carries the same source
    metadata.

    Args:
        text: The raw text to split. May be empty, in which case an
            empty list is returned.
        source_url: The URL where this content was retrieved from.
            Must be non-empty (validated by SourceChunk.__post_init__).
        source_title: The title of the source document/page.
        max_chars: Maximum character length per chunk. Must be >= 1.

    Returns:
        A list of SourceChunk objects, each with content bounded by
        max_chars.

    Raises:
        ValueError: If max_chars < 1.
    """
    if max_chars < 1:
        raise ValueError("max_chars must be >= 1")

    if not text:
        return []

    retrieved_at = datetime.now(UTC).isoformat()
    # Date-only portion for citation text
    retrieved_date = retrieved_at[:10]

    chunks: list[SourceChunk] = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= max_chars:
            # Last chunk
            chunk_text = remaining
            remaining = ""
        else:
            # Need to split — try paragraph break first
            split_pos = _find_paragraph_break(remaining, max_chars)
            if split_pos is None:
                # Fall back to sentence break
                split_pos = _find_sentence_break(remaining, max_chars)
            if split_pos is None:
                # Fall back to word break
                split_pos = _find_word_break(remaining, max_chars)
            if split_pos is None or split_pos == 0:
                # Hard cut as last resort
                split_pos = max_chars

            chunk_text = remaining[:split_pos].strip()
            remaining = remaining[split_pos:].strip()

        if chunk_text:
            citation_text = f"{source_title} ({source_url}, retrieved {retrieved_date})"
            chunks.append(
                SourceChunk(
                    content=chunk_text,
                    source_url=source_url,
                    source_title=source_title,
                    retrieved_at=retrieved_at,
                    citation_text=citation_text,
                )
            )

    return chunks
