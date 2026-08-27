"""Tests for state_core.event_models."""

from datetime import datetime
from uuid import UUID

import pytest

from state_core.event_models import (
    AnswerScoredEvent,
    AnswerSubmittedEvent,
    Event,
    LessonSectionCommittedEvent,
    ProfileDeltaApprovedEvent,
    ProfileDeltaProposedEvent,
    QuizItemCreatedEvent,
    TopicBranchedEvent,
    TopicPassedEvent,
    TopicStartedEvent,
)


class TestEventBase:
    """Happy-path tests for all event types."""

    def test_topic_started_event(self) -> None:
        e = TopicStartedEvent.create(topic="algebra", requested_level="intermediate")
        assert e.topic == "algebra"
        assert e.requested_level == "intermediate"
        assert e.parent_topic is None
        assert UUID(e.event_id).version == 4
        datetime.fromisoformat(e.timestamp)

    def test_lesson_section_committed_event(self) -> None:
        e = LessonSectionCommittedEvent.create(
            topic="algebra",
            section_id="sec_001",
            title="Section One",
            body="Content body",
            source_citations=["src1", "src2"],
        )
        assert e.topic == "algebra"
        assert e.section_id == "sec_001"
        assert e.source_citations == ["src1", "src2"]

    def test_quiz_item_created_event(self) -> None:
        e = QuizItemCreatedEvent.create(
            topic="algebra",
            quiz_id="quiz-1",
            quiz_item_id="q_001",
            question="What is algebra?",
            category="multiple_choice",
            difficulty="easy",
            answer_key_hash="abc123deadbeef",
        )
        assert e.topic == "algebra"
        assert e.quiz_id == "quiz-1"
        assert e.quiz_item_id == "q_001"
        assert e.question == "What is algebra?"
        assert e.category == "multiple_choice"
        assert e.difficulty == "easy"
        assert e.answer_key_hash == "abc123deadbeef"

    def test_answer_submitted_event(self) -> None:
        e = AnswerSubmittedEvent.create(
            quiz_item_id="q_001",
            raw_answer="42",
            attempt_number=1,
        )
        assert e.quiz_item_id == "q_001"
        assert e.raw_answer == "42"
        assert e.attempt_number == 1

    def test_answer_scored_event(self) -> None:
        e = AnswerScoredEvent.create(
            quiz_item_id="q_001",
            raw_score=0.85,
            passed=True,
            scoring_method="keyword",
        )
        assert e.quiz_item_id == "q_001"
        assert e.raw_score == 0.85
        assert e.passed is True
        assert e.scoring_method == "keyword"

    def test_topic_passed_event(self) -> None:
        e = TopicPassedEvent.create(
            topic="algebra",
            final_level="intermediate",
            attempts_total=5,
        )
        assert e.topic == "algebra"
        assert e.final_level == "intermediate"
        assert e.attempts_total == 5

    def test_topic_branched_event(self) -> None:
        e = TopicBranchedEvent.create(
            parent_topic="algebra",
            child_topic="linear-equations",
            reason="learner requested deeper study",
        )
        assert e.parent_topic == "algebra"
        assert e.child_topic == "linear-equations"
        assert e.reason == "learner requested deeper study"

    def test_profile_delta_proposed_event(self) -> None:
        e = ProfileDeltaProposedEvent.create(
            evidence=["completed quiz q_001"],
            proposed_changes={"learning_style": "visual"},
        )
        assert e.evidence == ["completed quiz q_001"]
        assert e.proposed_changes == {"learning_style": "visual"}
        assert e.approved is False

    def test_profile_delta_proposed_event_approved_forced_false(self) -> None:
        e = ProfileDeltaProposedEvent(
            event_id="ignored",
            timestamp="ignored",
            evidence=["test"],
            proposed_changes={},
            approved=True,
        )
        assert e.approved is False

    def test_profile_delta_approved_event(self) -> None:
        e = ProfileDeltaApprovedEvent.create(
            delta_event_id="some_proposed_id",
        )
        assert e.delta_event_id == "some_proposed_id"
        assert e.approved_by == "user"

    def test_profile_delta_approved_custom_approver(self) -> None:
        e = ProfileDeltaApprovedEvent.create(
            delta_event_id="some_id",
            approved_by="admin",
        )
        assert e.approved_by == "admin"


class TestSerialization:
    """Round-trip serialization/deserialization tests."""

    def test_topic_started_round_trip(self) -> None:
        original = TopicStartedEvent.create(topic="algebra", requested_level="intermediate")
        data = original.to_dict()
        restored = Event.from_dict(data)
        assert isinstance(restored, TopicStartedEvent)
        assert restored.topic == original.topic
        assert restored.requested_level == original.requested_level
        assert restored.event_id == original.event_id
        assert restored.timestamp == original.timestamp

    def test_profile_delta_proposed_round_trip_approved_reset(self) -> None:
        original = ProfileDeltaProposedEvent.create(
            evidence=["x"],
            proposed_changes={"a": "b"},
        )
        data = original.to_dict()
        data["approved"] = True
        restored = Event.from_dict(data)
        assert isinstance(restored, ProfileDeltaProposedEvent)
        assert restored.approved is False

    def test_unknown_event_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown event type"):
            Event.from_dict({"__event_type__": "bogus"})

    def test_missing_event_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown event type"):
            Event.from_dict({"event_id": "x", "timestamp": "y"})


class TestEdgeCases:
    """Edge cases for event creation."""

    def test_optional_fields_default_to_none(self) -> None:
        e = TopicStartedEvent.create(topic="python")
        assert e.requested_level is None
        assert e.parent_topic is None
        assert e.topic == "python"

    def test_empty_citations(self) -> None:
        e = LessonSectionCommittedEvent.create(
            topic="python",
            section_id="s1",
            title="t",
            body="b",
            source_citations=[],
        )
        assert e.source_citations == []

    def test_all_event_types_have_unique_event_ids(self) -> None:
        ids = [
            TopicStartedEvent.create(topic="a").event_id,
            LessonSectionCommittedEvent.create(
                topic="a", section_id="s1", title="t", body="b", source_citations=[]
            ).event_id,
        ]
        assert len(set(ids)) == len(ids)
