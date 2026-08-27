"""Data models for the Quiz Engine.

Defines quizzes, quiz items, and session results.
"""

from dataclasses import dataclass, field


@dataclass
class QuizItem:
    """A single item within a quiz.

    Inputs:
        quiz_item_id: Unique identifier for this item.
        question: The question text presented to the learner.
        category: Question category (e.g., 'multiple_choice', 'short_answer').
        difficulty: Difficulty classification (e.g., 'easy', 'medium', 'hard').
        required_keywords: Keywords that must appear in a correct answer.
            Stored on the item so the keyword-match score can be derived
            directly from the QuizItem (Directive 11: metacognitive
            feedback loop). Defaults to empty for backward compatibility;
            the sealed AnswerKey remains the authoritative scoring source.
    """

    quiz_item_id: str
    question: str
    category: str
    difficulty: str
    required_keywords: list[str] = field(default_factory=list)


@dataclass
class Quiz:
    """A quiz composed of multiple items for a topic.

    Inputs:
        topic: The topic this quiz belongs to.
        quiz_id: Unique identifier for the quiz.
        items: Ordered list of QuizItem instances.
        title: Optional human-readable title.
    """

    topic: str
    quiz_id: str
    items: list[QuizItem] = field(default_factory=list)
    title: str | None = None


@dataclass
class SessionResult:
    """Result of a single quiz item attempt within a session.

    Inputs:
        quiz_item_id: The quiz item attempted.
        question: The question text.
        attempt_number: Which attempt number.
        raw_score: The score received.
        passed: Whether the answer passed.
        missing_keywords: Required keywords not found in the answer.
        matched_keywords: Required keywords found in the answer.
    """

    quiz_item_id: str
    question: str
    attempt_number: int
    raw_score: float
    passed: bool
    missing_keywords: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class QuizSession:
    """Tracks a learner's session through a quiz.

    Inputs:
        session_id: Unique identifier for this session.
        quiz_id: The quiz being taken.
        topic: The topic being studied.
        results: List of SessionResult for each answered item.
        started_at: ISO8601 timestamp when the session started.
        completed_at: Optional ISO8601 timestamp when completed.
    """

    session_id: str
    quiz_id: str
    topic: str
    results: list[SessionResult] = field(default_factory=list)
    started_at: str = ""
    completed_at: str | None = None
