"""Tests for LessonOrchestrator.

All tests use StubGroundingClient and StubQuizGeneratorService — zero
live network calls, zero real LLM calls.
"""

from unittest import mock

import pytest

from cognitive_agent.agent_client import StubCognitiveAgentClient
from cognitive_agent.agent_models import LessonSectionGenerationError
from cognitive_agent.agent_service import CognitiveAgentService
from cognitive_engine.quiz_generator import GeneratedQuizItem
from content_engine import ContentService
from content_engine.generation_orchestrator import (
    GenerationOrchestrator,
    NoGroundingAvailableError,
)
from content_engine.lesson_orchestrator import LessonOrchestrator, LessonResult
from grounding_engine import GroundingService
from grounding_engine.grounding_client import StubGroundingClient
from grounding_engine.grounding_models import (
    GroundingFetchError,
    GroundingResult,
    SourceChunk,
)
from learning_service import LearningService
from quiz_engine import QuizService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig


class StubQuizGeneratorService:
    """Deterministic quiz generator for testing.

    Returns canned quiz items regardless of input text.
    """

    def __init__(self, items: list[GeneratedQuizItem] | None = None) -> None:
        self._items = items or [
            GeneratedQuizItem(
                quiz_item_id="stub-q1",
                question="What is the topic about?",
                category="short_answer",
                difficulty="easy",
                required_keywords=["concept", "definition"],
            ),
            GeneratedQuizItem(
                quiz_item_id="stub-q2",
                question="Why is this important?",
                category="short_answer",
                difficulty="medium",
                required_keywords=["importance", "value"],
            ),
        ]

    def generate_quiz_from_text(
        self,
        topic: str,
        text_content: str,
        num_questions: int = 3,
    ) -> list[GeneratedQuizItem]:
        return self._items[:num_questions]


