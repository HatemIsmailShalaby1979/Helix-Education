"""Integration tests for CognitiveAgentService with real-world scenarios.

These tests verify that the CognitiveAgentService works correctly in
integration scenarios, testing the complete flow from LLM generation
to validated lesson sections.
"""

import pytest

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import (
    LessonSectionDraft,
    LessonSectionGenerationError,
)
from cognitive_agent.agent_service import CognitiveAgentService
from grounding_engine.grounding_models import SourceChunk


def test_integration_valid_lesson_section_generation():
    """Integration test: Valid lesson section generation with realistic data."""
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
            content="Common machine learning algorithms include linear regression, decision trees, random forests, support vector machines, and neural networks.",
            source_url="https://www.geeksforgeeks.org/machine-learning-algorithms/",
            source_title="Machine Learning Algorithms - GeeksforGeeks",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Machine Learning Algorithms - GeeksforGeeks (https://www.geeksforgeeks.org/machine-learning-algorithms/, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="The field of machine learning has applications in various domains including healthcare, finance, marketing, and autonomous vehicles.",
            source_url="https://www.ibm.com/cloud/learn/machine-learning",
            source_title="Machine Learning - IBM Cloud",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Machine Learning - IBM Cloud (https://www.ibm.com/cloud/learn/machine-learning, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a realistic JSON response
    realistic_json = """{
        "section_title": "Introduction to Machine Learning",
        "body": "Machine learning is a powerful tool that enables computers to learn from data and make predictions. It encompasses various algorithms such as linear regression, decision trees, and neural networks. These algorithms help solve complex problems in areas like healthcare, finance, and autonomous vehicles. Understanding the fundamentals of machine learning is essential for anyone interested in data science and artificial intelligence.",
        "source_indices": [0, 1, 2]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(realistic_json)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Machine Learning",
        level="intermediate",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "Introduction to Machine Learning"
    assert "Machine learning is a powerful tool" in result.body
    assert result.source_indices == [0, 1, 2]


def test_integration_lesson_section_with_single_source():
    """Integration test: Lesson section generation with single source citation."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Deep learning is a subset of machine learning that uses neural networks with multiple layers to progressively extract higher-level features from raw input.",
            source_url="https://en.wikipedia.org/wiki/Deep_learning",
            source_title="Deep Learning - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Deep Learning - Wikipedia (https://en.wikipedia.org/wiki/Deep_learning, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with single source
    single_source_json = """{
        "section_title": "Deep Learning Overview",
        "body": "Deep learning has revolutionized many fields by enabling computers to learn complex patterns from large datasets. It powers applications like image recognition, natural language processing, and speech synthesis. The architecture typically consists of multiple hidden layers that automatically learn hierarchical representations of the input data.",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(single_source_json)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Deep Learning",
        level="advanced",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "Deep Learning Overview"
    assert result.source_indices == [0]


def test_integration_lesson_section_with_consecutive_sources():
    """Integration test: Lesson section generation with consecutive source indices."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Natural language processing (NLP) is a subfield of linguistics, computer science, and artificial intelligence concerned with the interactions between computers and human language.",
            source_url="https://en.wikipedia.org/wiki/Natural_language_processing",
            source_title="Natural Language Processing - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Natural Language Processing - Wikipedia (https://en.wikipedia.org/wiki/Natural_language_processing, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Common NLP tasks include text classification, named entity recognition, sentiment analysis, and machine translation.",
            source_url="https://www.ibm.com/cloud/learn/natural-language-processing",
            source_title="Natural Language Processing - IBM Cloud",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Natural Language Processing - IBM Cloud (https://www.ibm.com/cloud/learn/natural-language-processing, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Modern NLP models leverage transformer architectures and large language models to achieve state-of-the-art performance on various language understanding and generation tasks.",
            source_url="https://arxiv.org/abs/1706.03762",
            source_title="Attention Is All You Need - arXiv",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Attention Is All You Need - arXiv (https://arxiv.org/abs/1706.03762, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with consecutive sources
    consecutive_json = """{
        "section_title": "Natural Language Processing Fundamentals",
        "body": "Natural language processing enables computers to understand and generate human language. It encompasses a wide range of tasks from simple text classification to complex language generation. Modern NLP systems leverage advanced machine learning techniques, particularly transformer-based models that have achieved remarkable performance across various language understanding and generation benchmarks.",
        "source_indices": [0, 1, 2]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(consecutive_json)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Natural Language Processing",
        level="intermediate",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert isinstance(result, LessonSectionDraft)
    assert result.section_title == "Natural Language Processing Fundamentals"
    assert result.source_indices == [0, 1, 2]


def test_integration_citation_mapping_accuracy():
    """Integration test: Verify citation mapping accuracy with complex scenarios."""
    # Create grounding chunks with different content
    grounding_chunks = [
        SourceChunk(
            content="Computer vision is a field of artificial intelligence that enables computers to interpret, process, and understand visual information from the real world.",
            source_url="https://en.wikipedia.org/wiki/Computer_vision",
            source_title="Computer Vision - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Computer Vision - Wikipedia (https://en.wikipedia.org/wiki/Computer_vision, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Deep learning techniques, particularly convolutional neural networks, have significantly advanced computer vision capabilities, enabling applications like facial recognition and object detection.",
            source_url="https://www.ibm.com/cloud/learn/deep-learning",
            source_title="Deep Learning - IBM Cloud",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Deep Learning - IBM Cloud (https://www.ibm.com/cloud/learn/deep-learning, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Computer vision systems are used in various industries including healthcare for medical image analysis, automotive for autonomous driving, and retail for customer behavior analysis.",
            source_url="https://techcrunch.com/2023/01/15/computer-vision-applications/",
            source_title="Computer Vision Applications - TechCrunch",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Computer Vision Applications - TechCrunch (https://techcrunch.com/2023/01/15/computer-vision-applications/, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a lesson section draft
    draft = LessonSectionDraft(
        section_title="Computer Vision Applications",
        body="Computer vision technology has transformed numerous industries by enabling automated visual analysis and interpretation.",
        source_indices=[0, 2],  # Skip index 1 to test non-consecutive mapping
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Get the citations
    citations = service.draft_to_citations(draft, grounding_chunks)

    # Verify the citations (should be indices 0 and 2, skipping 1)
    assert len(citations) == 2
    assert (
        citations[0]
        == "Computer Vision - Wikipedia (https://en.wikipedia.org/wiki/Computer_vision, retrieved 2023-01-01T00:00:00Z)"
    )
    assert (
        citations[1]
        == "Computer Vision Applications - TechCrunch (https://techcrunch.com/2023/01/15/computer-vision-applications/, retrieved 2023-01-01T00:00:00Z)"
    )


def test_integration_error_handling_with_invalid_json():
    """Integration test: Error handling with invalid JSON responses."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Error handling is a critical aspect of software development that ensures applications can gracefully manage unexpected situations.",
            source_url="https://en.wikipedia.org/wiki/Error_handling",
            source_title="Error Handling - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Error Handling - Wikipedia (https://en.wikipedia.org/wiki/Error_handling, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create invalid JSON response
    invalid_json = """{
        "section_title": "Error Handling",
        "body": "Error handling is important",
        "source_indices": [0]
    """  # Missing closing brace

    # Create the service with a stub client
    client = StubCognitiveAgentClient(invalid_json)
    service = CognitiveAgentService(client)

    # Verify that LessonSectionGenerationError is raised
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Error Handling",
            level="beginner",
            grounding_chunks=grounding_chunks,
        )

    # Verify that the error message contains information about JSON parsing
    assert "JSON parsing failed" in str(exc_info.value)


def test_integration_error_handling_with_validation_failure():
    """Integration test: Error handling with schema validation failure."""
    # Create grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="Validation is the process of checking data for correctness and compliance with specified requirements.",
            source_url="https://en.wikipedia.org/wiki/Validation_(software)",
            source_title="Validation (software) - Wikipedia",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Validation (software) - Wikipedia (https://en.wikipedia.org/wiki/Validation_(software), retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create JSON response with validation failure (empty source_indices)
    validation_failure_json = """{
        "section_title": "Validation",
        "body": "Validation is important",
        "source_indices": []
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(validation_failure_json)
    service = CognitiveAgentService(client)

    # Verify that LessonSectionGenerationError is raised
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Validation",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )

    # Verify that the error message contains information about validation
    assert "section must cite at least one source_index" in str(exc_info.value)
