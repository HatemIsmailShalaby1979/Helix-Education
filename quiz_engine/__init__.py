"""Quiz Engine — quiz and session management micro-engine.

Manages quiz collections, quiz sessions, and aggregates results.
Uses the Learning Service for event-sourced persistence and the
Scoring Engine for deterministic answer scoring.
"""

from .quiz_models import Quiz, QuizItem, QuizSession, SessionResult
from .quiz_service import QuizService

__all__ = ["Quiz", "QuizItem", "QuizSession", "SessionResult", "QuizService"]
