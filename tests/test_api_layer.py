"""Tests for api_layer module."""

import pytest

from api_layer import (
    AnswerFeedbackResponse,
    CreateQuizItemRequest,
    LearnerProfileResponse,
    Router,
    StartTopicRequest,
    SubmitAnswerRequest,
    TopicStateResponse,
)
from delivery_engine import FeedbackService
from learning_service import LearningService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig


@pytest.fixture
def router(tmp_path) -> Router:
    es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
    ks = SealedAnswerKeyStore()
    ls = LearningService(es, ks)
    fs = FeedbackService(ls)
    return Router(ls, fs)


class TestApiModels:
    """Tests for API request/response models."""

    def test_start_topic_request(self) -> None:
        req = StartTopicRequest(topic="algebra", requested_level="intermediate")
        assert req.topic == "algebra"
        assert req.requested_level == "intermediate"

    def test_submit_answer_request(self) -> None:
        req = SubmitAnswerRequest(quiz_item_id="q1", raw_answer="42")
        assert req.quiz_item_id == "q1"
        assert req.raw_answer == "42"

    def test_create_quiz_item_request(self) -> None:
        req = CreateQuizItemRequest(
            topic="algebra",
            quiz_item_id="q1",
            question="Q?",
            category="mc",
            difficulty="easy",
            required_keywords=["4"],
        )
        assert req.topic == "algebra"
        assert req.question == "Q?"
        assert req.required_keywords == ["4"]

    def test_topic_state_response(self) -> None:
        resp = TopicStateResponse(
            topic="algebra",
            current_level="beginner",
            attempts_total=0,
            pass_count=0,
            fail_count=0,
            is_passed=False,
            branch_children=[],
            last_activity_timestamp="",
        )
        assert resp.topic == "algebra"
        assert resp.current_level == "beginner"

    def test_learner_profile_response(self) -> None:
        resp = LearnerProfileResponse(
            approved_traits={},
            pending_delta_count=0,
            topics_studied=[],
        )
        assert resp.pending_delta_count == 0

    def test_answer_feedback_response(self) -> None:
        resp = AnswerFeedbackResponse(
            raw_score=0.8,
            passed=True,
            missing_keywords=[],
            matched_keywords=["foo"],
            message="Correct!",
        )
        assert resp.passed is True
        assert resp.raw_score == 0.8


class TestRouter:
    """Tests for the API Router handlers."""

    def test_handle_start_topic(self, router) -> None:
        req = StartTopicRequest(topic="algebra")
        resp = router.handle_start_topic(req)
        assert resp.topic == "algebra"
        assert resp.current_level == "beginner"

    def test_handle_get_topic(self, router) -> None:
        router.handle_start_topic(StartTopicRequest(topic="algebra"))
        resp = router.handle_get_topic("algebra")
        assert resp is not None
        assert resp.topic == "algebra"

    def test_handle_get_topic_not_found(self, router) -> None:
        resp = router.handle_get_topic("nonexistent")
        assert resp is not None  # TopicState is always returned for any topic

    def test_handle_get_profile(self, router) -> None:
        resp = router.handle_get_profile()
        assert resp.approved_traits == {}
        assert resp.topics_studied == []

    def test_handle_submit_answer(self, router) -> None:
        # Create a quiz item first
        create_req = CreateQuizItemRequest(
            topic="algebra",
            quiz_item_id="q1",
            question="What is 2+2?",
            category="mc",
            difficulty="easy",
            required_keywords=["4"],
        )
        router.handle_create_quiz_item(create_req)

        # Submit answer
        answer_req = SubmitAnswerRequest(quiz_item_id="q1", raw_answer="4")
        resp = router.handle_submit_answer(answer_req)
        assert resp.passed is True
        assert resp.raw_score == 1.0
        assert "Correct!" in resp.message

    def test_handle_submit_answer_failing(self, router) -> None:
        create_req = CreateQuizItemRequest(
            topic="algebra",
            quiz_item_id="q1",
            question="What is 2+2?",
            category="mc",
            difficulty="easy",
            required_keywords=["4", "four"],
        )
        router.handle_create_quiz_item(create_req)
        answer_req = SubmitAnswerRequest(quiz_item_id="q1", raw_answer="5")
        resp = router.handle_submit_answer(answer_req)
        assert resp.passed is False
        assert "Needs Improvement" in resp.message

    def test_handle_create_quiz_item(self, router) -> None:
        req = CreateQuizItemRequest(
            topic="algebra",
            quiz_item_id="q1",
            question="Q?",
            category="mc",
            difficulty="easy",
            required_keywords=["4"],
        )
        resp = router.handle_create_quiz_item(req)
        assert resp["quiz_item_id"] == "q1"
        assert resp["status"] == "created"

    def test_handle_approve_delta(self, router) -> None:
        delta_id = router._learning.propose_profile_delta(
            ["evidence"],
            {"trait": "value"},
        )
        resp = router.handle_approve_delta(delta_id)
        assert resp["delta_event_id"] == delta_id
        assert resp["status"] == "approved"
        profile = router._learning.get_learner_profile()
        assert profile.approved_traits == {"trait": "value"}
