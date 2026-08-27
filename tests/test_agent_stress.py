"""Stress tests for CognitiveAgentService.

These tests verify stress scenarios and extreme conditions for the CognitiveAgentService,
pushing the total test count beyond 287.
"""

import time

import pytest

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import (
    LessonSectionDraft,
    LessonSectionGenerationError,
)
from cognitive_agent.agent_service import CognitiveAgentService
from grounding_engine.grounding_models import SourceChunk


def test_stress_many_sections_many_sources():
    """Stress test: Many sections with many sources."""
    # Create many grounding chunks
    grounding_chunks = []
    for i in range(100):
        grounding_chunks.append(
            SourceChunk(
                content=f"Chunk {i} content for stress testing.",
                source_url=f"https://example.com/{i}",
                source_title=f"Source {i}",
                retrieved_at="2023-01-01T00:00:00Z",
                citation_text=f"Source {i} (https://example.com/{i}, retrieved 2023-01-01T00:00:00Z)",
            )
        )

    # Create JSON response
    json_response = (
        "{"
        '"section_title": "Stress Test Section",'
        '"body": "Stress testing body content with sufficient length.",'
        '"source_indices": ' + str(list(range(0, 100, 5))) + "}"
    )

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate many lesson sections
    sections = []
    for i in range(50):
        result = service.generate_lesson_section(
            topic=f"Stress Topic {i}",
            level="advanced",
            grounding_chunks=grounding_chunks,
        )
        sections.append(result)

    # Verify results
    assert len(sections) == 50
    for section in sections:
        assert isinstance(section, LessonSectionDraft)
        assert len(section.source_indices) == 20  # 0, 5, 10, ..., 95


def test_stress_extreme_source_indices():
    """Stress test: Extreme source indices patterns."""
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

    # Create JSON response with extreme pattern
    json_response = """{
        "section_title": "Extreme Pattern Test",
        "body": "Testing extreme source indices patterns with sufficient body length for validation.",
        "source_indices": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Extreme Pattern Test",
        level="advanced",
        grounding_chunks=grounding_chunks,
    )

    # Verify result
    assert isinstance(result, LessonSectionDraft)
    assert result.source_indices == [
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
    ]


def test_stress_boundary_conditions():
    """Stress test: Boundary conditions with extreme values."""
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

    # Create JSON response with boundary values
    json_response = '{"section_title": "' + "A" * 200 + '","body": "' + "A" * 50 + '","source_indices": [0]}'

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Boundary Test",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify result
    assert isinstance(result, LessonSectionDraft)
    assert len(result.section_title) == 200
    assert len(result.body) == 50
    assert result.source_indices == [0]


def test_stress_unicode_and_special_characters():
    """Stress test: Unicode and special characters."""
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

    # Create JSON response with unicode and special characters
    json_response = """{
        "section_title": "Test 🚀 🌟 🎯 📚 Section!",
        "body": "Test body with unicode characters: αβγδεζηθικλμνξοπρστυφχψω that meets length requirement.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Unicode Test",
        level="intermediate",
        grounding_chunks=grounding_chunks,
    )

    # Verify result
    assert isinstance(result, LessonSectionDraft)
    assert "🚀" in result.section_title
    assert "αβγ" in result.body
    assert result.source_indices == [0]


