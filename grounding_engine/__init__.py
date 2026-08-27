"""Grounding Engine — source material retrieval and chunking.

This module provides the data structures, clients, chunking logic, and
caching service for retrieving and preparing grounded source material.

It has ZERO LLM/AI dependency. A future deliverable will wire an LLM
to consume this module's output.
"""

from .chunker import split_into_chunks
from .grounding_client import (
    GroundingClient,
    GroundingConfig,
    HttpGroundingClient,
    StubGroundingClient,
    WebGroundingClient,
)
from .grounding_models import GroundingFetchError, GroundingResult, SourceChunk
from .grounding_service import GroundingService

__all__ = [
    "SourceChunk",
    "GroundingResult",
    "GroundingFetchError",
    "GroundingClient",
    "GroundingConfig",
    "StubGroundingClient",
    "HttpGroundingClient",
    "WebGroundingClient",
    "split_into_chunks",
    "GroundingService",
]
