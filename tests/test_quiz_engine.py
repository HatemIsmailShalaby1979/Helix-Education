"""Tests for quiz_engine module."""

import pytest

from learning_service import LearningService
from quiz_engine import Quiz, QuizItem, QuizService, QuizSession, SessionResult
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.scoring_engine import AnswerKey


@pytest.fixture
def quiz_service(tmp_path) -> QuizService:
    """Provide a QuizService backed by temp EventStore."""
    es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
    ks = SealedAnswerKeyStore()
    ls = LearningService(es, ks)
    return QuizService(ls)


class TestQuizModels:
    """Tests for quiz data models."""

    def test_quiz_item_creation(self) -> None:
        item = QuizItem(
            quiz_item_id="qi_1",
            question="What is 2+2?",
            category="math",
            difficulty="easy",
        )
        assert item.quiz_item_id == "qi_1"
        assert item.question == "What is 2+2?"

    def test_quiz_creation(self) -> None:
        item = QuizItem(quiz_item_id="qi_1", question="Q1", category="mc", difficulty="easy")
        quiz = Quiz(topic="algebra", quiz_id="q_001", items=[item], title="Algebra Quiz")
        assert quiz.topic == "algebra"
        assert quiz.quiz_id == "q_001"
        assert quiz.title == "Algebra Quiz"
        assert len(quiz.items) == 1

    def test_session_result_creation(self) -> None:
        sr = SessionResult(
            quiz_item_id="qi_1",
            question="Q1",
            attempt_number=1,
            raw_score=0.8,
            passed=True,
        )
        assert sr.passed is True
        assert sr.raw_score == 0.8

    def test_quiz_session_creation(self) -> None:
        session = QuizSession(
            session_id="s_001",
            quiz_id="q_001",
            topic="algebra",
        )
        assert session.session_id == "s_001"
        assert session.results == []


