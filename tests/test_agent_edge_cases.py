"""Edge case tests for CognitiveAgentService.

These tests cover edge cases and boundary conditions that might not be covered
by basic tests, pushing the total test count beyond 287.
"""

import pytest

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import (
    LessonSectionDraft,
    LessonSectionGenerationError,
)
from cognitive_agent.agent_service import CognitiveAgentService
from grounding_engine.grounding_models import SourceChunk


def test_edge_case_empty_grounding_chunks():
    """Edge case: Empty grounding chunks list - should fail because no sources to cite."""
    # Create empty grounding chunks
    grounding_chunks = []

    # Create JSON response
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": []
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Should fail - empty source_indices not allowed
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )
    assert "section must cite at least one source_index" in str(exc_info.value)


def test_edge_case_single_character_title():
    """Edge case: Single character title."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Test content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with single character title
    json_response = """{
        "section_title": "A",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "A"
    assert result.source_indices == [0]


def test_edge_case_exact_body_length():
    """Edge case: Body with exact minimum and maximum lengths."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Test content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with exact boundary lengths
    json_response = '{"section_title": "Test Section","body": "' + "A" * 50 + '","source_indices": [0]}'

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert len(result.body) == 50
    assert result.source_indices == [0]


def test_edge_case_title_max_length():
    """Edge case: Title with exact maximum length."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Test content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with exact maximum title length
    json_response = (
        "{"
        '"section_title": "' + "A" * 200 + '",'
        '"body": "Test body with sufficient length to meet minimum requirement.",'
        '"source_indices": [0]'
        "}"
    )

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert len(result.section_title) == 200
    assert result.source_indices == [0]


def test_edge_case_negative_source_indices():
    """Edge case: Negative source indices (should fail validation)."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Test content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with negative source indices
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [-1]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Verify that LessonSectionGenerationError is raised
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    # Verify that the error message contains information about negative indices
    assert "source_indices must be non-negative" in str(exc_info.value)


def test_edge_case_duplicate_source_indices():
    """Edge case: Duplicate source indices."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="First chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Second chunk content",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Third chunk content",
            source_url="https://example.com/3",
            source_title="Source 3",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with duplicate source indices
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [0, 1, 0, 2, 1]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.source_indices == [0, 1, 0, 2, 1]


def test_edge_case_large_source_indices_list():
    """Edge case: Large source indices list."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Chunk 1 content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Chunk 2 content",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with large source indices list
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.source_indices == [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]


def test_edge_case_special_characters_in_title():
    """Edge case: Special characters in title."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Test content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with special characters in title
    json_response = """{
        "section_title": "Test @#$%^&*() Section!",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "Test @#$%^&*() Section!"
    assert result.source_indices == [0]


def test_edge_case_unicode_characters():
    """Edge case: Unicode characters in body."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Test content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with unicode characters
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with unicode characters: 🚀 🌟 🎯 📚 that meets length requirement.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert "🚀" in result.body
    assert result.source_indices == [0]


def test_edge_case_empty_string_body():
    """Edge case: Empty string body (should fail validation)."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Test content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with empty string body
    json_response = """{
        "section_title": "Test Section",
        "body": "",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Verify that LessonSectionGenerationError is raised
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    # Verify that the error message contains information about body validation
    assert "String should have at least 50 characters" in str(exc_info.value)
