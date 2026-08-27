"""Tests for CognitiveAgentService trust boundary.

This is the MOST IMPORTANT TEST FILE IN THE DELIVERABLE. Using StubCognitiveAgentClient
with various canned_response strings, prove:
  1. Valid JSON matching schema → returns correct LessonSectionDraft.
  2. Malformed JSON (not parseable at all) → raises LessonSectionGenerationError,
     does not crash with an unhandled JSONDecodeError.
  3. Valid JSON but missing a required field → raises LessonSectionGenerationError
     (Pydantic validation failure), not a silent partial object.
  4. Valid JSON with source_indices: [] (empty list) → raises
     LessonSectionGenerationError.
  5. Valid JSON with source_indices: [99] where grounding_chunks only has
     3 items → raises LessonSectionGenerationError (out-of-range citation,
     the model claimed to cite a source that doesn't exist — this is the
     single most important test in this entire deliverable, since it's
     the exact hallucinated-citation scenario the whole grounding
     architecture exists to prevent).
  6. draft_to_citations() correctly maps indices to citation_text strings
     in order.
"""

import pytest

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import LessonSectionGenerationError
from cognitive_agent.agent_service import CognitiveAgentService
from grounding_engine.grounding_models import SourceChunk


def test_valid_json_matching_schema_returns_correct_draft():
    """Test that valid JSON matching schema returns correct LessonSectionDraft."""
    # Create a mock grounding chunk
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Second source chunk content",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a valid JSON response
    valid_json = """{
        "section_title": "Test Section",
        "body": "This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        "source_indices": [0, 1]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(valid_json)
    service = CognitiveAgentService(client)

    # Generate the lesson section
    result = service.generate_lesson_section(
        topic="Test Topic",
        level="intermediate",
        grounding_chunks=grounding_chunks,
    )

    # Verify the result
    assert result.section_title == "Test Section"
    assert (
        result.body == "This is a test body with sufficient length to meet the minimum requirement of fifty characters."
    )
    assert result.source_indices == [0, 1]


def test_malformed_json_raises_lesson_section_generation_error():
    """Test that malformed JSON raises LessonSectionGenerationError."""
    # Create a mock grounding chunk
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a malformed JSON response
    malformed_json = """{
        "section_title": "Test Section",
        "body": "This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        "source_indices": [0]
    """  # Missing closing brace

    # Create the service with a stub client
    client = StubCognitiveAgentClient(malformed_json)
    service = CognitiveAgentService(client)

    # Verify that LessonSectionGenerationError is raised
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )

    # Verify that the error message contains information about JSON parsing
    assert "JSON parsing failed" in str(exc_info.value)


def test_valid_json_missing_required_field_raises_lesson_section_generation_error():
    """Test that valid JSON but missing a required field raises LessonSectionGenerationError."""
    # Create a mock grounding chunk
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a JSON response missing the body field
    json_missing_field = """{
        "section_title": "Test Section",
        "source_indices": [0]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_missing_field)
    service = CognitiveAgentService(client)

    # Verify that LessonSectionGenerationError is raised
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )

    # Verify that the error message contains information about validation
    assert "Schema validation failed" in str(exc_info.value)


