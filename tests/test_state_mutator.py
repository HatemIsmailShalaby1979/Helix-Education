"""Tests for progress_engine.state_mutator."""

import pytest

from progress_engine.state_mutator import StateMutatorService
from state_core.event_models import (
    LearningStateUpdatedEvent,
    QuizItemCreatedEvent,
    QuizResultEvent,
)
from state_core.event_store import EventStore, StoreConfig


@pytest.fixture
def event_store(tmp_path) -> EventStore:
    return EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))


@pytest.fixture
def mutator(event_store) -> StateMutatorService:
    return StateMutatorService(event_store)


def _seed_quiz_items(
    event_store: EventStore,
    topic: str,
    quiz_id: str,
    item_ids: list[str],
) -> None:
    for item_id in item_ids:
        event_store.append(
            QuizItemCreatedEvent.create(
                topic=topic,
                quiz_id=quiz_id,
                quiz_item_id=item_id,
                question=f"Q? {item_id}",
                category="sa",
                difficulty="easy",
                answer_key_hash="abc",
            )
        )


class TestStateMutatorInit:
    """Tests for StateMutatorService initialization."""

    def test_empty_store_initializes_clean_state(self, mutator) -> None:
        state = mutator.get_state()
        assert state.total_questions_studied == 0
        assert state.running_average_score == 0.0
        assert state.topics_mastered == []
        assert state.topics_in_progress == []

    def test_rebuilds_from_existing_quiz_result_events(self, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2"])
        event_store.append(QuizResultEvent.create(quiz_id="q1", quiz_item_id="qi1", raw_score=0.8, passed=True))
        event_store.append(QuizResultEvent.create(quiz_id="q1", quiz_item_id="qi2", raw_score=1.0, passed=True))
        mutator = StateMutatorService(event_store)
        state = mutator.get_state()
        assert state.total_questions_studied == 2
        assert state.running_average_score == pytest.approx(0.9)


class TestProcessQuizResult:
    """Tests for process_quiz_result method."""

    def test_appends_quiz_result_event(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)

        events = event_store.read_all()
        result_events = [e for e in events if isinstance(e, QuizResultEvent)]
        assert len(result_events) == 1
        assert result_events[0].quiz_item_id == "qi1"
        assert result_events[0].raw_score == 0.8

    def test_appends_learning_state_updated_event(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)

        events = event_store.read_all()
        update_events = [e for e in events if isinstance(e, LearningStateUpdatedEvent)]
        assert len(update_events) == 1
        assert update_events[0].total_questions_studied == 1
        assert update_events[0].running_average_score == pytest.approx(0.8)

    def test_updates_total_questions_studied(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2", "qi3"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)
        mutator.process_quiz_result("q1", "qi2", 0.4, False)
        mutator.process_quiz_result("q1", "qi3", 1.0, True)

        state = mutator.get_state()
        assert state.total_questions_studied == 3

    def test_running_average_score(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)
        mutator.process_quiz_result("q1", "qi2", 0.4, False)

        state = mutator.get_state()
        assert state.running_average_score == pytest.approx(0.6)

    def test_topic_mastered_when_all_items_pass(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)
        mutator.process_quiz_result("q1", "qi2", 1.0, True)

        state = mutator.get_state()
        assert "algebra" in state.topics_mastered
        assert "algebra" not in state.topics_in_progress

    def test_topic_in_progress_when_some_items_fail(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)
        mutator.process_quiz_result("q1", "qi2", 0.2, False)

        state = mutator.get_state()
        assert "algebra" not in state.topics_mastered
        assert "algebra" in state.topics_in_progress

    def test_topic_not_mastered_when_one_item_unanswered(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)

        state = mutator.get_state()
        assert "algebra" not in state.topics_mastered
        assert "algebra" in state.topics_in_progress

    def test_multiple_topics_independent(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1"])
        _seed_quiz_items(event_store, "geometry", "q2", ["qi2"])

        mutator.process_quiz_result("q1", "qi1", 1.0, True)
        mutator.process_quiz_result("q2", "qi2", 0.2, False)

        state = mutator.get_state()
        assert "algebra" in state.topics_mastered
        assert "geometry" in state.topics_in_progress
        assert "geometry" not in state.topics_mastered

    def test_best_score_used_for_mastery(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1"])
        mutator.process_quiz_result("q1", "qi1", 0.2, False)
        mutator.process_quiz_result("q1", "qi1", 0.8, True)

        state = mutator.get_state()
        assert "algebra" in state.topics_mastered

    def test_state_lists_are_sorted(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "zebra", "q1", ["qi1"])
        _seed_quiz_items(event_store, "alpha", "q2", ["qi2"])
        _seed_quiz_items(event_store, "middle", "q3", ["qi3"])

        mutator.process_quiz_result("q1", "qi1", 0.3, False)
        mutator.process_quiz_result("q2", "qi2", 0.3, False)
        mutator.process_quiz_result("q3", "qi3", 0.3, False)

        state = mutator.get_state()
        assert state.topics_in_progress == ["alpha", "middle", "zebra"]


class TestGetTopicMastery:
    """Tests for get_topic_mastery method."""

    def test_no_items_returns_zero(self, mutator) -> None:
        result = mutator.get_topic_mastery("nonexistent")
        assert result["is_mastered"] is False
        assert result["is_in_progress"] is False
        assert result["item_count"] == 0
        assert result["answered_count"] == 0

    def test_mastered_topic(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)
        mutator.process_quiz_result("q1", "qi2", 1.0, True)

        result = mutator.get_topic_mastery("algebra")
        assert result["is_mastered"] is True
        assert result["is_in_progress"] is False
        assert result["item_count"] == 2
        assert result["answered_count"] == 2

    def test_in_progress_topic(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2"])
        mutator.process_quiz_result("q1", "qi1", 0.8, True)

        result = mutator.get_topic_mastery("algebra")
        assert result["is_mastered"] is False
        assert result["is_in_progress"] is True
        assert result["item_count"] == 2
        assert result["answered_count"] == 1


class TestEventSourcingIntegrity:
    """Verify full event-sourced traceability."""

    def test_two_events_per_result(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1"])
        before = len(event_store.read_all())
        mutator.process_quiz_result("q1", "qi1", 0.8, True)
        after = len(event_store.read_all())
        assert after - before == 2

    def test_rebuild_after_restart(self, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1", "qi2"])

        mutator1 = StateMutatorService(event_store)
        mutator1.process_quiz_result("q1", "qi1", 0.8, True)

        mutator2 = StateMutatorService(event_store)
        state = mutator2.get_state()
        assert state.total_questions_studied == 1
        assert state.running_average_score == pytest.approx(0.8)

    def test_learning_state_updated_event_snapshot(self, mutator, event_store) -> None:
        _seed_quiz_items(event_store, "algebra", "q1", ["qi1"])
        mutator.process_quiz_result("q1", "qi1", 1.0, True)

        events = event_store.read_all()
        update = [e for e in events if isinstance(e, LearningStateUpdatedEvent)][-1]
        assert update.total_questions_studied == 1
        assert update.running_average_score == pytest.approx(1.0)
        assert update.topics_mastered == ["algebra"]
        assert update.topics_in_progress == []
