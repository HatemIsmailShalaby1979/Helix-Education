"""Cognitive Agent Orchestrator — wires the first LLM-facing pipeline.

This module implements the complete generate-and-persist flow for a single
lesson section, maintaining the trust boundary at every step:

1. Fetch grounding chunks via GroundingService (no LLM involvement)
2. Generate a validated LessonSectionDraft via CognitiveAgentService
   (trust boundary: LLM output -> Pydantic validation -> explicit failure)
3. Convert draft.source_indices to actual citation_text via
   CognitiveAgentService.draft_to_citations (LLM never writes citation text)
4. Persist via ContentService.commit_section (event-sourced durability)

No step silently swallows validation errors. No step fabricates fallback
data. The caller receives either a fully-validated, fully-persisted Section
or a typed exception explaining exactly where and why the pipeline failed.
"""

from cognitive_agent.agent_models import (
    LessonSectionDraft,
    LessonSectionGenerationError,
)
from cognitive_agent.agent_service import CognitiveAgentService
from content_engine.content_models import Section
from content_engine.content_service import ContentService
from grounding_engine.grounding_models import GroundingFetchError, GroundingResult
from grounding_engine.grounding_service import GroundingService


class AgentOrchestratorError(Exception):
    """Base exception for orchestrator failures."""

    pass


class GroundingFailedError(AgentOrchestratorError):
    """Raised when grounding fetch fails."""

    def __init__(self, topic: str, original_error: GroundingFetchError) -> None:
        self.topic = topic
        self.original_error = original_error
        super().__init__(f"Grounding fetch failed for topic '{topic}': {original_error}")


class GenerationFailedError(AgentOrchestratorError):
    """Raised when LLM generation or validation fails."""

    def __init__(
        self,
        topic: str,
        level: str,
        original_error: LessonSectionGenerationError,
    ) -> None:
        self.topic = topic
        self.level = level
        self.original_error = original_error
        super().__init__(f"Lesson section generation failed for topic '{topic}' at level '{level}': {original_error}")


class PersistenceFailedError(AgentOrchestratorError):
    """Raised when section commit fails."""

    def __init__(
        self,
        topic: str,
        section_id: str,
        original_error: Exception,
    ) -> None:
        self.topic = topic
        self.section_id = section_id
        self.original_error = original_error
        super().__init__(f"Section commit failed for topic '{topic}', section '{section_id}': {original_error}")


class LessonNotFoundError(AgentOrchestratorError):
    """Raised when no lesson exists for the topic."""

    def __init__(self, topic: str) -> None:
        self.topic = topic
        super().__init__(f"No lesson found for topic '{topic}'")


class AgentOrchestrator:
    """Orchestrates the full generate-and-persist pipeline for one section.

    This class has NO event-sourcing logic, NO LLM logic, NO grounding logic.
    It ONLY coordinates the three services, passing validated data between
    them. The trust boundary is preserved because:
    - GroundingService returns SourceChunk objects (trusted data)
    - CognitiveAgentService validates LLM output via Pydantic and raises
      LessonSectionGenerationError on ANY validation failure (no silent
      fallbacks)
    - CognitiveAgentService.draft_to_citations extracts citation_text from
      trusted SourceChunk objects (LLM only chooses indices, never writes
      citation text)
    - ContentService.commit_section persists the final Section and emits
      the event

    Args:
        grounding_service: GroundingService for fetching source material.
        agent_service: CognitiveAgentService for LLM generation + validation.
        content_service: ContentService for persistence + event emission.
    """

    def __init__(
        self,
        grounding_service: GroundingService,
        agent_service: CognitiveAgentService,
        content_service: ContentService,
    ) -> None:
        self._grounding = grounding_service
        self._agent = agent_service
        self._content = content_service

    def generate_and_commit_section(
        self,
        topic: str,
        level: str,
        section_id: str,
        max_chunks: int = 5,
    ) -> Section:
        """Generate one lesson section grounded in sources and persist it.

        Pipeline:
        1. Fetch grounding chunks for the topic via GroundingService.
        2. Generate LessonSectionDraft via CognitiveAgentService.
           - If validation fails at ANY stage (JSON parse, Pydantic schema,
             out-of-range source_indices), raises GenerationFailedError
             with the specific LessonSectionGenerationError.
        3. Convert draft.source_indices to citation_text strings via
           CognitiveAgentService.draft_to_citations.
        4. Ensure lesson exists for topic (auto-create if needed, matching
           ContentService's existing behavior in commit_section).
        5. Persist via ContentService.commit_section with the citations.

        Args:
            topic: The topic to generate a section for.
            level: Difficulty level (e.g., "beginner", "intermediate", "advanced").
            section_id: Unique identifier for the new section.
            max_chunks: Maximum grounding chunks to fetch (default 5).

        Returns:
            The persisted Section object with title, body, and source_citations.

        Raises:
            GroundingFailedError: If grounding fetch fails.
            GenerationFailedError: If LLM generation or validation fails.
            PersistenceFailedError: If section commit fails.
        """
        # Step 1: Fetch grounding
        try:
            grounding_result: GroundingResult = self._grounding.get_grounding(
                topic=topic,
                max_chunks=max_chunks,
            )
        except GroundingFetchError as e:
            raise GroundingFailedError(topic, e) from e

        grounding_chunks = grounding_result.chunks

        # Step 2: Generate validated draft (trust boundary)
        try:
            draft: LessonSectionDraft = self._agent.generate_lesson_section(
                topic=topic,
                level=level,
                grounding_chunks=grounding_chunks,
            )
        except LessonSectionGenerationError as e:
            raise GenerationFailedError(topic, level, e) from e

        # Step 3: Convert source_indices to actual citation_text
        # (LLM never writes citation text, only chooses which chunks by index)
        citations = self._agent.draft_to_citations(draft, grounding_chunks)

        # Step 4: Ensure lesson exists (ContentService.commit_section
        # auto-creates if missing, but we explicitly create to emit
        # TopicStartedEvent first for proper event-sourcing)
        lesson = self._content.get_lesson(topic)
        if lesson is None:
            # Auto-create lesson with generic title; commit_section will
            # update if needed
            self._content.create_lesson(
                topic=topic,
                title=topic,
                difficulty=level,
            )

        # Step 5: Persist section with citations
        try:
            section = self._content.commit_section(
                topic=topic,
                section_id=section_id,
                title=draft.section_title,
                body=draft.body,
                source_citations=citations,
            )
        except Exception as e:
            raise PersistenceFailedError(topic, section_id, e) from e

        return section
