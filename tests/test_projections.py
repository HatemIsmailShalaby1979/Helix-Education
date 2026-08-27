"""Tests for state_core.projections."""

from state_core.event_models import (
    AnswerScoredEvent,
    AnswerSubmittedEvent,
    Event,
    ProfileDeltaApprovedEvent,
    ProfileDeltaProposedEvent,
    QuizItemCreatedEvent,
    TopicBranchedEvent,
    TopicPassedEvent,
    TopicStartedEvent,
)
from state_core.projections import (
    project_learner_profile,
    project_topic_state,
)


def make_quiz_flow(topic: str, quiz_id: str, scores: list[float]):
    """Helper: build events for a quiz flow with given scores (0.0-1.0)."""
    events: list[Event] = []
    events.append(
        QuizItemCreatedEvent.create(
            topic=topic,
            quiz_id=quiz_id,
            quiz_item_id=quiz_id,
            question="Q?",
            category="mc",
            difficulty="easy",
            answer_key_hash="abc",
        )
    )
    for i, score in enumerate(scores, start=1):
        passed = score >= 0.6
        events.append(
            AnswerSubmittedEvent.create(
                quiz_item_id=quiz_id,
                raw_answer="answer",
                attempt_number=i,
            )
        )
        events.append(
            AnswerScoredEvent.create(
                quiz_item_id=quiz_id,
                raw_score=score,
                passed=passed,
                scoring_method="keyword",
            )
        )
    return events


class TestProjectTopicState:
    """Tests for project_topic_state."""

    def test_empty_events(self) -> None:
        state = project_topic_state([], "algebra")
        assert state.topic == "algebra"
        assert state.attempts_total == 0
        assert state.pass_count == 0
        assert state.fail_count == 0
        assert state.is_passed is False
        assert state.branch_children == []
        assert state.last_activity_timestamp == ""

    def test_topic_with_no_quiz_events(self) -> None:
        events = [TopicStartedEvent.create(topic="algebra")]
        state = project_topic_state(events, "algebra")
        assert state.attempts_total == 0
        assert state.is_passed is False

    def test_topic_with_passing_and_failing(self) -> None:
        events = make_quiz_flow("algebra", "q1", [0.8, 0.3, 0.9])
        state = project_topic_state(events, "algebra")
        assert state.attempts_total == 3
        assert state.pass_count == 2
        assert state.fail_count == 1
        assert state.is_passed is False

    def test_topic_officially_passed(self) -> None:
        events = make_quiz_flow("algebra", "q1", [0.8, 0.9])
        events.append(
            TopicPassedEvent.create(
                topic="algebra",
                final_level="intermediate",
                attempts_total=2,
            )
        )
        state = project_topic_state(events, "algebra")
        assert state.is_passed is True
        assert state.current_level == "intermediate"
        assert state.attempts_total == 2

    def test_branch_children(self) -> None:
        events = [
            TopicStartedEvent.create(topic="algebra"),
            TopicBranchedEvent.create(
                parent_topic="algebra",
                child_topic="linear-equations",
                reason="deeper study",
            ),
            TopicBranchedEvent.create(
                parent_topic="algebra",
                child_topic="quadratics",
                reason="deeper study",
            ),
        ]
        state = project_topic_state(events, "algebra")
        assert state.branch_children == ["linear-equations", "quadratics"]

    def test_recent_attempts(self) -> None:
        events = make_quiz_flow("algebra", "q1", [0.9, 0.2, 0.8, 0.95])
        state = project_topic_state(events, "algebra")
        assert len(state.recent_attempts) == 3
        assert state.recent_attempts == [True, True, False]

    def test_last_activity_timestamp(self) -> None:
        events = [TopicStartedEvent.create(topic="algebra")]
        state = project_topic_state(events, "algebra")
        assert state.last_activity_timestamp != ""

    def test_unrelated_topic_quiz_not_counted(self) -> None:
        events = make_quiz_flow("geometry", "q1", [0.8, 0.9])
        events += make_quiz_flow("algebra", "q2", [0.4])
        state = project_topic_state(events, "algebra")
        assert state.attempts_total == 1
        assert state.fail_count == 1