def _make_grounding_result(topic: str, num_chunks: int = 2) -> GroundingResult:
    """Create a GroundingResult with the given number of chunks."""
    chunks = [
        SourceChunk(
            content=f"Chunk {i} content for {topic}.",
            source_url=f"https://example.com/{topic}/{i}",
            source_title=f"{topic.title()} Source {i}",
            retrieved_at="2025-01-15T10:00:00+00:00",
            citation_text=(f"{topic.title()} Source {i} (https://example.com/{topic}/{i}, retrieved 2025-01-15)"),
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


def _make_lesson_orchestrator(
    tmp_path,
    topic: str,
    grounding_result: GroundingResult,
    agent_response_factory,
    quiz_items: list[GeneratedQuizItem] | None = None,
):
    """Create a fully wired LessonOrchestrator for testing."""
    es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
    ks = SealedAnswerKeyStore()
    ls = LearningService(es, ks)

    grounding_client = StubGroundingClient(canned_responses={topic: grounding_result})
    grounding_service = GroundingService(grounding_client)

    agent_client = StubCognitiveAgentClient(canned_response="")
    agent_client.generate_raw = mock.Mock(side_effect=agent_response_factory)
    agent_service = CognitiveAgentService(agent_client)

    content_service = ContentService(ls)

    generation_orchestrator = GenerationOrchestrator(
        grounding_service=grounding_service,
        agent_service=agent_service,
        content_service=content_service,
    )

    quiz_service = QuizService(ls)
    quiz_generator = StubQuizGeneratorService(items=quiz_items)

    lesson_orchestrator = LessonOrchestrator(
        generation_orchestrator=generation_orchestrator,
        quiz_service=quiz_service,
        quiz_generator=quiz_generator,
    )

    return lesson_orchestrator, ls, es, quiz_service


class TestLessonOrchestratorHappyPath:
    """Test 1: Happy path — multiple sections + quiz created correctly."""

    def test_generate_full_lesson_happy_path(self, tmp_path) -> None:
        """Multiple sections generate successfully, quiz created with items."""
        topic = "algebra"
        level = "beginner"

        grounding_result = _make_grounding_result(topic, num_chunks=3)

        call_count = [0]

        def agent_response_factory(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_valid_agent_response(
                    section_title="Introduction to Algebra",
                    body=(
                        "Algebra is the study of mathematical symbols "
                        "and the rules for manipulating them. It forms "
                        "the foundation for advanced mathematics."
                    ),
                    source_indices=[0, 1],
                )
            return _make_valid_agent_response(
                section_title="Variables and Constants",
                body=("Variables represent unknown values. Constants are fixed values that do not change."),
                source_indices=[2],
            )

        quiz_items = [
            GeneratedQuizItem(
                quiz_item_id="q1",
                question="What is algebra?",
                category="short_answer",
                difficulty="easy",
                required_keywords=["symbols", "rules"],
            ),
            GeneratedQuizItem(
                quiz_item_id="q2",
                question="What is a variable?",
                category="short_answer",
                difficulty="easy",
                required_keywords=["unknown", "value"],
            ),
        ]

        lesson_orchestrator, ls, es, quiz_service = _make_lesson_orchestrator(
            tmp_path, topic, grounding_result, agent_response_factory, quiz_items
        )

        section_specs = [
            {"section_id": "sec_001", "max_chunks": 3},
            {"section_id": "sec_002", "max_chunks": 3},
        ]

        quiz_id = "algebra_quiz"

        result = lesson_orchestrator.generate_full_lesson(
            topic=topic,
            level=level,
            section_specs=section_specs,
            quiz_id=quiz_id,
            num_quiz_questions=2,
        )

        assert isinstance(result, LessonResult)
        assert len(result.sections) == 2
        assert result.quiz is not None

        assert result.sections[0].section_id == "sec_001"
        assert result.sections[0].title == "Introduction to Algebra"
        assert "Algebra is the study" in result.sections[0].body
        assert len(result.sections[0].source_citations) == 2

        assert result.sections[1].section_id == "sec_002"
        assert result.sections[1].title == "Variables and Constants"
        assert "Variables represent unknown" in result.sections[1].body
        assert len(result.sections[1].source_citations) == 1

        assert result.quiz.quiz_id == quiz_id
        assert result.quiz.topic == topic
        assert len(result.quiz.items) == 2

        item1 = result.quiz.items[0]
        assert item1.quiz_item_id == "q1"
        assert item1.question == "What is algebra?"
        assert item1.category == "short_answer"
        assert item1.difficulty == "easy"

        item2 = result.quiz.items[1]
        assert item2.quiz_item_id == "q2"
        assert item2.question == "What is a variable?"

        retrieved_quiz = quiz_service.get_quiz(quiz_id)
        assert retrieved_quiz is not None
        assert retrieved_quiz.quiz_id == quiz_id
        assert len(retrieved_quiz.items) == 2

        events = es.read_all()
        from state_core.event_models import (
            LessonSectionCommittedEvent,
            QuizCreatedEvent,
            QuizItemCreatedEvent,
        )

        section_events = [e for e in events if isinstance(e, LessonSectionCommittedEvent)]
        quiz_created_events = [e for e in events if isinstance(e, QuizCreatedEvent)]
        quiz_item_events = [e for e in events if isinstance(e, QuizItemCreatedEvent)]

        assert len(section_events) == 2
        assert len(quiz_created_events) == 1
        assert len(quiz_item_events) == 2


class TestLessonOrchestratorSectionFailure:
    """Test 2: Second-of-three section failure blocks quiz AND later sections."""

    def test_section_failure_blocks_quiz_and_later_sections(self, tmp_path) -> None:
        """Malformed agent JSON on section 2 blocks quiz and later sections."""
        topic = "geometry"
        level = "intermediate"

        grounding_result = _make_grounding_result(topic, num_chunks=3)

        valid_response_1 = _make_valid_agent_response(
            section_title="Euclidean Geometry",
            body=("Euclidean geometry studies flat space. Points, lines, and planes are fundamental."),
            source_indices=[0],
        )
        malformed_response = "not valid json {"
        valid_response_3 = _make_valid_agent_response(
            section_title="Non-Euclidean Geometry",
            body="Non-Euclidean geometry explores curved spaces.",
            source_indices=[1, 2],
        )

        call_count = [0]

        def agent_response_factory(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return valid_response_1
            elif call_count[0] == 2:
                return malformed_response
            return valid_response_3

        lesson_orchestrator, ls, es, quiz_service = _make_lesson_orchestrator(
            tmp_path, topic, grounding_result, agent_response_factory
        )

        section_specs = [
            {"section_id": "sec_001", "max_chunks": 2},
            {"section_id": "sec_002", "max_chunks": 2},
            {"section_id": "sec_003", "max_chunks": 2},
        ]
        quiz_id = "geometry_quiz"

        with mock.patch.object(quiz_service, "create_quiz", wraps=quiz_service.create_quiz) as spy_create_quiz:
            with pytest.raises(LessonSectionGenerationError) as exc_info:
                lesson_orchestrator.generate_full_lesson(
                    topic=topic,
                    level=level,
                    section_specs=section_specs,
                    quiz_id=quiz_id,
                    num_quiz_questions=1,
                )

            assert "JSON parsing failed" in str(exc_info.value)
            spy_create_quiz.assert_not_called()

            events = es.read_all()
            from state_core.event_models import LessonSectionCommittedEvent

            section_events = [e for e in events if isinstance(e, LessonSectionCommittedEvent)]
            assert len(section_events) == 1
            assert section_events[0].section_id == "sec_001"

            from state_core.event_models import QuizCreatedEvent, QuizItemCreatedEvent

            quiz_events = [e for e in events if isinstance(e, (QuizCreatedEvent, QuizItemCreatedEvent))]
            assert len(quiz_events) == 0


class TestLessonOrchestratorQuizItems:
    """Test 3: Quiz items added correctly with real AnswerKey objects."""

    def test_quiz_items_added_with_answer_keys(self, tmp_path) -> None:
        """Quiz items created with AnswerKey, verified via quiz_service.get_quiz()."""
        topic = "calculus"
        level = "advanced"

        grounding_result = _make_grounding_result(topic, num_chunks=3)
        agent_response = _make_valid_agent_response(
            section_title="Limits and Continuity",
            body=("Limits describe function behavior near a point. Continuity means no jumps."),
            source_indices=[0, 1],
        )

        def agent_response_factory(*args, **kwargs):
            return agent_response

        quiz_items = [
            GeneratedQuizItem(
                quiz_item_id="q1_limits",
                question="What is a limit?",
                category="short_answer",
                difficulty="medium",
                required_keywords=["approaches", "value", "function"],
            ),
            GeneratedQuizItem(
                quiz_item_id="q2_continuity",
                question="Define continuity.",
                category="short_answer",
                difficulty="medium",
                required_keywords=["no", "jumps", "limit", "equals", "function"],
            ),
        ]

        lesson_orchestrator, ls, es, quiz_service = _make_lesson_orchestrator(
            tmp_path, topic, grounding_result, agent_response_factory, quiz_items
        )

        section_specs = [{"section_id": "sec_001", "max_chunks": 2}]
        quiz_id = "calculus_quiz"

        lesson_orchestrator.generate_full_lesson(
            topic=topic,
            level=level,
            section_specs=section_specs,
            quiz_id=quiz_id,
            num_quiz_questions=2,
        )

        retrieved_quiz = quiz_service.get_quiz(quiz_id)
        assert retrieved_quiz is not None
        assert len(retrieved_quiz.items) == 2

        from state_core.event_models import QuizItemCreatedEvent

        events = es.read_all()
        quiz_item_events = [e for e in events if isinstance(e, QuizItemCreatedEvent)]
        assert len(quiz_item_events) == 2

        for event in quiz_item_events:
            assert event.answer_key_hash is not None
            assert len(event.answer_key_hash) == 64

        item1 = next(i for i in retrieved_quiz.items if i.quiz_item_id == "q1_limits")
        assert item1.question == "What is a limit?"
        assert item1.category == "short_answer"
        assert item1.difficulty == "medium"

        item2 = next(i for i in retrieved_quiz.items if i.quiz_item_id == "q2_continuity")
        assert item2.question == "Define continuity."


class TestLessonOrchestratorNoGrounding:
    """Test: NoGroundingAvailableError propagates, no quiz created."""

    def test_no_grounding_available_propagates(self, tmp_path) -> None:
        """Empty grounding raises NoGroundingAvailableError; quiz not created."""
        topic = "empty_topic"
        level = "beginner"

        empty_result = GroundingResult(topic=topic, query_used=topic, chunks=[])
        agent_response = "{}"

        def agent_response_factory(*args, **kwargs):
            return agent_response

        lesson_orchestrator, ls, es, quiz_service = _make_lesson_orchestrator(
            tmp_path, topic, empty_result, agent_response_factory
        )

        section_specs = [{"section_id": "sec_001", "max_chunks": 2}]
        quiz_id = "empty_quiz"

        with mock.patch.object(quiz_service, "create_quiz", wraps=quiz_service.create_quiz) as spy_create_quiz:
            with pytest.raises(NoGroundingAvailableError):
                lesson_orchestrator.generate_full_lesson(
                    topic=topic,
                    level=level,
                    section_specs=section_specs,
                    quiz_id=quiz_id,
                    num_quiz_questions=1,
                )

            spy_create_quiz.assert_not_called()


class TestLessonOrchestratorGroundingFetchError:
    """Test: GroundingFetchError propagates, no quiz created."""

    def test_grounding_fetch_error_propagates(self, tmp_path) -> None:
        """GroundingFetchError from grounding step propagates; quiz never called."""
        topic = "fail_topic"
        level = "beginner"

        def failing_fetch(*args, **kwargs):
            raise GroundingFetchError("Network error")

        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        grounding_client = StubGroundingClient(canned_responses={})
        grounding_client.fetch = failing_fetch
        grounding_service = GroundingService(grounding_client)

        agent_client = StubCognitiveAgentClient(canned_response="{}")
        agent_service = CognitiveAgentService(agent_client)

        content_service = ContentService(ls)

        generation_orchestrator = GenerationOrchestrator(
            grounding_service=grounding_service,
            agent_service=agent_service,
            content_service=content_service,
        )

        quiz_service = QuizService(ls)
        quiz_generator = StubQuizGeneratorService()

        lesson_orchestrator = LessonOrchestrator(
            generation_orchestrator=generation_orchestrator,
            quiz_service=quiz_service,
            quiz_generator=quiz_generator,
        )

        section_specs = [{"section_id": "sec_001", "max_chunks": 2}]
        quiz_id = "fail_quiz"

        with mock.patch.object(quiz_service, "create_quiz", wraps=quiz_service.create_quiz) as spy_create_quiz:
            with pytest.raises(GroundingFetchError):
                lesson_orchestrator.generate_full_lesson(
                    topic=topic,
                    level=level,
                    section_specs=section_specs,
                    quiz_id=quiz_id,
                    num_quiz_questions=1,
                )

            spy_create_quiz.assert_not_called()
