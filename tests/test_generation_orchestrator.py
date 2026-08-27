"""Tests for GenerationOrchestrator.

All tests use StubGroundingClient and StubCognitiveAgentClient — zero
live network calls, zero real LLM calls.
"""

from unittest import mock

import pytest

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import LessonSectionGenerationError
from cognitive_agent.agent_service import CognitiveAgentService
from content_engine import ContentService
from content_engine.generation_orchestrator import (
    GenerationOrchestrator,
    NoGroundingAvailableError,
)
from grounding_engine import GroundingService
from grounding_engine.grounding_client import StubGroundingClient
from grounding_engine.grounding_models import (
    GroundingFetchError,
    GroundingResult,
    SourceChunk,
)
from learning_service import LearningService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig


def _make_grounding_result(topic: str, num_chunks: int = 2) -> GroundingResult:
    """Create a GroundingResult with the given number of chunks."""
    chunks = [
        SourceChunk(
            content=f"Chunk {i} content for {topic}.",
            source_url=f"https://example.com/{topic}/{i}",
            source_title=f"{topic.title()} Source {i}",
            retrieved_at="2025-01-15T10:00:00+00:00",
            citation_text=f"{topic.title()} Source {i} (https://example.com/{topic}/{i}, retrieved 2025-01-15)",
        )
        for i in range(num_chunks)
    ]
    return GroundingResult(
        topic=topic,
        query_used=topic,
        chunks=chunks,
    )


def _make_valid_agent_response(
    section_title: str,
    body: str,
    source_indices: list[int],
) -> str:
    """Create a valid JSON response matching LessonSectionDraft schema."""
    import json

    return json.dumps(
        {
            "section_title": section_title,
            "body": body,
            "source_indices": source_indices,
        }
    )


class TestGenerationOrchestratorHappyPath:
    """Test 1: Happy path - everything succeeds."""

    def test_generate_and_commit_section_happy_path(self, tmp_path) -> None:
        """Grounding succeeds, agent returns valid JSON, section committed with citations."""
        topic = "algebra"
        level = "beginner"
        section_id = "sec_001"

        # Setup: grounding returns 2 chunks
        grounding_result = _make_grounding_result(topic, num_chunks=2)

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={topic: grounding_result})
        grounding_service = GroundingService(grounding_client)

        # Setup: agent returns valid JSON citing both chunks
        agent_response = _make_valid_agent_response(
            section_title="Introduction to Algebra",
            body="Algebra is the study of mathematical symbols and the rules for manipulating them. It forms the foundation for advanced mathematics.",
            source_indices=[0, 1],
        )
        agent_client = StubCognitiveAgentClient(canned_response=agent_response)
        agent_service = CognitiveAgentService(agent_client)

        content_service = ContentService(ls)

        orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        # Execute
        section = orchestrator.generate_and_commit_section(
            topic=topic,
            level=level,
            section_id=section_id,
            max_chunks=5,
        )

        # Verify: section returned with correct data
        assert section.section_id == section_id
        assert section.title == "Introduction to Algebra"
        assert "Algebra is the study of mathematical symbols" in section.body
        assert len(section.source_citations) == 2
        assert section.source_citations[0] == "Algebra Source 0 (https://example.com/algebra/0, retrieved 2025-01-15)"
        assert section.source_citations[1] == "Algebra Source 1 (https://example.com/algebra/1, retrieved 2025-01-15)"

        # Verify: lesson has the section
        lesson = orchestrator.content_service.get_lesson(topic)
        assert lesson is not None
        assert len(lesson.sections) == 1
        assert lesson.sections[0].section_id == section_id


class TestGenerationOrchestratorGroundingFetchError:
    """Test 2: GroundingFetchError propagates uncaught, content_service never called."""

    def test_grounding_fetch_error_propagates(self, tmp_path) -> None:
        """GroundingFetchError from grounding step propagates; content_service never called."""
        topic = "unknown_topic"
        level = "beginner"
        section_id = "sec_001"

        # Grounding client raises GroundingFetchError
        def failing_fetch(*args, **kwargs):
            raise GroundingFetchError("Simulated API timeout")

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={})
        grounding_client.fetch = failing_fetch
        grounding_service = GroundingService(grounding_client)

        agent_client = StubCognitiveAgentClient(canned_response="{}")
        agent_service = CognitiveAgentService(agent_client)

        content_service = ContentService(ls)

        orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        # Spy on content_service.commit_section
        with mock.patch.object(
            orchestrator.content_service,
            "commit_section",
            wraps=orchestrator.content_service.commit_section,
        ) as spy_commit:
            with pytest.raises(GroundingFetchError) as exc_info:
                orchestrator.generate_and_commit_section(
                    topic=topic,
                    level=level,
                    section_id=section_id,
                )

            # Verify the exact exception type
            assert isinstance(exc_info.value, GroundingFetchError)
            assert "Simulated API timeout" in str(exc_info.value)

            # Verify content_service.commit_section was NEVER called
            spy_commit.assert_not_called()


