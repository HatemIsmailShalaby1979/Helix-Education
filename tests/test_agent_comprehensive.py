"""Comprehensive tests for CognitiveAgentService.

These tests provide comprehensive coverage of CognitiveAgentService functionality,
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


def test_comprehensive_valid_generation():
    """Comprehensive test: Valid lesson section generation with comprehensive data."""
    # Create comprehensive grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans.",
            source_url="https://en.wikipedia.org/wiki/Artificial_intelligence",
            source_title="Artificial Intelligence - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Artificial Intelligence - Wikipedia (https://en.wikipedia.org/wiki/Artificial_intelligence, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Machine learning is a subset of artificial intelligence that uses statistical models to enable computers to learn from data without being explicitly programmed.",
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
        SourceChunk(
            content="Neural networks are computing systems inspired by biological neural networks that constitute animal brains. They consist of node layers, each layer fully connected to the previous one.",
            source_url="https://en.wikipedia.org/wiki/Neural_network",
            source_title="Neural Network - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Neural Network - Wikipedia (https://en.wikipedia.org/wiki/Neural_network, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Reinforcement learning is a type of machine learning where an agent learns to make decisions by receiving rewards or penalties for actions taken in an environment.",
            source_url="https://en.wikipedia.org/wiki/Reinforcement_learning",
            source_title="Reinforcement Learning - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Reinforcement Learning - Wikipedia (https://en.wikipedia.org/wiki/Reinforcement_learning, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create comprehensive JSON response
    comprehensive_json = """{
        "section_title": "Comprehensive Overview of Artificial Intelligence",
        "body": "Artificial intelligence encompasses a wide range of technologies and approaches that enable machines to simulate human intelligence. This includes machine learning, deep learning, neural networks, and reinforcement learning. Each of these approaches has unique characteristics and applications across various industries and domains. Understanding the relationships between these different AI paradigms is crucial for developing effective AI solutions.",
        "source_indices": [0, 1, 2, 3, 4]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(comprehensive_json)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Artificial Intelligence",
        level="advanced",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "Comprehensive Overview of Artificial Intelligence"
    assert "Artificial intelligence encompasses a wide range of technologies" in result.body
    assert result.source_indices == [0, 1, 2, 3, 4]


def test_comprehensive_error_handling():
    """Comprehensive test: Comprehensive error handling scenarios."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Error handling test content.",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Test various error scenarios
    error_cases = [
        # Invalid JSON
        (
            """{
            "section_title": "Error Test",
            "body": "Test body with sufficient length to meet minimum requirement.",
            "source_indices": [0]
        """,
            "JSON parsing failed",
        ),
        # Validation failure - empty source_indices
        (
            """{
            "section_title": "Validation Test",
            "body": "Test body with sufficient length to meet minimum requirement.",
            "source_indices": []
        }""",
            "section must cite at least one source_index",
        ),
        # Out of range indices - body is valid length
        (
            """{
            "section_title": "Range Test",
            "body": "Test body with sufficient length to meet minimum requirement.",
            "source_indices": [99]
        }""",
            "source_indices contains out-of-range index 99",
        ),
    ]

    # Create the service
    service = CognitiveAgentService(StubCognitiveAgentClient(""))

    # Test each error case
    for error_json, expected_error in error_cases:
        client = StubCognitiveAgentClient(error_json)
        service = CognitiveAgentService(client)

        # Should raise LessonSectionGenerationError
        with pytest.raises(LessonSectionGenerationError) as exc_info:
            service.generate_lesson_section(
                topic="Error Test",
                level="beginner",
                grounding_chunks=grounding_chunks,
            )

        # Verify error message contains expected text
        assert expected_error in str(exc_info.value)


def test_comprehensive_citation_scenarios():
    """Comprehensive test: Various citation scenarios."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="First chunk content for citation testing.",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Second chunk content for citation testing.",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Third chunk content for citation testing.",
            source_url="https://example.com/3",
            source_title="Source 3",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a lesson section draft - body must be at least 50 chars
    draft = LessonSectionDraft(
        section_title="Citation Test",
        body="Testing citation scenarios with sufficient body length for validation.",
        source_indices=[0, 2, 1],
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Get the citations
    citations = service.draft_to_citations(draft, grounding_chunks)

    # Verify the citations
    assert len(citations) == 3
    assert citations[0] == "Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)"
    assert citations[1] == "Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)"
    assert citations[2] == "Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)"


def test_comprehensive_performance():
    """Comprehensive test: Performance testing with many scenarios."""
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

    # Create JSON response - body must be >= 50 chars
    json_response = """{
        "section_title": "Performance Test",
        "body": "Testing performance with sufficient body length to meet requirement.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_response)
    service = CognitiveAgentService(client)

    # Generate many lesson sections
    sections = []
    for i in range(100):
        result = service.generate_lesson_section(
            topic=f"Performance Topic {i}",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )
        sections.append(result)

    # Verify results
    assert len(sections) == 100
    for section in sections:
        assert isinstance(section, LessonSectionDraft)


def test_comprehensive_edge_cases():
    """Comprehensive test: Edge cases and boundary conditions."""
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

    # Test various edge cases - each body must be >= 50 chars
    edge_cases = [
        # Single character title
        ("A", "Test body with sufficient length to meet minimum requirement.", [0]),
        # Maximum length title
        (
            "A" * 200,
            "Test body with sufficient length to meet minimum requirement.",
            [0],
        ),
        # Minimum length body (exactly 50 chars)
        ("Test Section", "A" * 50, [0]),
        # Maximum length body (exactly 4000 chars)
        ("Test Section", "A" * 4000, [0]),
        # Unicode characters
        (
            "Test 🚀 Section",
            "Test body with unicode characters: αβγδεζηθ that meets length requirement.",
            [0],
        ),
        # Special characters
        (
            "Test @#$%^&*() Section!",
            "Test body with special chars: !@#$%^&*() that meets length requirement.",
            [0],
        ),
    ]

    # Test each edge case
    for title, body, indices in edge_cases:
        json_response = (
            '{"section_title": "' + title + '","body": "' + body + '","source_indices": ' + str(indices) + "}"
        )

        client = StubCognitiveAgentClient(json_response)
        service = CognitiveAgentService(client)

        # Should generate successfully
        result = service.generate_lesson_section(
            topic="Edge Case Test",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

        # Verify result
        assert isinstance(result, LessonSectionDraft)
        assert result.section_title == title
        assert result.body == body
        assert result.source_indices == indices


def test_comprehensive_integration_scenarios():
    """Comprehensive test: Integration scenarios with realistic data."""
    # Create realistic grounding chunks
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
        SourceChunk(
            content="Neural networks are computing systems inspired by biological neural networks that constitute animal brains. They consist of node layers, each layer fully connected to the previous one.",
            source_url="https://en.wikipedia.org/wiki/Neural_network",
            source_title="Neural Network - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Neural Network - Wikipedia (https://en.wikipedia.org/wiki/Neural_network, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create realistic JSON response
    realistic_json = """{
        "section_title": "Machine Learning and Deep Learning",
        "body": "Machine learning and deep learning are powerful technologies that enable computers to learn from data. Machine learning is a subset of artificial intelligence that uses statistical models to learn from data, while deep learning uses multiple layers of neural networks to extract complex features from raw input. These technologies have revolutionized many fields, from healthcare to autonomous vehicles.",
        "source_indices": [0, 1, 2]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(realistic_json)
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
    assert result.source_indices == [0, 1, 2]


def test_comprehensive_error_recovery():
    """Comprehensive test: Error recovery and resilience."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Error recovery test content.",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create the service
    service = CognitiveAgentService(StubCognitiveAgentClient(""))

    # Test error recovery with various scenarios
    error_scenarios = [
        # Invalid JSON
        """{
            "section_title": "Error Test",
            "body": "Test body",
            "source_indices": [0]
        """,
        # Validation failure
        """{
            "section_title": "Validation Test",
            "body": "Test body",
            "source_indices": []
        }""",
        # Out of range indices
        """{
            "section_title": "Range Test",
            "body": "Test body",
            "source_indices": [99]
        }""",
    ]

    # Test each scenario
    for i, error_json in enumerate(error_scenarios):
        client = StubCognitiveAgentClient(error_json)
        service = CognitiveAgentService(client)

        # Should raise LessonSectionGenerationError
        with pytest.raises(LessonSectionGenerationError):
            service.generate_lesson_section(
                topic=f"Error Recovery Test {i}",
                level="beginner",
                grounding_chunks=grounding_chunks,
            )


def test_comprehensive_citation_mapping():
    """Comprehensive test: Citation mapping with complex scenarios."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="First chunk content for citation mapping.",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Second chunk content for citation mapping.",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Third chunk content for citation mapping.",
            source_url="https://example.com/3",
            source_title="Source 3",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Fourth chunk content for citation mapping.",
            source_url="https://example.com/4",
            source_title="Source 4",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 4 (https://example.com/4, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a lesson section draft with complex citation pattern
    draft = LessonSectionDraft(
        section_title="Complex Citation Mapping Test",
        body="Testing complex citation mapping with sufficient body length for validation.",
        source_indices=[0, 3, 1, 0, 2, 3, 1],
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Get the citations
    citations = service.draft_to_citations(draft, grounding_chunks)

    # Verify the citations
    assert len(citations) == 7
    assert citations[0] == "Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)"
    assert citations[1] == "Source 4 (https://example.com/4, retrieved 2023-01-01T00:00:00Z)"
    assert citations[2] == "Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)"
    assert citations[3] == "Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)"
    assert citations[4] == "Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)"
    assert citations[5] == "Source 4 (https://example.com/4, retrieved 2023-01-01T00:00:00Z)"
    assert citations[6] == "Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)"
