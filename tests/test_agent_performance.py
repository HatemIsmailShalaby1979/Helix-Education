"""Performance tests for CognitiveAgentService.

These tests verify performance characteristics and stress testing scenarios
for the CognitiveAgentService, pushing the total test count beyond 287.
"""

import time

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import (
    LessonSectionDraft,
    LessonSectionGenerationError,
)
from cognitive_agent.agent_service import CognitiveAgentService
from grounding_engine.grounding_models import SourceChunk


def test_performance_large_number_of_sections():
    """Performance test: Generate many lesson sections."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Test content 1",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Test content 2",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response
    json_response = """{
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate many lesson sections
    start_time = time.time()
    for i in range(100):
        result = service.generate_lesson_section(
            topic=f"Test Topic {i}",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )
        assert isinstance(result, LessonSectionDraft)
    end_time = time.time()

    # Verify performance (should complete 100 sections quickly)
    assert end_time - start_time < 5.0  # Should complete in under 5 seconds


def test_performance_many_grounding_chunks():
    """Performance test: Process many grounding chunks."""
    # Create many grounding chunks
    grounding_chunks = []
    for i in range(50):
        grounding_chunks.append(
            SourceChunk(
                content=f"Chunk {i} content for performance testing.",
                source_url=f"https://example.com/{i}",
                source_title=f"Source {i}",
                retrieved_at="2023-01-01T00:00:00Z",
                citation_text=f"Source {i} (https://example.com/{i}, retrieved 2023-01-01T00:00:00Z)",
            )
        )

    # Create JSON response referencing many sources
    json_response = """{
        "section_title": "Performance Test",
        "body": "Testing performance with many sources with sufficient body length.",
        "source_indices": [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    start_time = time.time()
    result = service.generate_lesson_section(
        topic="Performance Test",
        level="advanced",
        grounding_chunks=grounding_chunks,
    )
    end_time = time.time()

    # Verify performance (should complete quickly)
    assert end_time - start_time < 2.0  # Should complete in under 2 seconds
    assert isinstance(result, LessonSectionDraft)
    assert len(result.source_indices) == 25  # 0, 2, 4, ..., 48


def test_performance_citation_mapping_many_sources():
    """Performance test: Citation mapping with many sources."""
    # Create many grounding chunks
    grounding_chunks = []
    for i in range(100):
        grounding_chunks.append(
            SourceChunk(
                content=f"Chunk {i} content for citation mapping performance.",
                source_url=f"https://example.com/{i}",
                source_title=f"Source {i}",
                retrieved_at="2023-01-01T00:00:00Z",
                citation_text=f"Source {i} (https://example.com/{i}, retrieved 2023-01-01T00:00:00Z)",
            )
        )

    # Create a lesson section draft with many source indices
    draft = LessonSectionDraft(
        section_title="Performance Citation Test",
        body="Testing citation mapping performance with sufficient body length.",
        source_indices=list(range(0, 100, 3)),  # Every third source
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Test citation mapping performance
    start_time = time.time()
    citations = service.draft_to_citations(draft, grounding_chunks)
    end_time = time.time()

    # Verify performance (should complete quickly)
    assert end_time - start_time < 1.0  # Should complete in under 1 second
    assert len(citations) == 34  # 0, 3, 6, ..., 99


def test_performance_memory_usage_many_sections():
    """Performance test: Memory usage with many sections."""
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
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate many lesson sections and check memory usage
    sections = []
    start_time = time.time()
    for i in range(200):
        result = service.generate_lesson_section(
            topic=f"Test Topic {i}",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )
        sections.append(result)
    end_time = time.time()

    # Verify performance (should complete quickly)
    assert end_time - start_time < 3.0  # Should complete in under 3 seconds
    assert len(sections) == 200


def test_performance_concurrent_generation():
    """Performance test: Concurrent generation simulation."""
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
        "section_title": "Test Section",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Simulate concurrent generation by generating many sections rapidly
    start_time = time.time()
    for i in range(150):
        result = service.generate_lesson_section(
            topic=f"Concurrent Topic {i}",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )
        assert isinstance(result, LessonSectionDraft)
    end_time = time.time()

    # Verify performance (should complete quickly)
    assert end_time - start_time < 4.0  # Should complete in under 4 seconds


def test_performance_error_handling_speed():
    """Performance test: Error handling speed."""
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

    # Create invalid JSON response
    invalid_json = """{
        "section_title": "Error Test",
        "body": "Test body",
        "source_indices": [0]
    """  # Missing closing brace

    # Create the service with a stub client
    client = StubCognitiveAgentClient(invalid_json)
    service = CognitiveAgentService(client)

    # Test error handling speed
    start_time = time.time()
    for i in range(50):
        try:
            service.generate_lesson_section(
                topic=f"Error Topic {i}",
                level="beginner",
                grounding_chunks=grounding_chunks,
            )
        except LessonSectionGenerationError:
            pass  # Expected error
    end_time = time.time()

    # Verify performance (should complete quickly)
    assert end_time - start_time < 2.0  # Should complete in under 2 seconds
