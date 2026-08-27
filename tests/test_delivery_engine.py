"""Tests for delivery_engine module."""

import pytest

from delivery_engine import FeedbackLevel, FeedbackMessage, FeedbackService, SessionLog
from learning_service import LearningService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.scoring_engine import ScoreResult


@pytest.fixture
def feedback_service(tmp_path) -> FeedbackService:
    es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
    ks = SealedAnswerKeyStore()
    ls = LearningService(es, ks)
    return FeedbackService(ls)


class TestDeliveryModels:
    """Tests for delivery data models."""

    def test_feedback_message_creation(self) -> None:
        msg = FeedbackMessage(
            level=FeedbackLevel.SUCCESS,
            title="Correct!",
            body="Well done.",
            details=["Keyword 'foo' matched"],
        )
        assert msg.level == FeedbackLevel.SUCCESS
        assert msg.title == "Correct!"
        assert msg.details == ["Keyword 'foo' matched"]

    def test_session_log_creation(self) -> None:
        log = SessionLog(session_id="s_001", started_at="2026-01-01T00:00:00")
        assert log.session_id == "s_001"
        assert log.entries == []


class TestFeedbackService:
    """Tests for the Feedback Service."""

    def test_score_feedback_passing(self, feedback_service) -> None:
        result = ScoreResult(
            raw_score=0.8,
            passed=True,
            missing_keywords=[],
            matched_keywords=["foo", "bar"],
        )
        msg = feedback_service.score_feedback(result)
        assert msg.level == FeedbackLevel.SUCCESS
        assert "Correct!" in msg.title

    def test_score_feedback_failing(self, feedback_service) -> None:
        result = ScoreResult(
            raw_score=0.3,
            passed=False,
            missing_keywords=["bar", "baz"],
            matched_keywords=["foo"],
        )
        msg = feedback_service.score_feedback(result)
        assert msg.level == FeedbackLevel.WARNING
        assert "Needs Improvement" in msg.title
        assert any("bar" in d for d in msg.details)

    def test_topic_progress_feedback_not_started(self, feedback_service) -> None:
        msg = feedback_service.topic_progress_feedback("algebra")
        assert msg.level == FeedbackLevel.INFO
        assert "Not Started" in msg.title

    def test_topic_progress_feedback_in_progress(self, feedback_service) -> None:
        feedback_service._learning.start_topic("algebra")
        msg = feedback_service.topic_progress_feedback("algebra")
        assert "In Progress" in msg.title

    def test_topic_progress_feedback_passed(self, feedback_service) -> None:
        feedback_service._learning.start_topic("algebra")
        feedback_service._learning.pass_topic("algebra", "intermediate")
        msg = feedback_service.topic_progress_feedback("algebra")
        assert "Topic Passed" in msg.title
        assert msg.level == FeedbackLevel.SUCCESS

    def test_session_started(self, feedback_service) -> None:
        log = feedback_service.session_started("s_001")
        assert log.session_id == "s_001"
        assert log.started_at != ""

    def test_session_log_entry(self, feedback_service) -> None:
        log = feedback_service.session_started("s_001")
        log2 = feedback_service.session_log_entry(log, "Started quiz")
        assert len(log2.entries) == 1
        assert "Started quiz" in log2.entries[0]
        # Original is unchanged (immutable pattern)
        assert len(log.entries) == 0

    def test_pass_rate_zero_attempts(self) -> None:
        assert FeedbackService._pass_rate(0, 0) == 0.0

    def test_pass_rate_calculation(self) -> None:
        assert FeedbackService._pass_rate(3, 4) == 0.75
