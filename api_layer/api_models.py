"""Request/response models for the Education Center API.

All models use dataclasses for zero-dependency serialization.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StartTopicRequest:
    """POST /topics request body."""

    topic: str
    requested_level: str | None = None
    parent_topic: str | None = None


@dataclass
class SubmitAnswerRequest:
    """POST /answers request body."""

    quiz_item_id: str
    raw_answer: str


@dataclass
class CreateQuizItemRequest:
    """POST /quiz-items request body."""

    topic: str
    quiz_item_id: str
    question: str
    category: str
    difficulty: str
    required_keywords: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)
    min_length_chars: int = 0


@dataclass
class TopicStateResponse:
    """GET /topics/{topic} response body."""

    topic: str
    current_level: str
    attempts_total: int
    pass_count: int
    fail_count: int
    is_passed: bool
    branch_children: list[str]
    last_activity_timestamp: str


@dataclass
class LearnerProfileResponse:
    """GET /profile response body."""

    approved_traits: dict[str, Any]
    pending_delta_count: int
    topics_studied: list[str]


@dataclass
class AnswerFeedbackResponse:
    """POST /answers response body."""

    raw_score: float
    passed: bool
    missing_keywords: list[str]
    matched_keywords: list[str]
    message: str
