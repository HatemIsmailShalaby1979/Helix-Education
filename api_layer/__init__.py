"""API Layer — RESTful integration for the Education Center.

Defines route handlers and request/response models for external
integration. Designed to be mounted on any HTTP framework (FastAPI,
Flask, or stdlib http.server).
"""

from .api_models import (
    AnswerFeedbackResponse,
    CreateQuizItemRequest,
    LearnerProfileResponse,
    StartTopicRequest,
    SubmitAnswerRequest,
    TopicStateResponse,
)
from .routes import Router

__all__ = [
    "StartTopicRequest",
    "SubmitAnswerRequest",
    "CreateQuizItemRequest",
    "TopicStateResponse",
    "LearnerProfileResponse",
    "AnswerFeedbackResponse",
    "Router",
]
