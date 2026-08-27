"""Cognitive Engine — knowledge maps, recommendations, and metacognitive insights.

Tracks learner sessions, builds knowledge maps from event data, generates
study recommendations with HITL approval, and produces metacognitive
insights about learning patterns.
"""

from .cognitive_models import (
    CognitiveNode,
    JourneyEntry,
    KnowledgeMap,
    LearningSession,
    MetacognitiveInsight,
    Recommendation,
)
from .cognitive_service import CognitiveService

__all__ = [
    "CognitiveNode",
    "Recommendation",
    "LearningSession",
    "MetacognitiveInsight",
    "KnowledgeMap",
    "JourneyEntry",
    "CognitiveService",
]
