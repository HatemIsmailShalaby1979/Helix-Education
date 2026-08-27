"""Quiz Service — quiz and session management.

Coordinates with the Learning Service to create quiz items, manage
sessions, and aggregate results. Sessions are tracked in-memory with
event-sourced persistence through the Learning Service.
"""

import time
from datetime import UTC, datetime
from uuid import uuid4

from learning_service import LearningService
from observability.metrics import metrics
from state_core.scoring_engine import AnswerKey

from .quiz_models import Quiz, QuizItem, QuizSession, SessionResult


class QuizService:
    """Manages quiz collections and learner quiz sessions.

    Quiz metadata (quizzes, items) is rebuilt from the event log on init
    and survives restarts. Active sessions are stored in-memory only and
    are lost on process restart.

    Inputs:
        learning_service: A LearningService instance for event coordination.
    """

    def __init__(self, learning_service: LearningService) -> None:
        self._learning = learning_service
        self._quizzes: dict[str, Quiz] = {}
        self._sessions: dict[str, QuizSession] = {}
        self._rebuild_from_events()

    def _rebuild_from_events(self) -> None:
        from state_core.event_models import QuizCreatedEvent, QuizItemCreatedEvent

        events = self._learning._event_store.read_all()
        for e in events:
            if isinstance(e, QuizCreatedEvent):
                if e.quiz_id not in self._quizzes:
                    self._quizzes[e.quiz_id] = Quiz(
                        topic=e.topic,
                        quiz_id=e.quiz_id,
                        title=e.title,
                    )
            elif isinstance(e, QuizItemCreatedEvent):
                quiz = self._quizzes.get(e.quiz_id)
                if quiz is None:
                    quiz = Quiz(topic=e.topic, quiz_id=e.quiz_id)
                    self._quizzes[e.quiz_id] = quiz
                exists = any(i.quiz_item_id == e.quiz_item_id for i in quiz.items)
                if not exists:
                    quiz.items.append(
                        QuizItem(
                            quiz_item_id=e.quiz_item_id,
                            question=e.question if hasattr(e, "question") else "",
                            category=e.category,
                            difficulty=e.difficulty,
                        )
                    )

    # ── Quiz Management ──────────────────────────────────────────

    def create_quiz(
        self,
        topic: str,
        quiz_id: str,
        title: str | None = None,
    ) -> Quiz:
        """Create an empty quiz for a topic.

        Inputs:
            topic: The topic name.
            quiz_id: Unique identifier for the quiz.
            title: Optional human-readable title.
        Returns:
            The created Quiz instance.
        Raises:
            ValueError: If a quiz with this ID already exists.
        """
        if quiz_id in self._quizzes:
            raise ValueError(f"Quiz already exists: {quiz_id}")
        from state_core.event_models import QuizCreatedEvent

        event = QuizCreatedEvent.create(topic=topic, quiz_id=quiz_id, title=title)
        self._learning._event_store.append(event)
        quiz = Quiz(topic=topic, quiz_id=quiz_id, title=title)
        self._quizzes[quiz_id] = quiz
        return quiz

    def add_item(
        self,
        quiz_id: str,
        quiz_item_id: str,
        question: str,
        category: str,
        difficulty: str,
        answer_key: AnswerKey,
        required_keywords: list[str] | None = None,
    ) -> QuizItem:
        """Add an item to a quiz and persist via the Learning Service.

        Inputs:
            quiz_id: The quiz to add the item to.
            quiz_item_id: Unique identifier for the item.
            question: The question text.
            category: Question category.
            difficulty: Difficulty level.
            answer_key: The AnswerKey for scoring (sealed in the key store).
            required_keywords: Keywords that must appear in a correct answer.
                Stored on the QuizItem so the keyword-match score can be
                derived directly from the item (Directive 11). When None,
                defaults to the AnswerKey's required_keywords so the item
                is self-describing for keyword scoring.
        Returns:
            The created QuizItem.
        Raises:
            ValueError: If the quiz is not found.
        """
        quiz = self._quizzes.get(quiz_id)
        if quiz is None:
            raise ValueError(f"Quiz not found: {quiz_id}")

        # Persist through the Learning Service (appends to event log)
        self._learning.create_quiz_item(
            topic=quiz.topic,
            quiz_id=quiz_id,
            quiz_item_id=quiz_item_id,
            question=question,
            category=category,
            difficulty=difficulty,
            answer_key=answer_key,
        )

        if required_keywords is None:
            required_keywords = list(answer_key.required_keywords)

        item = QuizItem(
            quiz_item_id=quiz_item_id,
            question=question,
            category=category,
            difficulty=difficulty,
            required_keywords=required_keywords,
        )
        quiz.items.append(item)
        return item

    def get_quiz(self, quiz_id: str) -> Quiz | None:
        """Retrieve a quiz by ID.

        Inputs:
            quiz_id: The quiz identifier.
        Returns:
            The Quiz if found, None otherwise.
        """
        return self._quizzes.get(quiz_id)

    def list_quizzes_for_topic(self, topic: str) -> list[Quiz]:
        """List all quizzes for a given topic.

        Inputs:
            topic: The topic name.
        Returns:
            List of Quiz instances for this topic.
        """
        return [q for q in self._quizzes.values() if q.topic == topic]

    # ── Session Management ───────────────────────────────────────

    def start_session(self, quiz_id: str) -> str:
        """Start a new quiz session for a learner.

        Inputs:
            quiz_id: The quiz to start.
        Returns:
            The session_id string.
        Raises:
            ValueError: If the quiz is not found.
        """
        quiz = self._quizzes.get(quiz_id)
        if quiz is None:
            raise ValueError(f"Quiz not found: {quiz_id}")

        session_id = str(uuid4())
        session = QuizSession(
            session_id=session_id,
            quiz_id=quiz_id,
            topic=quiz.topic,
            started_at=datetime.now(UTC).isoformat(),
        )
        self._sessions[session_id] = session
        return session_id

    def answer_item(
        self,
        session_id: str,
        quiz_item_id: str,
        raw_answer: str,
    ) -> SessionResult:
        """Submit and score an answer within a session.

        Inputs:
            session_id: The session to answer within.
            quiz_item_id: The quiz item being answered.
            raw_answer: The learner's answer text.
        Returns:
            A SessionResult with score details.
        Raises:
            ValueError: If the session is not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        quiz = self._quizzes.get(session.quiz_id)
        question = ""
        if quiz:
            for item in quiz.items:
                if item.quiz_item_id == quiz_item_id:
                    question = item.question
                    break

        start_time = time.time()
        result = self._learning.submit_and_score_answer(
            quiz_item_id=quiz_item_id,
            raw_answer=raw_answer,
            question=question,
        )
        latency = time.time() - start_time

        metrics.increment_counter("quiz_answers_submitted")
        metrics.observe_histogram("quiz_scoring_latency_seconds", latency)
        if result.passed:
            metrics.increment_counter("quiz_answers_passed")

        sr = SessionResult(
            quiz_item_id=quiz_item_id,
            question=question,
            attempt_number=result.attempt_number,
            raw_score=result.raw_score,
            passed=result.passed,
            missing_keywords=result.missing_keywords,
            matched_keywords=result.matched_keywords,
        )
        session.results.append(sr)
        return sr

    def complete_session(self, session_id: str) -> QuizSession | None:
        """Mark a session as completed.

        Inputs:
            session_id: The session to complete.
        Returns:
            The completed QuizSession, or None if not found.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.completed_at = datetime.now(UTC).isoformat()
        return session

    def get_session(self, session_id: str) -> QuizSession | None:
        """Retrieve a session by ID.

        Inputs:
            session_id: The session identifier.
        Returns:
            The QuizSession if found, None otherwise.
        """
        return self._sessions.get(session_id)

    def get_session_summary(self, session_id: str) -> dict | None:
        """Get a summary of a completed session.

        Inputs:
            session_id: The session identifier.
        Returns:
            A dict with total_items, passed_count, failed_count,
            average_score, and pass_rate, or None if session not found.
        """
        session = self._sessions.get(session_id)
        if session is None or not session.results:
            return None

        total = len(session.results)
        passed = sum(1 for r in session.results if r.passed)
        failed = total - passed
        avg_score = sum(r.raw_score for r in session.results) / total if total > 0 else 0.0

        return {
            "session_id": session_id,
            "quiz_id": session.quiz_id,
            "topic": session.topic,
            "total_items": total,
            "passed_count": passed,
            "failed_count": failed,
            "average_score": round(avg_score, 2),
            "pass_rate": round(passed / total, 2) if total > 0 else 0.0,
            "completed_at": session.completed_at,
        }
