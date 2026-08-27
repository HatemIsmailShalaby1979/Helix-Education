"""Data models for the Progress Engine.

Defines milestones, learning paths, and progress tracking structures.
"""

from dataclasses import dataclass, field
from enum import Enum


class MilestoneType(Enum):
    """Types of learning milestones."""

    TOPIC_STARTED = "topic_started"
    TOPIC_PASSED = "topic_passed"
    LEVEL_ACHIEVED = "level_achieved"
    BRANCH_EXPLORED = "branch_explored"
    QUIZ_COMPLETED = "quiz_completed"


@dataclass
class Milestone:
    """A learning milestone achieved by the learner.

    Inputs:
        milestone_type: The type of milestone.
        topic: The topic associated with this milestone.
        detail: Additional detail (e.g., level achieved, quiz score).
        timestamp: ISO8601 timestamp of when the milestone was achieved.
    """

    milestone_type: MilestoneType
    topic: str
    detail: str = ""
    timestamp: str = ""


@dataclass
class LearningPath:
    """A suggested learning path through topics.

    Inputs:
        topics: Ordered list of topic names defining the curriculum.
        current_index: Index into topics indicating current position.
        completed_topics: List of topics the learner has completed.
        recommended_next: Topic recommended as the next step.
    """

    topics: list[str] = field(default_factory=list)
    current_index: int = 0
    completed_topics: list[str] = field(default_factory=list)
    recommended_next: str | None = None


@dataclass
class UserLearningState:
    """Persistent learning state for a learner, rebuilt from events.

    Tracks aggregate statistics across all quiz attempts and
    topic-level mastery flags. Mutations are event-sourced —
    every change emits a LearningStateUpdatedEvent.

    Inputs:
        total_questions_studied: Cumulative count of quiz items answered.
        running_average_score: Running average of all raw_scores.
        topics_mastered: Topics where all items have been answered
            with raw_score >= 0.6.
        topics_in_progress: Topics with at least one attempt but
            not yet fully mastered.
    """

    total_questions_studied: int = 0
    running_average_score: float = 0.0
    topics_mastered: list[str] = field(default_factory=list)
    topics_in_progress: list[str] = field(default_factory=list)