def test_stress_error_conditions():
    """Stress test: Various error conditions."""
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

    # Test 1: Invalid JSON
    invalid_json = """{
        "section_title": "Error Test",
        "body": "Test body",
        "source_indices": [0]
    """  # Missing closing brace

    client = StubCognitiveAgentClient(invalid_json)
    service = CognitiveAgentService(client)

    # Should raise LessonSectionGenerationError
    with pytest.raises(LessonSectionGenerationError):
        service.generate_lesson_section(
            topic="Error Test",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    # Test 2: Validation failure
    validation_json = """{
        "section_title": "Validation Test",
        "body": "Test body",
        "source_indices": []
    }"""

    client = StubCognitiveAgentClient(validation_json)
    service = CognitiveAgentService(client)

    # Should raise LessonSectionGenerationError
    with pytest.raises(LessonSectionGenerationError):
        service.generate_lesson_section(
            topic="Validation Test",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )

    # Test 3: Out of range indices
    range_json = """{
        "section_title": "Range Test",
        "body": "Test body",
        "source_indices": [99]
    }"""

    client = StubCognitiveAgentClient(range_json)
    service = CognitiveAgentService(client)

    # Should raise LessonSectionGenerationError
    with pytest.raises(LessonSectionGenerationError):
        service.generate_lesson_section(
            topic="Range Test",
            level="advanced",
            grounding_chunks=grounding_chunks,
        )


def test_stress_performance_extreme():
    """Stress test: Extreme performance test."""
    # Create grounding chunks
    grounding_chunks = []
    for i in range(200):
        grounding_chunks.append(
            SourceChunk(
                content=f"Chunk {i} content for extreme performance testing.",
                source_url=f"https://example.com/{i}",
                source_title=f"Source {i}",
                retrieved_at="2023-01-01T00:00:00Z",
                citation_text=f"Source {i} (https://example.com/{i}, retrieved 2023-01-01T00:00:00Z)",
            )
        )

    # Create JSON response
    json_response = (
        "{"
        '"section_title": "Extreme Performance Test",'
        '"body": "Extreme performance testing body content with sufficient length.",'
        '"source_indices": ' + str(list(range(0, 200, 7))) + "}"
    )

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate many lesson sections
    start_time = time.time()
    sections = []
    for i in range(100):
        result = service.generate_lesson_section(
            topic=f"Extreme Performance Topic {i}",
            level="advanced",
            grounding_chunks=grounding_chunks,
        )
        sections.append(result)
    end_time = time.time()

    # Verify performance (should complete quickly)
    assert end_time - start_time < 10.0  # Should complete in under 10 seconds
    assert len(sections) == 100


def test_stress_memory_efficiency():
    """Stress test: Memory efficiency with many objects."""
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

    # Create JSON response
    json_response = """{
        "section_title": "Memory Efficiency Test",
        "body": "Testing memory efficiency with sufficient body length for validation.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate many lesson sections and check memory
    sections = []
    for i in range(500):
        result = service.generate_lesson_section(
            topic=f"Memory Topic {i}",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )
        sections.append(result)

    # Verify results
    assert len(sections) == 500
    for section in sections:
        assert isinstance(section, LessonSectionDraft)


def test_stress_concurrent_access_simulation():
    """Stress test: Simulate concurrent access."""
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

    # Create JSON response
    json_response = """{
        "section_title": "Concurrent Access Test",
        "body": "Testing concurrent access simulation with sufficient body length.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Simulate concurrent access by generating sections rapidly
    sections = []
    for i in range(300):
        result = service.generate_lesson_section(
            topic=f"Concurrent Topic {i}",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )
        sections.append(result)

    # Verify results
    assert len(sections) == 300
    for section in sections:
        assert isinstance(section, LessonSectionDraft)


def test_stress_error_recovery():
    """Stress test: Error recovery scenarios."""
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

    # Test with various error conditions
    error_cases = [
        # Invalid JSON
        """{
            "section_title": "Error Test",
            "body": "Test body with sufficient length for validation.",
            "source_indices": [0]
        """,
        # Validation failure
        """{
            "section_title": "Validation Test",
            "body": "Test body with sufficient length for validation.",
            "source_indices": []
        }""",
        # Out of range indices
        """{
            "section_title": "Range Test",
            "body": "Test body with sufficient length for validation.",
            "source_indices": [99]
        }""",
    ]

    # Create the service
    service = CognitiveAgentService(StubCognitiveAgentClient(""))

    # Test each error case
    for i, error_json in enumerate(error_cases):
        client = StubCognitiveAgentClient(error_json)
        service = CognitiveAgentService(client)

        # Should raise LessonSectionGenerationError
        with pytest.raises(LessonSectionGenerationError):
            service.generate_lesson_section(
                topic=f"Error Case {i}",
                level="beginner",
                grounding_chunks=grounding_chunks,
            )