class TestGenerationOrchestratorNoGroundingAvailable:
    """Test 3: Empty GroundingResult.chunks raises NoGroundingAvailableError."""

    def test_empty_grounding_raises_no_grounding_available(self, tmp_path) -> None:
        """GroundingResult with zero chunks raises NoGroundingAvailableError with topic."""
        topic = "empty_topic"
        level = "beginner"
        section_id = "sec_001"

        # Grounding returns result with zero chunks
        empty_result = GroundingResult(
            topic=topic,
            query_used=topic,
            chunks=[],
        )

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={topic: empty_result})
        grounding_service = GroundingService(grounding_client)

        agent_client = StubCognitiveAgentClient(canned_response="{}")
        agent_service = CognitiveAgentService(agent_client)

        content_service = ContentService(ls)

        orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        # Spy on content_service
        with mock.patch.object(
            orchestrator.content_service,
            "commit_section",
            wraps=orchestrator.content_service.commit_section,
        ) as spy_commit:
            with pytest.raises(NoGroundingAvailableError) as exc_info:
                orchestrator.generate_and_commit_section(
                    topic=topic,
                    level=level,
                    section_id=section_id,
                )

            # Verify exception carries the topic
            assert exc_info.value.topic == topic
            assert topic in str(exc_info.value)

            # commit_section never called
            spy_commit.assert_not_called()


class TestGenerationOrchestratorAgentError:
    """Test 4: LessonSectionGenerationError propagates, content_service never called."""

    def test_agent_generation_error_propagates_uncaught(self, tmp_path) -> None:
        """LessonSectionGenerationError from agent propagates; commit_section never called."""
        topic = "algebra"
        level = "beginner"
        section_id = "sec_001"

        # Grounding returns valid chunks
        grounding_result = _make_grounding_result(topic, num_chunks=2)

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={topic: grounding_result})
        grounding_service = GroundingService(grounding_client)

        # Agent returns MALFORMED JSON -> triggers LessonSectionGenerationError
        agent_client = StubCognitiveAgentClient(canned_response="not valid json {")
        agent_service = CognitiveAgentService(agent_client)

        content_service = ContentService(ls)

        orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        # Spy on commit_section
        with mock.patch.object(
            orchestrator.content_service,
            "commit_section",
            wraps=orchestrator.content_service.commit_section,
        ) as spy_commit:
            with pytest.raises(LessonSectionGenerationError) as exc_info:
                orchestrator.generate_and_commit_section(
                    topic=topic,
                    level=level,
                    section_id=section_id,
                )

            # Verify it's the exact LessonSectionGenerationError
            assert "JSON parsing failed" in str(exc_info.value)

            # CRITICAL: commit_section never called - bad LLM output never reaches storage
            spy_commit.assert_not_called()

    def test_agent_validation_error_empty_source_indices(self, tmp_path) -> None:
        """Agent returns valid JSON but empty source_indices -> LessonSectionGenerationError."""
        topic = "algebra"
        level = "beginner"
        section_id = "sec_001"

        grounding_result = _make_grounding_result(topic, num_chunks=2)

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={topic: grounding_result})
        grounding_service = GroundingService(grounding_client)

        # Valid JSON but empty source_indices (fails Pydantic validation)
        import json

        agent_response = json.dumps(
            {
                "section_title": "Test Section",
                "body": "This is a test body with sufficient length to pass validation.",
                "source_indices": [],
            }
        )
        agent_client = StubCognitiveAgentClient(canned_response=agent_response)
        agent_service = CognitiveAgentService(agent_client)

        content_service = ContentService(ls)

        orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        with mock.patch.object(
            orchestrator.content_service,
            "commit_section",
            wraps=orchestrator.content_service.commit_section,
        ) as spy_commit:
            with pytest.raises(LessonSectionGenerationError) as exc_info:
                orchestrator.generate_and_commit_section(
                    topic=topic,
                    level=level,
                    section_id=section_id,
                )

            assert "section must cite at least one source_index" in str(exc_info.value)
            spy_commit.assert_not_called()

    def test_agent_out_of_range_source_indices(self, tmp_path) -> None:
        """Agent cites index 99 when only 2 chunks exist -> LessonSectionGenerationError."""
        topic = "algebra"
        level = "beginner"
        section_id = "sec_001"

        grounding_result = _make_grounding_result(topic, num_chunks=2)

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={topic: grounding_result})
        grounding_service = GroundingService(grounding_client)

        # Valid JSON but out-of-range source index
        import json

        agent_response = json.dumps(
            {
                "section_title": "Test Section",
                "body": "This is a test body with sufficient length to pass validation.",
                "source_indices": [99],  # Only indices 0,1 exist
            }
        )
        agent_client = StubCognitiveAgentClient(canned_response=agent_response)
        agent_service = CognitiveAgentService(agent_client)

        content_service = ContentService(ls)

        orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        with mock.patch.object(
            orchestrator.content_service,
            "commit_section",
            wraps=orchestrator.content_service.commit_section,
        ) as spy_commit:
            with pytest.raises(LessonSectionGenerationError) as exc_info:
                orchestrator.generate_and_commit_section(
                    topic=topic,
                    level=level,
                    section_id=section_id,
                )

            assert "out-of-range index 99" in str(exc_info.value)
            spy_commit.assert_not_called()


