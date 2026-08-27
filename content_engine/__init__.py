"""Content Engine — lesson and section management micro-engine.

Manages lesson content with its own storage, separate from the event log.
The event log tracks *that* content was committed; the content engine
stores the actual body text and metadata.
"""

from .content_models import Lesson, Section
from .content_service import ContentService, ContentStoreConfig
from .lesson_orchestrator import LessonOrchestrator, LessonResult

__all__ = [
    "Lesson",
    "Section",
    "ContentService",
    "ContentStoreConfig",
    "LessonOrchestrator",
    "LessonResult",
]
