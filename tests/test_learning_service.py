"""Tests for learning_service.py."""

import pytest

from learning_service import LearningService
from state_core.event_store import EventStore, StoreConfig
from state_core.projections import TopicState
from state_core.scoring_engine import AnswerKey


@pytest.fixture
def service(tmp_path) -> LearningService:
    """Provide a LearningService backed by temp EventStore and in-memory key store."""
    from state_core.event_store import SealedAnswerKeyStore

    es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
    ks = SealedAnswerKeyStore()
    return LearningService(es, ks)


class TestTopicLifecycle:
    """Tests for topic start, state query, level, pass, branch."""

    def test_start_topic_creates_event_and_returns_state(self, service) -> None:
        state = service.start_topic("algebra", requested_level="intermediate")
        assert isinstance(state, TopicState)
        assert state.topic == "algebra"

    def test_start_topic_with_parent(self, service) -> None:
        state = service.start_topic("linear-equations", parent_topic="algebra")
        assert state.topic == "linear-equations"
        # parent_topic is stored in the event, not reflected in TopicState
        # (TopicState doesn't track parent — that's a domain concern)

    def test_get_topic_state_empty(self, service) -> None:
        state = service.get_topic_state("nonexistent")
        assert state.topic == "nonexistent"
        assert state.attempts_total == 0

    def test_get_topic_state_after_events(self, service) -> None:
        service.start_topic("algebra")
        state = service.get_topic_state("algebra")
        assert state.last_activity_timestamp != ""

    def test_compute_level_beginner(self, service) -> None:
        service.start_topic("algebra")
        level = service.compute_topic_level("algebra")
        assert level == "beginner"

    def test_pass_topic(self, service) -> None:
        service.start_topic("algebra")
        passed = service.pass_topic("algebra", "intermediate")
        assert passed.topic == "algebra"
        assert passed.final_level == "intermediate"
        state = service.get_topic_state("algebra")
        assert state.is_passed is True
        assert state.current_level == "intermediate"

    def test_branch_topic(self, service) -> None:
        service.start_topic("algebra")
        branch = service.branch_topic(
            "algebra",
            "linear-equations",
            "learner needs deeper study",
        )
        assert branch.parent_topic == "algebra"
        assert branch.child_topic == "linear-equations"
        state = service.get_topic_state("algebra")
        assert "linear-equations" in state.branch_children


class TestLessonLifecycle:
    """Tests for lesson section commitment."""

    def test_commit_lesson_section(self, service) -> None:
        service.start_topic("algebra")
        service.commit_lesson_section(
            topic="algebra",
            section_id="sec_001",
            title="Section One",
            body="Content body",
            source_citations=["src1", "src2"],
        )
        state = service.get_topic_state("algebra")
        assert state.last_activity_timestamp != ""


class TestQuizLifecycle:
    """Tests for quiz item creation and answer scoring."""

    def test_create_quiz_item(self, service) -> None:
        key = AnswerKey(required_keywords=["foo", "bar"])
        event = service.create_quiz_item(
            topic="algebra",
            quiz_id="quiz-1",
            quiz_item_id="q_001",
            question="What is foo?",
            category="short_answer",
            difficulty="easy",
            answer_key=key,
        )
        assert event.topic == "algebra"
        assert event.quiz_id == "quiz-1"
        assert event.quiz_item_id == "q_001"
        assert event.question == "What is foo?"
        assert event.answer_key_hash != ""  # hash is set, not raw key

    def test_submit_and_score_answer_passing(self, service) -> None:
        key = AnswerKey(required_keywords=["foo", "bar"])
        service.create_quiz_item("algebra", "quiz-1", "q_001", "What is foo?", "sa", "easy", key)
        result = service.submit_and_score_answer("q_001", "foo and bar")
        assert result.passed is True
        assert result.raw_score == 1.0

    def test_submit_and_score_answer_failing(self, service) -> None:
        key = AnswerKey(required_keywords=["foo", "bar", "baz"])
        service.create_quiz_item("algebra", "quiz-1", "q_001", "Q?", "sa", "easy", key)
        result = service.submit_and_score_answer("q_001", "only foo")
        assert result.passed is False
        assert "bar" in result.missing_keywords
        assert "baz" in result.missing_keywords

    def test_submit_and_score_answer_missing_key_raises(self, service) -> None:
        with pytest.raises(ValueError, match="No answer key found"):
            service.submit_and_score_answer("nonexistent", "answer")

    def test_submit_and_score_tracks_attempt_number(self, service) -> None:
        key = AnswerKey(required_keywords=["x"])
        service.create_quiz_item("algebra", "quiz-1", "q_001", "Q?", "sa", "easy", key)
        service.submit_and_score_answer("q_001", "x")
        service.submit_and_score_answer("q_001", "x")
        service.submit_and_score_answer("q_001", "x")
        # The events should record attempt numbers 1, 2, 3
        events = service._event_store.read_all()
        submitted = [e for e in events if hasattr(e, "attempt_number")]
        assert len(submitted) == 3
        assert submitted[0].attempt_number == 1
        assert submitted[1].attempt_number == 2
        assert submitted[2].attempt_number == 3


class TestProfileLifecycle:
    """Tests for profile delta proposal and approval gate."""

    def test_propose_and_approve_delta(self, service) -> None:
        delta_id = service.propose_profile_delta(
            evidence=["quiz results"],
            proposed_changes={"learning_style": "visual"},
        )
        profile = service.get_learner_profile()
        assert len(profile.pending_deltas) == 1
        assert profile.approved_traits == {}

        service.approve_profile_delta(delta_id)
        profile = service.get_learner_profile()
        assert profile.approved_traits == {"learning_style": "visual"}
        assert profile.pending_deltas == []

    def test_approval_gate_leak_proof(self, service) -> None:
        """Prove that proposing a delta does NOT merge into approved_traits."""
        service.propose_profile_delta(
            evidence=["test"],
            proposed_changes={"pace": "fast"},
        )
        profile = service.get_learner_profile()
        assert "pace" not in profile.approved_traits
        assert len(profile.pending_deltas) == 1

    def test_multiple_deltas_independent_approval(self, service) -> None:
        id1 = service.propose_profile_delta(["e1"], {"trait_a": "x"})
        id2 = service.propose_profile_delta(["e2"], {"trait_b": "y"})
        service.approve_profile_delta(id1)

        profile = service.get_learner_profile()
        assert profile.approved_traits == {"trait_a": "x"}
        assert len(profile.pending_deltas) == 1
        assert profile.pending_deltas[0].proposed_changes == {"trait_b": "y"}

    def test_get_learner_profile_empty(self, service) -> None:
        profile = service.get_learner_profile()
        assert profile.approved_traits == {}
        assert profile.pending_deltas == []
        assert profile.topics_studied == []

    def test_topics_studied_tracked(self, service) -> None:
        service.start_topic("algebra")
        service.start_topic("geometry")
        profile = service.get_learner_profile()
        assert set(profile.topics_studied) == {"algebra", "geometry"}
