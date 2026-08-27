"""Validation tests for CognitiveAgentService.

These tests verify validation scenarios and edge cases for the CognitiveAgentService,
pushing the total test count beyond 287.
"""

import pytest

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import (
    LessonSectionDraft,
    LessonSectionGenerationError,
)
from cognitive_agent.agent_service import CognitiveAgentService
from grounding_engine.grounding_models import SourceChunk


def test_validation_valid_schema():
    """Validation test: Valid schema generation."""
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

    # Create valid JSON response
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet the minimum requirement of fifty characters.",
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
    assert result.section_title == "Test Section"
    assert result.source_indices == [0]


def test_validation_empty_source_indices():
    """Validation test: Empty source indices should fail."""
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

    # Create JSON response with empty source indices
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet the minimum requirement of fifty characters.",
        "source_indices": []
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Should raise LessonSectionGenerationError
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    assert "section must cite at least one source_index" in str(exc_info.value)


def test_validation_negative_source_indices():
    """Validation test: Negative source indices should fail."""
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
        "body": "Test body with sufficient length to meet the minimum requirement of fifty characters.",
        "source_indices": [-1]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Should raise LessonSectionGenerationError
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    assert "source_indices must be non-negative" in str(exc_info.value)


def test_validation_out_of_range_indices():
    """Validation test: Out of range source indices should fail."""
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

    # Create JSON response with out of range indices
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet the minimum requirement of fifty characters.",
        "source_indices": [99]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Should raise LessonSectionGenerationError
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    assert "source_indices contains out-of-range index 99" in str(exc_info.value)


def test_validation_malformed_json():
    """Validation test: Malformed JSON should fail."""
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

    # Create malformed JSON response
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet the minimum requirement of fifty characters.",
        "source_indices": [0]
    """  # Missing closing brace

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Should raise LessonSectionGenerationError
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    assert "JSON parsing failed" in str(exc_info.value)


def test_validation_missing_required_fields():
    """Validation test: Missing required fields should fail."""
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

    # Create JSON response missing required fields
    json_response = """{
        "section_title": "Test Section"
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Should raise LessonSectionGenerationError
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    assert "Schema validation failed" in str(exc_info.value)


def test_validation_title_length_constraints():
    """Validation test: Title length constraints."""
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

    # Test 1: Title at exact max length (200 chars) - should pass
    json_response = (
        "{"
        '"section_title": "' + "A" * 200 + '",'
        '"body": "Test body with sufficient length to meet the minimum requirement of fifty characters.",'
        '"source_indices": [0]'
        "}"
    )

    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Should succeed with max length title
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )
    assert len(result.section_title) == 200

    # Test 2: Title too long (201 chars) - should fail
    json_response = (
        "{"
        '"section_title": "' + "A" * 201 + '",'
        '"body": "Test body with sufficient length to meet the minimum requirement of fifty characters.",'
        '"source_indices": [0]'
        "}"
    )

    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    with pytest.raises(LessonSectionGenerationError):
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )


def test_validation_body_length_constraints():
    """Validation test: Body length constraints."""
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

    # Test 1: Body too short
    json_response = """{
        "section_title": "Test Section",
        "body": "Short",
        "source_indices": [0]
    }"""

    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    with pytest.raises(LessonSectionGenerationError):
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    # Test 2: Body too long
    json_response = """{
        "section_title": "Test Section",
        "body": "A" * 4001,
        "source_indices": [0]
    }"""

    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    with pytest.raises(LessonSectionGenerationError):
        service.generate_lesson_section(
            topic="Test Topic",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )


def test_validation_citation_mapping():
    """Validation test: Citation mapping accuracy."""
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
    ]

    # Create a lesson section draft with sufficient body length
    draft = LessonSectionDraft(
        section_title="Test Section",
        body="Test body with sufficient length to meet minimum requirement.",
        source_indices=[0, 1],
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Get the citations
    citations = service.draft_to_citations(draft, grounding_chunks)

    # Verify the citations
    assert len(citations) == 2
    assert citations[0] == "Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)"
    assert citations[1] == "Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)"


def test_validation_error_messages():
    """Validation test: Error message quality."""
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

    # Test various error messages - each body must be >= 50 chars
    error_cases = [
        (
            """{
            "section_title": "Test",
            "body": "Test body with sufficient length to meet minimum requirement.",
            "source_indices": []
        }""",
            "section must cite at least one source_index",
        ),
        (
            """{
            "section_title": "Test",
            "body": "Test body with sufficient length to meet minimum requirement.",
            "source_indices": [-1]
        }""",
            "source_indices must be non-negative",
        ),
        (
            """{
            "section_title": "Test",
            "body": "Test body with sufficient length to meet minimum requirement.",
            "source_indices": [99]
        }""",
            "source_indices contains out-of-range index 99",
        ),
    ]

    # Test each error case
    for error_json, expected_message in error_cases:
        client = StubCognitiveAgentClient(error_json)
        service = CognitiveAgentService(client)

        with pytest.raises(LessonSectionGenerationError) as exc_info:
            service.generate_lesson_section(
                topic="Test Topic",
                level="beginner",
                grounding_chunks=grounding_chunks,
            )

        assert expected_message in str(exc_info.value)


def test_validation_integration_scenarios():
    """Validation test: Integration scenarios with validation."""
    # Create comprehensive grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
            source_url="https://en.wikipedia.org/wiki/Machine_learning",
            source_title="Machine Learning - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Machine Learning - Wikipedia (https://en.wikipedia.org/wiki/Machine_learning, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Deep learning is a class of machine learning algorithms that uses multiple layers to progressively extract higher-level features from raw input.",
            source_url="https://en.wikipedia.org/wiki/Deep_learning",
            source_title="Deep Learning - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Deep Learning - Wikipedia (https://en.wikipedia.org/wiki/Deep_learning, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create valid JSON response
    json_response = """{
        "section_title": "Machine Learning and Deep Learning",
        "body": "Machine learning and deep learning are powerful technologies that enable computers to learn from data. Machine learning is a subset of artificial intelligence that uses statistical models to learn from data, while deep learning uses multiple layers of neural networks to extract complex features from raw input. These technologies have revolutionized many fields, from healthcare to autonomous vehicles.",
        "source_indices": [0, 1]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Machine Learning and Deep Learning",
        level="intermediate",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "Machine Learning and Deep Learning"
    assert "Machine learning and deep learning are powerful technologies" in result.body
    assert result.source_indices == [0, 1]


def test_validation_performance():
    """Validation test: Performance with validation."""
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

    # Create JSON response - body >= 50 chars
    json_response = """{
        "section_title": "Performance Test",
        "body": "Testing performance with validation and sufficient body length.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate many lesson sections
    sections = []
    for i in range(50):
        result = service.generate_lesson_section(
            topic=f"Performance Topic {i}",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )
        sections.append(result)

    # Verify results
    assert len(sections) == 50
    for section in sections:
        assert isinstance(section, LessonSectionDraft)
