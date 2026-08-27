"""Data models for the Delivery Engine.

Defines feedback messages, session logs, and delivery formats.
"""

from dataclasses import dataclass, field
from enum import Enum


class FeedbackLevel(Enum):
    """Level of feedback detail."""

    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class FeedbackMessage:
    """A rendered feedback message for the learner.

    Inputs:
        level: The feedback severity/type level.
        title: Short title for the feedback.
        body: Detailed feedback body text.
        details: Optional list of detail strings (e.g., missed keywords).
    """

    level: FeedbackLevel
    title: str
    body: str
    details: list[str] = field(default_factory=list)


@dataclass
class SessionLog:
    """A log of the learner's actions in a session.

    Inputs:
        session_id: Unique session identifier.
        entries: Ordered list of log entry strings.
        started_at: ISO8601 timestamp for session start.
    """

    session_id: str
    entries: list[str] = field(default_factory=list)
    started_at: str = ""