class TestGenerationOrchestratorCitationsCorrect:
    """Test 5: Returned Section has correct citation_text strings from grounding chunks."""

    def test_citations_match_grounding_chunks_exactly(self, tmp_path) -> None:
        """Citations in returned Section match draft_to_citations output exactly."""
        topic = "geometry"
        level = "intermediate"
        section_id = "geo_001"

        # 3 grounding chunks
        grounding_result = _make_grounding_result(topic, num_chunks=3)

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={topic: grounding_result})
        grounding_service = GroundingService(grounding_client)

        # Agent cites indices [0, 2] (skipping index 1)
        agent_response = _make_valid_agent_response(
            section_title="Euclidean Geometry",
            body="Euclidean geometry studies flat space. Points, lines, and planes are fundamental.",
            source_indices=[0, 2],
        )
        agent_client = StubCognitiveAgentClient(canned_response=agent_response)
        agent_service = CognitiveAgentService(agent_client)

        content_service = ContentService(ls)

        orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        section = orchestrator.generate_and_commit_section(
            topic=topic,
            level=level,
            section_id=section_id,
        )

        # Verify citations EXACTLY match what draft_to_citations produces
        # from the grounding chunks at indices 0 and 2
        assert len(section.source_citations) == 2
        assert section.source_citations[0] == (
            "Geometry Source 0 (https://example.com/geometry/0, retrieved 2025-01-15)"
        )
        assert section.source_citations[1] == (
            "Geometry Source 2 (https://example.com/geometry/2, retrieved 2025-01-15)"
        )

        # Verify NO fabricated/empty citations
        for citation in section.source_citations:
            assert citation.strip() != ""
            assert "Geometry Source" in citation
            assert "https://example.com/geometry/" in citation


class TestGenerationOrchestratorMultipleSections:
    """Test 6: Multiple sections on same topic append correctly."""

    def test_multiple_sections_same_topic_different_ids(self, tmp_path) -> None:
        """Two calls with different section_ids on same topic append both sections."""
        topic = "calculus"
        level = "advanced"

        grounding_result = _make_grounding_result(topic, num_chunks=2)

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={topic: grounding_result})
        grounding_service = GroundingService(grounding_client)

        content_service = ContentService(ls)

        # First section
        agent_response_1 = _make_valid_agent_response(
            section_title="Limits and Continuity",
            body="Limits describe the behavior of functions as inputs approach a value. Continuity means no jumps.",
            source_indices=[0],
        )
        agent_client_1 = StubCognitiveAgentClient(canned_response=agent_response_1)
        agent_service_1 = CognitiveAgentService(agent_client_1)

        orchestrator_1 = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service_1,
            content_service=content_service,
        )

        section_1 = orchestrator_1.generate_and_commit_section(
            topic=topic,
            level=level,
            section_id="sec_001",
        )

        # Second section - different agent response
        agent_response_2 = _make_valid_agent_response(
            section_title="Derivatives",
            body="The derivative measures instantaneous rate of change. It is the limit of the difference quotient.",
            source_indices=[1],
        )
        agent_client_2 = StubCognitiveAgentClient(canned_response=agent_response_2)
        agent_service_2 = CognitiveAgentService(agent_client_2)

        orchestrator_2 = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service_2,
            content_service=content_service,
        )

        section_2 = orchestrator_2.generate_and_commit_section(
            topic=topic,
            level=level,
            section_id="sec_002",
        )

        # Verify both sections exist and are distinct
        assert section_1.section_id == "sec_001"
        assert section_1.title == "Limits and Continuity"
        assert section_1.source_citations == [
            "Calculus Source 0 (https://example.com/calculus/0, retrieved 2025-01-15)"
        ]

        assert section_2.section_id == "sec_002"
        assert section_2.title == "Derivatives"
        assert section_2.source_citations == [
            "Calculus Source 1 (https://example.com/calculus/1, retrieved 2025-01-15)"
        ]

        # Verify ContentService lesson has BOTH sections in order
        lesson = content_service.get_lesson(topic)
        assert lesson is not None
        assert len(lesson.sections) == 2
        assert [s.section_id for s in lesson.sections] == ["sec_001", "sec_002"]
        assert lesson.sections[0].title == "Limits and Continuity"
        assert lesson.sections[1].title == "Derivatives"
