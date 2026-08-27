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
)
from cognitive_agent.agent_service import CognitiveAgentService
from content_engine.content_models import Section
from content_engine.content_service import ContentService
from grounding_engine.grounding_models import GroundingResult
from grounding_engine.grounding_service import GroundingService


class NoGroundingAvailableError(Exception):
    """Raised when grounding fetch succeeds but returns zero chunks.

    This is distinct from GroundingFetchError because 'the fetch worked but
    found nothing' is a different situation from 'the fetch broke', and
    callers may want to handle them differently (e.g., retry with a broader
    query vs. alert an operator).

    Args:
        topic: The topic that had no grounding results.
    """

    def __init__(self, topic: str) -> None:
        self.topic = topic
        super().__init__(f"No grounding chunks available for topic: {topic}")


class GenerationOrchestrator:
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

    @property
    def content_service(self) -> ContentService:
        """Expose ContentService for test verification."""
        return self._content

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
             out-of-range source_indices), raises LessonSectionGenerationError
        3. Convert draft.source_indices to citation_text strings via
           CognitiveAgentService.draft_to_citations.
        4. Ensure lesson exists for topic (auto-create if needed).
        5. Persist via ContentService.commit_section with the citations.

        Args:
            topic: The topic to generate a section for.
            level: Difficulty level (e.g., "beginner", "intermediate", "advanced").
            section_id: Unique identifier for the new section.
            max_chunks: Maximum grounding chunks to fetch (default 5).

        Returns:
            The persisted Section object with title, body, and source_citations.

        Raises:
            GroundingFetchError: If grounding fetch fails.
            NoGroundingAvailableError: If grounding fetch succeeds but returns zero chunks.
            LessonSectionGenerationError: If LLM generation or validation fails.
            ValueError: If ContentService.commit_section raises.
        """
        # Step 1: Fetch grounding
        grounding_result: GroundingResult = self._grounding.get_grounding(
            topic=topic,
            max_chunks=max_chunks,
        )

        grounding_chunks = grounding_result.chunks

        # Step 2: Empty grounding is a distinct error (not a fetch failure)
        if not grounding_chunks:
            raise NoGroundingAvailableError(topic)

        # Step 3: Generate validated draft (trust boundary)
        draft: LessonSectionDraft = self._agent.generate_lesson_section(
            topic=topic,
            level=level,
            grounding_chunks=grounding_chunks,
        )

        # Step 4: Convert source_indices to actual citation_text
        # (LLM never writes citation text, only chooses which chunks by index)
        citations = self._agent.draft_to_citations(draft, grounding_chunks)

        # Step 5: Ensure lesson exists (ContentService.commit_section
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

        # Step 6: Persist section with citations
        section = self._content.commit_section(
            topic=topic,
            section_id=section_id,
            title=draft.section_title,
            body=draft.body,
            source_citations=citations,
        )

        return section
