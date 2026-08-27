"""Progress Engine — learning path, milestone, and progress tracking.

Computes learner progress across topics, recommends next steps, and
tracks milestone achievements using the event-sourced state.
"""

from .progress_models import LearningPath, Milestone, MilestoneType, UserLearningState
from .progress_service import ProgressService
from .state_mutator import StateMutatorService

__all__ = [
    "Milestone",
    "LearningPath",
    "MilestoneType",
    "UserLearningState",
    "ProgressService",
    "StateMutatorService",
]
