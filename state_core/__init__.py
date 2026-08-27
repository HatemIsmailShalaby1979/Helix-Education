"""Helix Education Center — State Core.

Event-sourced learning state engine with zero AI dependencies.
"""

from .event_models import (
    AnswerScoredEvent,
    AnswerSubmittedEvent,
    Event,
    LearningStateUpdatedEvent,
    LessonSectionCommittedEvent,
    ProfileDeltaApprovedEvent,
    ProfileDeltaProposedEvent,
    QuizItemCreatedEvent,
    QuizResultEvent,
    TopicBranchedEvent,
    TopicPassedEvent,
    TopicStartedEvent,
)
from .event_store import EventStore, SealedAnswerKeyStore, StoreConfig, compute_key_hash
from .leveling_engine import compute_level
from .projections import (
    LearnerProfile,
    TopicState,
    project_learner_profile,
    project_topic_state,
)
from .scoring_engine import AnswerKey, ScoreResult, score_answer, score_answer_simple

__all__ = [
    "Event",
    "TopicStartedEvent",
    "LessonSectionCommittedEvent",
    "QuizItemCreatedEvent",
    "AnswerSubmittedEvent",
    "AnswerScoredEvent",
    "TopicPassedEvent",
    "TopicBranchedEvent",
    "ProfileDeltaProposedEvent",
    "ProfileDeltaApprovedEvent",
    "QuizResultEvent",
    "LearningStateUpdatedEvent",
    "EventStore",
    "StoreConfig",
    "SealedAnswerKeyStore",
    "compute_key_hash",
    "project_topic_state",
    "project_learner_profile",
    "TopicState",
    "LearnerProfile",
    "compute_level",
    "AnswerKey",
    "ScoreResult",
    "score_answer",
    "score_answer_simple",
]
