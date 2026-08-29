"""Event models for the Learning Engine State Core.

Defines the closed set of event types used in the event-sourced architecture.
All events are immutable after creation.
"""

from dataclasses import asdict, dataclass
try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from typing import Any
from uuid import uuid4

_EVENT_TYPE_REGISTRY: dict[str, type["Event"]] = {}


def register_event_type(event_type_str: str):
    """Decorator that registers an event subclass in the type registry."""

    def decorator(cls: type["Event"]) -> type["Event"]:
        _EVENT_TYPE_REGISTRY[event_type_str] = cls
        return cls

    return decorator


@dataclass
class Event:
    """Base event with common fields for all event types.

    Inputs:
        event_id: UUID4 string uniquely identifying this event.
        timestamp: ISO8601 UTC timestamp of when the event was created.
    """

    event_id: str
    timestamp: str

    @classmethod
    def create(cls, **kwargs: Any) -> "Event":
        """Create a new event with auto-generated event_id and timestamp.

        Inputs:
            **kwargs: Field values specific to the event subclass.
        Returns:
            A new Event instance of the calling class.
        """
        return cls(
            event_id=str(uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            **kwargs,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this event to a JSON-compatible dictionary.

        Returns:
            dict with all fields plus a '__event_type__' key for routing.
        """
        result = asdict(self)
        for type_str, cls in _EVENT_TYPE_REGISTRY.items():
            if cls is type(self):
                result["__event_type__"] = type_str
                break
        return result

    @property
    def event_type(self) -> str:
        """Return the registered event type string for this event's class.

        Returns:
            The event type string (e.g. 'topic_started').
        Raises:
            ValueError: If the event class is not registered.
        """
        for type_str, cls in _EVENT_TYPE_REGISTRY.items():
            if cls is type(self):
                return type_str
        raise ValueError(f"Unregistered event class: {type(self).__name__}")

    def validate(self) -> None:
        """Validate that required base fields are present and well-formed.

        Raises:
            ValueError: If event_id or timestamp is missing/empty.
        """
        if not self.event_id or not isinstance(self.event_id, str):
            raise ValueError("event_id must be a non-empty string")
        if not self.timestamp or not isinstance(self.timestamp, str):
            raise ValueError("timestamp must be a non-empty string")

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Event":
        """Deserialize a dictionary back into the correct Event subclass.

        Inputs:
            data: dict containing '__event_type__' and all event fields.
        Returns:
            A concrete Event subclass instance.
        Raises:
            ValueError: If the event type is unknown.
        """
        data = data.copy()
        event_type_key = data.pop("__event_type__", "")
        cls = _EVENT_TYPE_REGISTRY.get(event_type_key)
        if cls is None:
            raise ValueError(f"Unknown event type: {event_type_key}")
        return cls(**data)


@register_event_type("topic_started")
@dataclass
class TopicStartedEvent(Event):
    """Emitted when a learner begins study of a new topic."""

    topic: str
    requested_level: str | None = None
    parent_topic: str | None = None
    lesson_title: str | None = None
    difficulty: str | None = None


@register_event_type("lesson_section_committed")
@dataclass
class LessonSectionCommittedEvent(Event):
    """Emitted when a lesson section with source citations is committed."""

    topic: str
    section_id: str
    title: str
    body: str
    source_citations: list[str]
    lesson_title: str | None = None


@register_event_type("quiz_created")
@dataclass
class QuizCreatedEvent(Event):
    """Emitted when a quiz is created for a topic."""

    topic: str
    quiz_id: str
    title: str | None = None


@register_event_type("quiz_item_created")
@dataclass
class QuizItemCreatedEvent(Event):
    """Emitted when a quiz item is created.

    Stores a hash of the answer key, NOT the raw key.
    """

    topic: str
    quiz_id: str
    quiz_item_id: str
    question: str
    category: str
    difficulty: str
    answer_key_hash: str


@register_event_type("answer_submitted")
@dataclass
class AnswerSubmittedEvent(Event):
    """Emitted when a learner submits an answer to a quiz item."""

    quiz_item_id: str
    raw_answer: str
    attempt_number: int


@register_event_type("answer_scored")
@dataclass
class AnswerScoredEvent(Event):
    """Emitted when an answer has been scored."""

    quiz_item_id: str
    raw_score: float
    passed: bool
    scoring_method: str


@register_event_type("topic_passed")
@dataclass
class TopicPassedEvent(Event):
    """Emitted when a topic is officially passed at a given level."""

    topic: str
    final_level: str
    attempts_total: int


@register_event_type("topic_branched")
@dataclass
class TopicBranchedEvent(Event):
    """Emitted when a learner drills deeper into a subtopic (dig deeper)."""

    parent_topic: str
    child_topic: str
    reason: str


@register_event_type("profile_delta_proposed")
@dataclass
class ProfileDeltaProposedEvent(Event):
    """Emitted when a change to the learner profile is proposed.

    The 'approved' field is always False and is enforced at construction.
    Approval is granted only by a separate ProfileDeltaApprovedEvent.
    """

    evidence: list[str]
    proposed_changes: dict
    approved: bool = False

    def __post_init__(self) -> None:
        """Enforce that approved is always False at the model level."""
        self.approved = False


@register_event_type("lesson_deleted")
@dataclass
class LessonDeletedEvent(Event):
    """Emitted when a lesson is removed from the content store.

    Past events are not mutated â€” this event marks the deletion so
    replays can reflect the current state accurately.
    """

    topic: str


@register_event_type("profile_delta_approved")
@dataclass
class ProfileDeltaApprovedEvent(Event):
    """Emitted when a proposed profile delta is explicitly approved."""

    delta_event_id: str
    approved_by: str = "user"


@register_event_type("learning_session_started")
@dataclass
class LearningSessionStartedEvent(Event):
    """Emitted when a learning session is started."""

    session_id: str
    topic: str


@register_event_type("journey_entry_recorded")
@dataclass
class JourneyEntryRecordedEvent(Event):
    """Emitted when a journey entry is recorded.

    entry_type is one of: "session_started", "section_read", "dig_deeper", "quiz_completed"
    """

    session_id: str
    entry_type: str
    topic: str
    detail: str
    score: float | None = None


@register_event_type("recommendation_proposed")
@dataclass
class RecommendationProposedEvent(Event):
    """Emitted when a recommendation is proposed."""

    recommendation_id: str
    concept: str
    topic: str
    reason: str
    suggested_action: str
    evidence: str
    priority: str


@register_event_type("recommendation_decision")
@dataclass
class RecommendationDecisionEvent(Event):
    """Emitted when a recommendation is approved or rejected.

    decision must be "approved" or "reject".
    """

    recommendation_id: str
    decision: str

    def __post_init__(self) -> None:
        """Validate that decision is either 'approved' or 'reject'."""
        if self.decision not in ("approved", "reject"):
            raise ValueError(f"decision must be 'approved' or 'reject', got: {self.decision}")


@register_event_type("quiz_result")
@dataclass
class QuizResultEvent(Event):
    """Emitted when a quiz item answer has been scored.

    Carries the item_id, score, and pass/fail status needed by the
    StateMutatorService to update persistent learning state.
    """

    quiz_id: str
    quiz_item_id: str
    raw_score: float
    passed: bool


@register_event_type("learning_state_updated")
@dataclass
class LearningStateUpdatedEvent(Event):
    """Emitted when persistent learning state has been mutated.

    Captures a snapshot of the UserLearningState after a mutation,
    ensuring full event-sourced traceability.
    """

    total_questions_studied: int
    running_average_score: float
    topics_mastered: list[str]
    topics_in_progress: list[str]
