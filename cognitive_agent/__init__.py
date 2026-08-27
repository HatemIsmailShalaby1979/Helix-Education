"""Cognitive Agent — trust boundary for LLM-generated content.

Implements strict validation of LLM output against trusted schemas,
ensuring malformed or malicious responses can never corrupt durable state.
"""

from .agent_client import CognitiveAgentClient
from .agent_models import LessonSectionDraft, LessonSectionGenerationError
from .agent_service import CognitiveAgentService
from .grounding_config import GroundingConfig

__all__ = [
    "CognitiveAgentClient",
    "CognitiveAgentService",
    "GroundingConfig",
    "LessonSectionDraft",
    "LessonSectionGenerationError",
]