class TestQuizService:
    """Tests for the Quiz Service."""

    def test_create_quiz(self, quiz_service) -> None:
        quiz = quiz_service.create_quiz("algebra", "q_001", "Algebra Quiz")
        assert quiz.quiz_id == "q_001"
        assert quiz.topic == "algebra"
        assert quiz.title == "Algebra Quiz"

    def test_create_duplicate_quiz_raises(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        with pytest.raises(ValueError, match="already exists"):
            quiz_service.create_quiz("geometry", "q_001")

    def test_add_item(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        key = AnswerKey(required_keywords=["4"])
        item = quiz_service.add_item(
            quiz_id="q_001",
            quiz_item_id="qi_001",
            question="What is 2+2?",
            category="math",
            difficulty="easy",
            answer_key=key,
        )
        assert item.quiz_item_id == "qi_001"
        assert item.question == "What is 2+2?"

        # Verify it's in the quiz
        quiz = quiz_service.get_quiz("q_001")
        assert quiz is not None
        assert len(quiz.items) == 1

    def test_add_item_no_quiz_raises(self, quiz_service) -> None:
        key = AnswerKey(required_keywords=["x"])
        with pytest.raises(ValueError, match="Quiz not found"):
            quiz_service.add_item("nonexistent", "qi_1", "Q?", "mc", "easy", key)

    def test_add_item_creates_event(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        key = AnswerKey(required_keywords=["4"])
        quiz_service.add_item("q_001", "qi_001", "What is 2+2?", "math", "easy", key)

        events = quiz_service._learning._event_store.read_all()
        quiz_events = [e for e in events if hasattr(e, "quiz_item_id")]
        assert len(quiz_events) == 1
        assert quiz_events[0].quiz_item_id == "qi_001"

    def test_get_quiz_not_found(self, quiz_service) -> None:
        assert quiz_service.get_quiz("nonexistent") is None

    def test_list_quizzes_for_topic(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        quiz_service.create_quiz("algebra", "q_002")
        quiz_service.create_quiz("geometry", "q_003")
        algebra_quizzes = quiz_service.list_quizzes_for_topic("algebra")
        assert len(algebra_quizzes) == 2
        geometry_quizzes = quiz_service.list_quizzes_for_topic("geometry")
        assert len(geometry_quizzes) == 1

    def test_start_session(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        session_id = quiz_service.start_session("q_001")
        assert len(session_id) > 0
        session = quiz_service.get_session(session_id)
        assert session is not None
        assert session.quiz_id == "q_001"
        assert session.topic == "algebra"

    def test_start_session_no_quiz_raises(self, quiz_service) -> None:
        with pytest.raises(ValueError, match="Quiz not found"):
            quiz_service.start_session("nonexistent")

    def test_answer_item_in_session(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        key = AnswerKey(required_keywords=["4"])
        quiz_service.add_item("q_001", "qi_001", "What is 2+2?", "math", "easy", key)

        session_id = quiz_service.start_session("q_001")
        result = quiz_service.answer_item(session_id, "qi_001", "4")
        assert result.passed is True
        assert result.quiz_item_id == "qi_001"
        assert result.question == "What is 2+2?"

    def test_answer_item_wrong_answer(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        key = AnswerKey(required_keywords=["4", "four"])
        quiz_service.add_item("q_001", "qi_001", "What is 2+2?", "math", "easy", key)

        session_id = quiz_service.start_session("q_001")
        result = quiz_service.answer_item(session_id, "qi_001", "5")
        assert result.passed is False
        assert result.raw_score == 0.0

    def test_answer_item_no_session_raises(self, quiz_service) -> None:
        with pytest.raises(ValueError, match="Session not found"):
            quiz_service.answer_item("bad_session", "qi_001", "answer")

    def test_complete_session(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        session_id = quiz_service.start_session("q_001")
        completed = quiz_service.complete_session(session_id)
        assert completed is not None
        assert completed.completed_at is not None
        assert completed.session_id == session_id

    def test_complete_nonexistent_session(self, quiz_service) -> None:
        assert quiz_service.complete_session("nonexistent") is None

    def test_get_session_summary(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        key1 = AnswerKey(required_keywords=["4"])
        key2 = AnswerKey(required_keywords=["Paris"])
        quiz_service.add_item("q_001", "qi_001", "2+2?", "math", "easy", key1)
        quiz_service.add_item("q_001", "qi_002", "Capital of France?", "geo", "easy", key2)

        session_id = quiz_service.start_session("q_001")
        quiz_service.answer_item(session_id, "qi_001", "4")
        quiz_service.answer_item(session_id, "qi_002", "Paris")
        quiz_service.complete_session(session_id)

        summary = quiz_service.get_session_summary(session_id)
        assert summary is not None
        assert summary["total_items"] == 2
        assert summary["passed_count"] == 2
        assert summary["average_score"] == 1.0
        assert summary["pass_rate"] == 1.0

    def test_get_session_summary_with_failures(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        key1 = AnswerKey(required_keywords=["4"])
        key2 = AnswerKey(required_keywords=["Paris"])
        quiz_service.add_item("q_001", "qi_001", "2+2?", "math", "easy", key1)
        quiz_service.add_item("q_001", "qi_002", "Capital of France?", "geo", "easy", key2)

        session_id = quiz_service.start_session("q_001")
        quiz_service.answer_item(session_id, "qi_001", "4")
        quiz_service.answer_item(session_id, "qi_002", "London")
        quiz_service.complete_session(session_id)

        summary = quiz_service.get_session_summary(session_id)
        assert summary is not None
        assert summary["passed_count"] == 1
        assert summary["failed_count"] == 1
        assert summary["average_score"] == 0.5

    def test_get_session_summary_no_results(self, quiz_service) -> None:
        quiz_service.create_quiz("algebra", "q_001")
        session_id = quiz_service.start_session("q_001")
        assert quiz_service.get_session_summary(session_id) is None

    def test_get_session_summary_nonexistent(self, quiz_service) -> None:
        assert quiz_service.get_session_summary("bad") is None

    # ── Fix 1: attempt_number divergence across sessions ─────────────

    def test_attempt_number_increases_across_sessions(self, quiz_service) -> None:
        """A quiz retaken in a second session produces strictly increasing
        attempt_number across sessions for the same quiz_item_id (Fix 1)."""
        quiz_service.create_quiz("algebra", "q_001")
        key = AnswerKey(required_keywords=["4"])
        quiz_service.add_item("q_001", "qi_001", "What is 2+2?", "math", "easy", key)

        # Session 1: first attempt
        session1 = quiz_service.start_session("q_001")
        result1 = quiz_service.answer_item(session1, "qi_001", "4")
        assert result1.attempt_number == 1
        quiz_service.complete_session(session1)

        # Session 2: second attempt (should be attempt_number=2, not 1)
        session2 = quiz_service.start_session("q_001")
        result2 = quiz_service.answer_item(session2, "qi_001", "4")
        assert result2.attempt_number == 2
        quiz_service.complete_session(session2)

        # Session 3: third attempt
        session3 = quiz_service.start_session("q_001")
        result3 = quiz_service.answer_item(session3, "qi_001", "4")
        assert result3.attempt_number == 3

    # ── Fix 2: missing_keywords and matched_keywords in SessionResult ──

    def test_session_result_includes_keyword_details(self, quiz_service) -> None:
        """SessionResult.missing_keywords and matched_keywords are non-empty
        and correct after a partially-wrong answer (Fix 2)."""
        quiz_service.create_quiz("algebra", "q_001")
        key = AnswerKey(required_keywords=["foo", "bar", "baz"])
        quiz_service.add_item("q_001", "qi_001", "Q?", "sa", "easy", key)

        session_id = quiz_service.start_session("q_001")
        # Answer with only "foo" and "bar" — missing "baz"
        result = quiz_service.answer_item(session_id, "qi_001", "foo and bar")

        assert result.missing_keywords == ["baz"]
        assert result.matched_keywords == ["foo", "bar"]
        assert result.raw_score == pytest.approx(2 / 3)
        assert result.passed is True  # 0.66 >= 0.6

    def test_session_result_keywords_empty_on_perfect_answer(self, quiz_service) -> None:
        """SessionResult.missing_keywords is empty and matched_keywords has all
        keywords on a perfect answer."""
        quiz_service.create_quiz("algebra", "q_001")
        key = AnswerKey(required_keywords=["foo", "bar"])
        quiz_service.add_item("q_001", "qi_001", "Q?", "sa", "easy", key)

        session_id = quiz_service.start_session("q_001")
        result = quiz_service.answer_item(session_id, "qi_001", "foo and bar")

        assert result.missing_keywords == []
        assert result.matched_keywords == ["foo", "bar"]
        assert result.raw_score == 1.0
        assert result.passed is True