def test_valid_json_with_empty_source_indices_raises_lesson_section_generation_error():
    """Test that valid JSON with empty source_indices raises LessonSectionGenerationError."""
    # Create a mock grounding chunk
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a JSON response with empty source_indices
    json_empty_indices = """{
        "section_title": "Test Section",
        "body": "This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        "source_indices": []
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_empty_indices)
    service = CognitiveAgentService(client)

    # Verify that LessonSectionGenerationError is raised
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )

    # Verify that the error message contains information about empty source indices
    assert "section must cite at least one source_index" in str(exc_info.value)


def test_valid_json_with_out_of_range_source_indices_raises_lesson_section_generation_error():
    """Test that valid JSON with out-of-range source_indices raises LessonSectionGenerationError.

    This is the single most important test in this entire deliverable, since it's
    the exact hallucinated-citation scenario the whole grounding architecture exists to prevent.
    """
    # Create mock grounding chunks (only 3 chunks)
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Second source chunk content",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Third source chunk content",
            source_url="https://example.com/3",
            source_title="Source 3",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a JSON response with out-of-range source_indices (index 99 when only 3 chunks exist)
    json_out_of_range = """{
        "section_title": "Test Section",
        "body": "This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        "source_indices": [99]
    }"""

    # Create the service with a stub client
    client = StubCognitiveAgentClient(json_out_of_range)
    service = CognitiveAgentService(client)

    # Verify that LessonSectionGenerationError is raised
    with pytest.raises(LessonSectionGenerationError) as exc_info:
        service.generate_lesson_section(
            topic="Test Topic",
            level="intermediate",
            grounding_chunks=grounding_chunks,
        )

    # Verify that the error message contains information about out-of-range indices
    assert "source_indices contains out-of-range index 99" in str(exc_info.value)


def test_draft_to_citations_correctly_maps_indices_to_citation_texts():
    """Test that draft_to_citations correctly maps indices to citation_text strings."""
    # Create mock grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Second source chunk content",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Third source chunk content",
            source_url="https://example.com/3",
            source_title="Source 3",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a lesson section draft
    from cognitive_agent.agent_models import LessonSectionDraft

    draft = LessonSectionDraft(
        section_title="Test Section",
        body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        source_indices=[0, 2, 1],
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Get the citations
    citations = service.draft_to_citations(draft, grounding_chunks)

    # Verify the citations
    assert citations == [
        "Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        "Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)",
        "Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
    ]


def test_draft_to_citations_with_single_index():
    """Test that draft_to_citations works with a single index."""
    # Create mock grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a lesson section draft
    from cognitive_agent.agent_models import LessonSectionDraft

    draft = LessonSectionDraft(
        section_title="Test Section",
        body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        source_indices=[0],
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Get the citations
    citations = service.draft_to_citations(draft, grounding_chunks)

    # Verify the citations
    assert citations == ["Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)"]


def test_draft_to_citations_with_consecutive_indices():
    """Test that draft_to_citations works with consecutive indices."""
    # Create mock grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Second source chunk content",
            source_url="https://example.com/2",
            source_title="Source 2",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        ),
        SourceChunk(
            content="Third source chunk content",
            source_url="https://example.com/3",
            source_title="Source 3",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a lesson section draft
    from cognitive_agent.agent_models import LessonSectionDraft

    draft = LessonSectionDraft(
        section_title="Test Section",
        body="This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
        source_indices=[0, 1, 2],
    )

    # Create the service
    client = StubCognitiveAgentClient("")
    service = CognitiveAgentService(client)

    # Get the citations
    citations = service.draft_to_citations(draft, grounding_chunks)

    # Verify the citations
    assert citations == [
        "Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        "Source 2 (https://example.com/2, retrieved 2023-01-01T00:00:00Z)",
        "Source 3 (https://example.com/3, retrieved 2023-01-01T00:00:00Z)",
    ]


def test_prompt_includes_grounded_only_instruction():
    """Test that the prompt sent to the LLM contains the anti-elaboration
    instruction forbidding ungrounded factual claims (Fix 2)."""
    from cognitive_agent.agent_client import CognitiveAgentClient

    # Create mock grounding chunks
    grounding_chunks = [
        SourceChunk(
            content="First source chunk content",
            source_url="https://example.com/1",
            source_title="Source 1",
            retrieved_at="2023-01-01T00:00:00Z",
            citation_text="Source 1 (https://example.com/1, retrieved 2023-01-01T00:00:00Z)",
        ),
    ]

    # Create a mock client that captures the prompt passed to generate_raw
    captured_prompt = {}

    class CapturingClient(CognitiveAgentClient):
        def generate_raw(self, prompt: str) -> str:
            captured_prompt["prompt"] = prompt
            # Return valid JSON to avoid validation errors
            return """{
                "section_title": "Test Section",
                "body": "This is a test body with sufficient length to meet the minimum requirement of fifty characters.",
                "source_indices": [0]
            }"""

    client = CapturingClient()
    service = CognitiveAgentService(client)

    # Call generate_lesson_section
    service.generate_lesson_section(
        topic="Test Topic",
        level="intermediate",
        grounding_chunks=grounding_chunks,
    )

    # Verify the prompt contains the anti-elaboration instruction
    prompt = captured_prompt["prompt"]
    # Key phrases from the instruction that must be present
    assert (
        "Do not add any factual claim, example, or elaboration that is not directly supported by the provided source chunks"
        in prompt
    )
    assert "Every sentence in the body must either paraphrase content from a specific chunk" in prompt
    assert (
        "If the grounding chunks do not contain enough material to write a complete section, write a SHORTER section using only what is grounded"
        in prompt
    )