class TestProjectLearnerProfile:
    """Tests for project_learner_profile."""

    def test_empty_events(self) -> None:
        profile = project_learner_profile([])
        assert profile.approved_traits == {}
        assert profile.pending_deltas == []
        assert profile.topics_studied == []

    def test_pending_delta_not_merged(self) -> None:
        events = [
            ProfileDeltaProposedEvent.create(
                evidence=["quiz pass"],
                proposed_changes={"learning_style": "visual"},
            ),
        ]
        profile = project_learner_profile(events)
        assert profile.approved_traits == {}
        assert len(profile.pending_deltas) == 1
        assert profile.pending_deltas[0].proposed_changes == {"learning_style": "visual"}

    def test_approved_delta_merged(self) -> None:
        proposed = ProfileDeltaProposedEvent.create(
            evidence=["quiz pass"],
            proposed_changes={"learning_style": "visual"},
        )
        approved = ProfileDeltaApprovedEvent.create(
            delta_event_id=proposed.event_id,
        )
        events = [proposed, approved]
        profile = project_learner_profile(events)
        assert profile.approved_traits == {"learning_style": "visual"}
        assert profile.pending_deltas == []

    def test_approved_delta_merged_reverse_order(self) -> None:
        approved = ProfileDeltaApprovedEvent.create(
            delta_event_id="future_proposed_id",
        )
        events = [
            ProfileDeltaProposedEvent(
                event_id="future_proposed_id",
                timestamp="2026-01-01T00:00:00",
                evidence=["x"],
                proposed_changes={"style": "auditory"},
            ),
            approved,
        ]
        profile = project_learner_profile(events)
        assert profile.approved_traits == {"style": "auditory"}

    def test_leak_proof_unapproved_delta_never_merges(self) -> None:
        traits = {"learning_style": "visual", "pace": "slow"}
        proposed = ProfileDeltaProposedEvent(
            event_id="delta_001",
            timestamp="2026-01-01T00:00:00",
            evidence=["quiz_results"],
            proposed_changes=traits,
        )
        events_order_1 = [proposed]
        events_order_2 = [proposed, TopicStartedEvent.create(topic="unrelated")]
        events_order_3 = [
            TopicStartedEvent.create(topic="other"),
            proposed,
            AnswerScoredEvent.create(
                quiz_item_id="q1",
                raw_score=0.9,
                passed=True,
                scoring_method="keyword",
            ),
        ]

        for events in [events_order_1, events_order_2, events_order_3]:
            profile = project_learner_profile(events)
            for key in traits:
                assert key not in profile.approved_traits, (
                    f"Leak detected: {key} appeared in approved_traits without an ApprovalEvent (order variant)"
                )
            assert len(profile.pending_deltas) == 1
            assert profile.pending_deltas[0].event_id == "delta_001"

    def test_multiple_approved_deltas_merged(self) -> None:
        proposed_1 = ProfileDeltaProposedEvent(
            event_id="d1",
            timestamp="t1",
            evidence=["e1"],
            proposed_changes={"a": 1},
        )
        proposed_2 = ProfileDeltaProposedEvent(
            event_id="d2",
            timestamp="t2",
            evidence=["e2"],
            proposed_changes={"b": 2},
        )
        approved = ProfileDeltaApprovedEvent.create(delta_event_id="d1")
        events = [proposed_1, proposed_2, approved]
        profile = project_learner_profile(events)
        assert profile.approved_traits == {"a": 1}
        assert len(profile.pending_deltas) == 1
        assert profile.pending_deltas[0].event_id == "d2"

    def test_topics_studied(self) -> None:
        events = [
            TopicStartedEvent.create(topic="algebra"),
            TopicPassedEvent.create(topic="geometry", final_level="beginner", attempts_total=1),
            TopicBranchedEvent.create(parent_topic="algebra", child_topic="linear", reason="x"),
        ]
        profile = project_learner_profile(events)
        assert set(profile.topics_studied) == {"algebra", "geometry", "linear"}

    def test_duplicate_topics_deduped(self) -> None:
        events = [
            TopicStartedEvent.create(topic="algebra"),
            TopicStartedEvent.create(topic="algebra"),
        ]
        profile = project_learner_profile(events)
        assert profile.topics_studied == ["algebra"]
