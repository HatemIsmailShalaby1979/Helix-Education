"""Tests for progress_engine module."""

import pytest

from learning_service import LearningService
from progress_engine import LearningPath, Milestone, MilestoneType, ProgressService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.scoring_engine import AnswerKey


@pytest.fixture
def progress_service(tmp_path) -> ProgressService:
    es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
    ks = SealedAnswerKeyStore()
    ls = LearningService(es, ks)
    return ProgressService(ls)


class TestProgressModels:
    """Tests for progress data models."""

    def test_milestone_creation(self) -> None:
        m = Milestone(
            milestone_type=MilestoneType.TOPIC_PASSED,
            topic="algebra",
            detail="passed at intermediate",
            timestamp="2026-01-01T00:00:00",
        )
        assert m.milestone_type == MilestoneType.TOPIC_PASSED
        assert m.topic == "algebra"

    def test_learning_path_creation(self) -> None:
        lp = LearningPath(
            topics=["algebra", "geometry", "calculus"],
            current_index=1,
            completed_topics=["algebra"],
            recommended_next="geometry",
        )
        assert lp.recommended_next == "geometry"
        assert lp.current_index == 1


class TestProgressService:
    """Tests for the Progress Service."""

    def test_get_milestones_empty(self, progress_service) -> None:
        assert progress_service.get_milestones() == []

    def test_get_milestones_after_events(self, progress_service) -> None:
        progress_service._learning.start_topic("algebra")
        progress_service._learning.pass_topic("algebra", "intermediate")
        progress_service._learning.branch_topic("algebra", "linear-equations", "deeper")

        milestones = progress_service.get_milestones()
        assert len(milestones) == 3
        types = [m.milestone_type for m in milestones]
        assert MilestoneType.TOPIC_STARTED in types
        assert MilestoneType.TOPIC_PASSED in types
        assert MilestoneType.BRANCH_EXPLORED in types

    def test_milestones_sorted_by_timestamp(self, progress_service) -> None:
        progress_service._learning.start_topic("algebra")
        progress_service._learning.branch_topic("algebra", "linear", "deeper")
        progress_service._learning.pass_topic("algebra", "intermediate")

        milestones = progress_service.get_milestones()
        for i in range(len(milestones) - 1):
            assert milestones[i].timestamp <= milestones[i + 1].timestamp

    def test_get_learning_path_empty(self, progress_service) -> None:
        lp = progress_service.get_learning_path([])
        assert lp.topics == []
        assert lp.recommended_next is None

    def test_get_learning_path_all_new(self, progress_service) -> None:
        lp = progress_service.get_learning_path(["algebra", "geometry"])
        assert lp.recommended_next == "algebra"
        assert lp.completed_topics == []

    def test_get_learning_path_some_completed(self, progress_service) -> None:
        progress_service._learning.start_topic("algebra")
        progress_service._learning.pass_topic("algebra", "intermediate")
        lp = progress_service.get_learning_path(["algebra", "geometry", "calculus"])
        assert "algebra" in lp.completed_topics
        assert lp.recommended_next == "geometry"

    def test_get_learning_path_all_completed(self, progress_service) -> None:
        progress_service._learning.start_topic("algebra")
        progress_service._learning.pass_topic("algebra", "intermediate")
        lp = progress_service.get_learning_path(["algebra"])
        assert lp.recommended_next is None

    def test_get_topic_summary(self, progress_service) -> None:
        progress_service._learning.start_topic("algebra")
        summary = progress_service.get_topic_summary("algebra")
        assert summary["topic"] == "algebra"
        assert summary["level"] == "beginner"
        assert summary["attempts_total"] == 0

    def test_get_topic_summary_after_quiz(self, progress_service) -> None:
        ls = progress_service._learning
        ls.start_topic("algebra")
        key = AnswerKey(required_keywords=["4"])
        ls.create_quiz_item("algebra", "quiz-1", "q1", "Q?", "mc", "easy", key)
        ls.submit_and_score_answer("q1", "4")
        ls.submit_and_score_answer("q1", "5")

        summary = progress_service.get_topic_summary("algebra")
        assert summary["attempts_total"] == 2
        assert summary["pass_count"] == 1
        assert summary["fail_count"] == 1
        assert summary["pass_rate"] == 0.5
