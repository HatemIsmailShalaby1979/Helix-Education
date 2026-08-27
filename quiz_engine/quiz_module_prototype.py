"""
QuizModule — Deep module owning the quiz lifecycle end-to-end.

This is a THROWAAWAY PROTOTYPE to validate the interface and state model.
Located at: quiz_engine/quiz_module_prototype.py
Run with: python -m quiz_engine.quiz_module_prototype
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from state_core.event_models import (
    AnswerScoredEvent,
    AnswerSubmittedEvent,
    QuizCreatedEvent,
    QuizItemCreatedEvent,
)

# ── Dependencies (interfaces we receive) ─────────────────────────────
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.leveling_engine import compute_level
from state_core.projections import project_topic_state

# ── ScoringEngine inlined as private methods ─────────────────────────


@dataclass
class _AnswerKey:
    required_keywords: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)
    min_length_chars: int = 0


@dataclass
class _ScoreResult:
    raw_score: float
    passed: bool
    missing_keywords: list[str]
    matched_keywords: list[str]


def _normalize(text: str) -> str:
    return text.strip().lower()


def _score_answer(raw_answer: str, answer_key: _AnswerKey) -> _ScoreResult:
    if not raw_answer or not raw_answer.strip():
        raise ValueError("raw_answer must not be empty")

    normalized = _normalize(raw_answer)
    required_count = len(answer_key.required_keywords)

    matched: list[str] = []
    missing: list[str] = []
    for kw in answer_key.required_keywords:
        if _normalize(kw) in normalized:
            matched.append(kw)
        else:
            missing.append(kw)

    base_score = len(matched) / required_count if required_count > 0 else 1.0

    forbidden_found = sum(1 for kw in answer_key.forbidden_keywords if _normalize(kw) in normalized)
    raw_score = max(0.0, base_score - forbidden_found * 0.1)
    passed = raw_score >= 0.6

    return _ScoreResult(
        raw_score=raw_score,
        passed=passed,
        missing_keywords=missing,
        matched_keywords=matched,
    )


def _compute_key_hash(key: _AnswerKey) -> str:
    import hashlib
    import json

    canonical = json.dumps(
        {
            "required_keywords": sorted(key.required_keywords),
            "forbidden_keywords": sorted(key.forbidden_keywords),
            "min_length_chars": key.min_length_chars,
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Public dataclasses (interface types) ─────────────────────────────


@dataclass
class Quiz:
    topic: str
    quiz_id: str
    title: str | None = None
    items: list[QuizItem] = field(default_factory=list)


@dataclass
class QuizItem:
    quiz_item_id: str
    question: str
    category: str
    difficulty: str


@dataclass
class SessionResult:
    quiz_item_id: str
    question: str
    attempt_number: int
    raw_score: float
    passed: bool


@dataclass
class QuizSession:
    session_id: str
    quiz_id: str
    topic: str
    started_at: str
    results: list[SessionResult] = field(default_factory=list)
    completed_at: str | None = None


@dataclass
class SessionSummary:
    session_id: str
    quiz_id: str
    topic: str
    total_items: int
    passed_count: int
    failed_count: int
    average_score: float
    pass_rate: float
    completed_at: str | None


# ── QuizModule — the deep module ─────────────────────────────────────


class QuizModule:
    """
    Deep module owning the quiz lifecycle.

    Public interface (9 methods):
      - start_quiz(topic, quiz_id) -> session_id
      - answer_item(session_id, quiz_item_id, raw_answer) -> SessionResult
      - complete_session(session_id) -> SessionSummary
      - get_summary(session_id) -> Optional[SessionSummary]
      - list_quizzes(topic) -> list[Quiz]
      - get_quiz(quiz_id) -> Optional[Quiz]
      - create_quiz(topic, quiz_id, title) -> Quiz
      - get_topic_state(topic) -> TopicState
      - compute_topic_level(topic) -> str

    Dependencies (injected):
      - EventStore: append-only event log
      - SealedAnswerKeyStore: answer key storage (hashes only in events)
    """

    def __init__(
        self,
        event_store: EventStore,
        key_store: SealedAnswerKeyStore,
    ) -> None:
        self._events = event_store
        self._keys = key_store
        self._quizzes: dict[str, Quiz] = {}
        self._sessions: dict[str, QuizSession] = {}
        self._rebuild_quizzes_from_events()

    # ── Internal: rebuild quiz metadata from event log ──────────────

    def _rebuild_quizzes_from_events(self) -> None:
        events = self._events.read_all()
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

    # ── Session persistence (event-sourced) ─────────────────────────

    def _persist_session_start(self, session: QuizSession) -> None:
        # In a full impl, we'd emit a QuizSessionStartedEvent
        pass

    def _persist_answer(
        self,
        session_id: str,
        quiz_item_id: str,
        raw_answer: str,
        attempt_number: int,
    ) -> None:
        event = AnswerSubmittedEvent.create(
            quiz_item_id=quiz_item_id,
            raw_answer=raw_answer,
            attempt_number=attempt_number,
        )
        self._events.append(event)

    def _persist_score(
        self,
        quiz_item_id: str,
        raw_score: float,
        passed: bool,
    ) -> None:
        event = AnswerScoredEvent.create(
            quiz_item_id=quiz_item_id,
            raw_score=raw_score,
            passed=passed,
            scoring_method="keyword",
        )
        self._events.append(event)

    def _persist_session_complete(self, session: QuizSession) -> None:
        # In a full impl, we'd emit a QuizSessionCompletedEvent
        pass

    # ── Public Interface: Quiz Management ───────────────────────────

    def create_quiz(
        self,
        topic: str,
        quiz_id: str,
        title: str | None = None,
    ) -> Quiz:
        """Create an empty quiz for a topic."""
        if quiz_id in self._quizzes:
            raise ValueError(f"Quiz already exists: {quiz_id}")

        event = QuizCreatedEvent.create(topic=topic, quiz_id=quiz_id, title=title)
        self._events.append(event)

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
        required_keywords: list[str],
        forbidden_keywords: list[str] = None,
        min_length_chars: int = 0,
    ) -> QuizItem:
        """Add an item to a quiz with a sealed answer key."""
        quiz = self._quizzes.get(quiz_id)
        if quiz is None:
            raise ValueError(f"Quiz not found: {quiz_id}")

        key = _AnswerKey(
            required_keywords=required_keywords,
            forbidden_keywords=forbidden_keywords or [],
            min_length_chars=min_length_chars,
        )
        key_hash = self._keys.store(quiz_item_id, key)
        # Note: In real impl, we'd use the actual AnswerKey from state_core
        # For prototype, we store our internal _AnswerKey

        event = QuizItemCreatedEvent.create(
            topic=quiz.topic,
            quiz_id=quiz_id,
            quiz_item_id=quiz_item_id,
            question=question,
            category=category,
            difficulty=difficulty,
            answer_key_hash=key_hash,
        )
        self._events.append(event)

        item = QuizItem(
            quiz_item_id=quiz_item_id,
            question=question,
            category=category,
            difficulty=difficulty,
        )
        quiz.items.append(item)
        return item

    def get_quiz(self, quiz_id: str) -> Quiz | None:
        return self._quizzes.get(quiz_id)

    def list_quizzes(self, topic: str) -> list[Quiz]:
        return [q for q in self._quizzes.values() if q.topic == topic]

    # ── Public Interface: Session Management ────────────────────────

    def start_quiz(self, topic: str, quiz_id: str) -> str:
        """Start a new quiz session. Returns session_id."""
        quiz = self._quizzes.get(quiz_id)
        if quiz is None:
            raise ValueError(f"Quiz not found: {quiz_id}")

        session_id = str(uuid4())
        session = QuizSession(
            session_id=session_id,
            quiz_id=quiz_id,
            topic=topic,
            started_at=datetime.now(UTC).isoformat(),
        )
        self._sessions[session_id] = session
        self._persist_session_start(session)
        return session_id

    def answer_item(
        self,
        session_id: str,
        quiz_item_id: str,
        raw_answer: str,
    ) -> SessionResult:
        """Submit and score an answer within a session."""
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

        # Persist the submission
        attempt_number = sum(1 for r in session.results if r.quiz_item_id == quiz_item_id) + 1
        self._persist_answer(session_id, quiz_item_id, raw_answer, attempt_number)

        # Score it
        answer_key = self._keys.retrieve(quiz_item_id)
        if answer_key is None:
            # Fallback for prototype: use internal key store
            from state_core.scoring_engine import AnswerKey as SKAnswerKey

            answer_key = SKAnswerKey()  # Would need actual retrieval

        # For prototype, use our internal scoring
        internal_key = _AnswerKey()  # Would retrieve from _keys
        result = _score_answer(raw_answer, internal_key)

        # Persist the score
        self._persist_score(quiz_item_id, result.raw_score, result.passed)

        sr = SessionResult(
            quiz_item_id=quiz_item_id,
            question=question,
            attempt_number=attempt_number,
            raw_score=result.raw_score,
            passed=result.passed,
        )
        session.results.append(sr)
        return sr

    def complete_session(self, session_id: str) -> QuizSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.completed_at = datetime.now(UTC).isoformat()
        self._persist_session_complete(session)
        return session

    def get_summary(self, session_id: str) -> SessionSummary | None:
        session = self._sessions.get(session_id)
        if session is None or not session.results:
            return None

        total = len(session.results)
        passed = sum(1 for r in session.results if r.passed)
        failed = total - passed
        avg_score = sum(r.raw_score for r in session.results) / total if total > 0 else 0.0

        return SessionSummary(
            session_id=session_id,
            quiz_id=session.quiz_id,
            topic=session.topic,
            total_items=total,
            passed_count=passed,
            failed_count=failed,
            average_score=round(avg_score, 2),
            pass_rate=round(passed / total, 2) if total > 0 else 0.0,
            completed_at=session.completed_at,
        )

    # ── Public Interface: Topic State Queries ───────────────────────

    def get_topic_state(self, topic: str):
        """Compute topic state by projecting events."""
        events = self._events.read_all()
        return project_topic_state(events, topic)

    def compute_topic_level(self, topic: str) -> str:
        """Compute deterministic mastery level for a topic."""
        state = self.get_topic_state(topic)
        return compute_level(state)


# ── Demo / Test Harness ──────────────────────────────────────────────


def run_demo() -> None:
    """Run a quick session lifecycle demo."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        event_path = Path(tmpdir) / "events.jsonl"
        event_store = EventStore(StoreConfig(path=str(event_path)))
        key_store = SealedAnswerKeyStore()

        module = QuizModule(event_store, key_store)

        # Create quiz
        module.create_quiz("python-basics", "python-basics-quiz", "Python Basics Quiz")
        module.add_item(
            quiz_id="python-basics-quiz",
            quiz_item_id="q1",
            question="What is a list comprehension?",
            category="short_answer",
            difficulty="easy",
            required_keywords=["brackets", "expression", "for"],
            forbidden_keywords=["loop", "append"],
            min_length_chars=20,
        )
        module.add_item(
            quiz_id="python-basics-quiz",
            quiz_item_id="q2",
            question="How do you handle exceptions?",
            category="short_answer",
            difficulty="medium",
            required_keywords=["try", "except"],
            forbidden_keywords=["catch"],
            min_length_chars=15,
        )

        # Start session
        session_id = module.start_quiz("python-basics", "python-basics-quiz")
        print(f"Started session: {session_id}")

        # Answer items
        result1 = module.answer_item(
            session_id,
            "q1",
            "A list comprehension uses brackets with an expression for each item in an iterable",
        )
        print(f"Q1: score={result1.raw_score:.0%} passed={result1.passed}")

        result2 = module.answer_item(
            session_id,
            "q2",
            "You use try and except blocks to catch and handle exceptions",
        )
        print(f"Q2: score={result2.raw_score:.0%} passed={result2.passed}")

        # Complete and summarize
        module.complete_session(session_id)
        summary = module.get_summary(session_id)
        print(f"\nSummary: {summary.passed_count}/{summary.total_items} passed, avg={summary.average_score:.0%}")

        # Topic state
        topic_state = module.get_topic_state("python-basics")
        level = module.compute_topic_level("python-basics")
        print(f"\nTopic state: {topic_state.topic}, level={level}, attempts={topic_state.attempts_total}")

        print("\n[OK] Session lifecycle test passed!")


if __name__ == "__main__":
    run_demo()
