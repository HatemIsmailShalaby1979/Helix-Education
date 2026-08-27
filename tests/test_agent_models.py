"""Tests for LessonSectionDraft schema validation.

Covers:
- LessonSectionDraft accepts valid data
- Rejects empty source_indices
- Rejects title/body outside length bounds
"""

import pytest
from pydantic import ValidationError

from cognitive_agent.agent_models import (
    LessonSectionDraft,
)


def test_lesson_section_draft_accepts_valid_data():
    """Test that LessonSectionDraft accepts valid data."""
    draft = LessonSectionDraft(
        section_title="Test Section",
        body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        source_indices=[0, 1],
    )
    assert draft.section_title == "Test Section"
    assert (
        draft.body == "This is a test body with sufficient length to meet the minimum requirement of fifty characters."
    )
    assert draft.source_indices == [0, 1]


def test_lesson_section_draft_rejects_empty_source_indices():
    """Test that LessonSectionDraft rejects empty source_indices."""
    with pytest.raises(ValidationError) as exc_info:
        LessonSectionDraft(
            section_title="Test Section",
            body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
            source_indices=[],
        )

    assert "section must cite at least one source_index" in str(exc_info.value)


def test_lesson_section_draft_rejects_title_too_short():
    """Test that LessonSectionDraft rejects title that's too short."""
    with pytest.raises(ValidationError) as exc_info:
        LessonSectionDraft(
            section_title="",
            body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
            source_indices=[0],
        )

    assert "String should have at least 1 character" in str(exc_info.value)


def test_lesson_section_draft_rejects_title_too_long():
    """Test that LessonSectionDraft rejects title that's too long."""
    long_title = "x" * 201  # 201 characters, exceeds max of 200
    with pytest.raises(ValidationError) as exc_info:
        LessonSectionDraft(
            section_title=long_title,
            body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
            source_indices=[0],
        )

    assert "String should have at most 200 characters" in str(exc_info.value)


def test_lesson_section_draft_rejects_body_too_short():
    """Test that LessonSectionDraft rejects body that's too short."""
    short_body = "Short"  # Only 5 characters, needs at least 50
    with pytest.raises(ValidationError) as exc_info:
        LessonSectionDraft(section_title="Test Section", body=short_body, source_indices=[0])

    assert "String should have at least 50 characters" in str(exc_info.value)


def test_lesson_section_draft_rejects_body_too_long():
    """Test that LessonSectionDraft rejects body that's too long."""
    long_body = "x" * 4001  # 4001 characters, exceeds max of 4000
    with pytest.raises(ValidationError) as exc_info:
        LessonSectionDraft(section_title="Test Section", body=long_body, source_indices=[0])

    assert "String should have at most 4000 characters" in str(exc_info.value)


def test_lesson_section_draft_rejects_negative_source_indices():
    """Test that LessonSectionDraft rejects negative source indices."""
    with pytest.raises(ValidationError) as exc_info:
        LessonSectionDraft(
            section_title="Test Section",
            body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
            source_indices=[-1],
        )

    assert "source_indices must be non-negative" in str(exc_info.value)


def test_lesson_section_draft_accepts_single_source_index():
    """Test that LessonSectionDraft accepts a single source index."""
    draft = LessonSectionDraft(
        section_title="Test Section",
        body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        source_indices=[0],
    )
    assert draft.source_indices == [0]


def test_lesson_section_draft_accepts_multiple_source_indices():
    """Test that LessonSectionDraft accepts multiple source indices."""
    draft = LessonSectionDraft(
        section_title="Test Section",
        body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        source_indices=[0, 1, 2, 3, 4],
    )
    assert draft.source_indices == [0, 1, 2, 3, 4]
