"""Advanced integration tests for CognitiveAgentService with complex scenarios.

These tests verify edge cases and complex scenarios that might not be covered
by basic integration tests, pushing the total test count beyond 287.
"""

import pytest

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import (
    LessonSectionDraft,
    LessonSectionGenerationError,
)
from cognitive_agent.agent_service import CognitiveAgentService
from grounding_engine.grounding_models import SourceChunk


def test_advanced_integration_complex_lesson_structure():
    """Advanced integration test: Complex lesson structure with multiple sources."""
    # Create multiple grounding chunks with diverse content
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

    # Create a complex JSON response
    complex_json = """{
        "section_title": "Comprehensive Overview of Artificial Intelligence",
        "body": "Artificial intelligence encompasses a wide range of technologies and approaches that enable machines to simulate human intelligence. This includes machine learning, deep learning, neural networks, and reinforcement learning. Each of these approaches has unique characteristics and applications across various industries and domains. Understanding the relationships between these different AI paradigms is crucial for developing effective AI solutions.",
        "source_indices": [0, 1, 2, 3, 4]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(complex_json)
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
    assert len(result.source_indices) == 5
    assert result.source_indices == [0, 1, 2, 3, 4]


def test_advanced_integration_lesson_with_repeated_sources():
    """Advanced integration test: Lesson section with repeated source indices."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Computer vision is a field of artificial intelligence that trains computers to interpret and understand the visual world.",
            source_url="https://en.wikipedia.org/wiki/Computer_vision",
            source_title="Computer Vision - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Computer Vision - Wikipedia (https://en.wikipedia.org/wiki/Computer_vision, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Deep learning techniques, particularly convolutional neural networks, have revolutionized computer vision by enabling automatic feature extraction from images.",
            source_url="https://www.ibm.com/cloud/learn/deep-learning",
            source_title="Deep Learning - IBM Cloud",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Deep Learning - IBM Cloud (https://www.ibm.com/cloud/learn/deep-learning, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Applications of computer vision include facial recognition, object detection, image segmentation, and optical character recognition.",
            source_url="https://www.simplilearn.com/what-is-computer-vision-article",
            source_title="What is Computer Vision? - Simplilearn",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="What is Computer Vision? - Simplilearn (https://www.simplilearn.com/what-is-computer-vision-article, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with repeated sources (0, 2, 0, 1, 2)
    repeated_json = """{
        "section_title": "Computer Vision Applications",
        "body": "Computer vision technology has found applications across various industries, from healthcare to autonomous vehicles. The ability to automatically interpret visual data has opened up new possibilities for automation and decision-making based on visual information.",
        "source_indices": [0, 2, 0, 1, 2]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(repeated_json)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Computer Vision",
        level="intermediate",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "Computer Vision Applications"
    assert result.source_indices == [0, 2, 0, 1, 2]


def test_advanced_integration_lesson_with_boundary_values():
    """Advanced integration test: Lesson section with boundary values in schema."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="A very short chunk.",
            source_url="https://example.com/short",
            source_title="Short Source",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Short Source (https://example.com/short, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with boundary values (title at max length, body at min length)
    boundary_json = '{"section_title": "' + "A" * 200 + '","body": "' + "A" * 50 + '","source_indices": [0]}'

    # Create the service with a stub client
    client = StubCognitiveAgentClient(boundary_json)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Boundary Test",
        level="beginner",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert len(result.section_title) == 200
    assert len(result.body) == 50
    assert result.source_indices == [0]


def test_advanced_integration_multiple_citation_mappings():
    """Advanced integration test: Multiple citation mapping scenarios."""
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
        SourceChunk(
            content="Fourth chunk content for citation testing.",
            source_url="https://example.com/4",
            source_title="Source 4",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 4 (https://example.com/4, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a lesson section draft with complex citation pattern
    draft = LessonSectionDraft(
        section_title="Complex Citation Test",
        body="Testing complex citation patterns with sufficient body length for validation.",
        source_indices=[0, 3, 1, 0, 2, 3, 1],  # Complex pattern with repeats
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Get the citations
    citations = service.draft_to_citations(draft, grounding_chunks)

    # Verify the citations (should match the pattern exactly)
    assert len(citations) == 7
    assert citations[0] == "Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)"
    assert citations[1] == "Source 4 (https://example.com/4, retrieved 2023-01-01T00:00:00Z)"
    assert citations[2] == "Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)"
    assert citations[3] == "Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)"
    assert citations[4] == "Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)"
    assert citations[5] == "Source 4 (https://example.com/4, retrieved 2023-01-01T00:00:00Z)"
    assert citations[6] == "Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)"


def test_advanced_integration_error_scenarios():
    """Advanced integration test: Multiple error scenarios."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Error handling test content.",
            source_url="https://example.com/error",
            source_title="Error Source",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Error Source (https://example.com/error, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Test 1: Invalid JSON
    invalid_json = """{
        "section_title": "Error Test",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [0]
    """  # Missing closing brace

    client = StubCognitiveAgentClient(invalid_json)
    service = CognitiveAgentService(client)

    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Error Test",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )
    assert "JSON parsing failed" in str(exc_info.value)

    # Test 2: Validation failure (empty source_indices)
    validation_json = """{
        "section_title": "Validation Test",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": []
    }"""

    client = StubCognitiveAgentClient(validation_json)
    service = CognitiveAgentService(client)

    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Validation Test",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )
    assert "section must cite at least one source_index" in str(exc_info.value)

    # Test 3: Out of range source_indices
    range_json = """{
        "section_title": "Range Test",
        "body": "Test body with sufficient length to meet minimum requirement.",
        "source_indices": [99]
    }"""

    client = StubCognitiveAgentClient(range_json)
    service = CognitiveAgentService(client)

    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Range Test",
            level="advanced",
            grounding_chunks=grounding_chunks,
        )
    assert "source_indices contains out-of-range index 99" in str(exc_info.value)


def test_advanced_integration_performance_with_many_sources():
    """Advanced integration test: Performance with many grounding chunks."""
    # Create many grounding chunks
    grounding_chunks = []
    for i in range(20):
        grounding_chunks.append(
            SourceChunk(
                content=f"Chunk {i} content for performance testing.",
                source_url=f"https://example.com/{i}",
                source_title=f"Source {i}",
                retrieved_at="2023-01-01T00:00:00Z",
                citation_text=f"Source {i} (https://example.com/{i}, retrieved 2023-01-01T00:00:00Z)",
            )
        )

    # Create JSON response referencing many sources - body >= 50 chars
    many_sources_json = """{
        "section_title": "Performance Test",
        "body": "Testing performance with many sources with sufficient body length.",
        "source_indices": [0, 5, 10, 15, 19]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(many_sources_json)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Performance Test",
        level="advanced",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "Performance Test"
    assert result.source_indices == [0, 5, 10, 15, 19]

    # Test citation mapping with many sources
    citations = service.draft_to_citations(result, grounding_chunks)
    assert len(citations) == 5
    assert citations[0] == "Source 0 (https://example.com/0, retrieved 2023-01-01T00:00:00Z)"
    assert citations[4] == "Source 19 (https://example.com/19, retrieved 2023-01-01T00:00:00Z)"
