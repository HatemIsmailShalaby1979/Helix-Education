"""Cognitive agent service implementing the trust boundary.

This module contains the CognitiveAgentService class which implements the
strict trust boundary between LLM output and trusted data. It validates
LLM responses against the LessonSectionDraft schema and ensures that
malformed or malicious LLM output can never corrupt durable state.
"""

import json

from pydantic import ValidationError

from grounding_engine.grounding_models import SourceChunk

from .agent_client import CognitiveAgentClient
from .agent_models import LessonSectionDraft, LessonSectionGenerationError


class CognitiveAgentService:
    """Service for generating lesson sections with strict validation.

    This class implements the trust boundary between LLM output and trusted
    data. It validates LLM responses against the LessonSectionDraft schema
    and ensures that malformed or malicious LLM output can never corrupt
    durable state.
    """

    def __init__(self, client: CognitiveAgentClient) -> None:
        """Initialize the CognitiveAgentService.

        Args:
            client: The cognitive agent client to use for LLM calls.
        """
        self._client = client

    def generate_lesson_section(
        self,
        topic: str,
        level: str,
        grounding_chunks: list[SourceChunk],
    ) -> LessonSectionDraft:
        """Generate one lesson section grounded ONLY in the given chunks.

        1. Build a prompt that includes the topic, level, and the
           grounding_chunks' content — index them explicitly (0, 1, 2...)
           in the prompt text so the model can cite by index.
        2. Instruct the model to respond ONLY with JSON matching the
           LessonSectionDraft schema — no prose before/after.
        3. Call self._client.generate_raw(prompt).
        4. Parse the raw response as JSON, then validate against
           LessonSectionDraft via Pydantic.
        5. If JSON parsing fails OR Pydantic validation fails OR any
           source_indices value is out of range for the given
           grounding_chunks list length: raise
           LessonSectionGenerationError with the specific reason
           (which failure mode, and the raw response for debugging) —
           DO NOT retry silently inside this method, DO NOT return a
           partially-valid or fabricated result. One attempt, clean
           success or explicit typed failure. Retry logic, if wanted,
           belongs to the CALLER, not this method — keep this method's
           contract simple and honest.
        6. On success, return the validated LessonSectionDraft.

        This method NEVER touches the EventStore directly. It has no
        knowledge of ContentService or LearningService. It is a pure
        generate-and-validate function — persistence is the caller's
        job, explicitly, so this boundary stays testable in total
        isolation from the event-sourced state.
        """
        # Build prompt with explicit chunk indices
        prompt = self._build_prompt(topic, level, grounding_chunks)

        # Call the LLM client
        raw_response = self._client.generate_raw(prompt)

        # Parse and validate the response
        return self._parse_and_validate_response(raw_response, grounding_chunks)

    def _build_prompt(
        self,
        topic: str,
        level: str,
        grounding_chunks: list[SourceChunk],
    ) -> str:
        """Build the prompt for the LLM.

        Args:
            topic: The topic to generate a lesson section about.
            level: The difficulty level of the lesson section.
            grounding_chunks: The grounding chunks to use.

        Returns:
            The prompt for the LLM.
        """
        # Build the grounding context section
        grounding_context = "\n".join(f"[{i}] {chunk.content}" for i, chunk in enumerate(grounding_chunks))

        return f"""You are an educational content generator. Generate a lesson section about the topic '{topic}' at the '{level}' difficulty level.

Use the following grounding chunks to inform your response. Cite chunks by their index in square brackets.

Grounding Chunks:
{grounding_context}

Requirements:
1. Generate a section_title (max 200 characters)
2. Generate a body (50-4000 characters)
3. Generate source_indices (list of integers) referencing the chunks above
   - MUST reference at least one valid index
   - Each index must be within the range of available chunks
4. Do not add any factual claim, example, or elaboration that is not directly supported by the provided source chunks. Every sentence in the body must either paraphrase content from a specific chunk (and be covered by that chunk's index in source_indices) or be a purely structural/transitional sentence with no independent factual content (e.g., "Let's look at how this works in practice."). If the grounding chunks do not contain enough material to write a complete section, write a SHORTER section using only what is grounded, rather than filling gaps with unsourced content.

Output ONLY valid JSON matching this exact schema:
{{
    "section_title": "string (1-200 chars)",
    "body": "string (50-4000 chars)",
    "source_indices": [integer, ...]
}}

Do not include any prose before or after the JSON.
"""

    def _parse_and_validate_response(
        self,
        raw_response: str,
        grounding_chunks: list[SourceChunk],
    ) -> LessonSectionDraft:
        """Parse and validate the LLM response.

        Args:
            raw_response: The raw response from the LLM.
            grounding_chunks: The grounding chunks to validate against.

        Returns:
            The validated LessonSectionDraft.

        Raises:
            LessonSectionGenerationError: If the response cannot be parsed
                or validated.
        """
        # Parse JSON
        try:
            parsed_data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise LessonSectionGenerationError(f"JSON parsing failed: {e}. Raw response: {raw_response}") from e

        # Validate against schema
        try:
            draft = LessonSectionDraft(**parsed_data)
        except ValidationError as e:
            raise LessonSectionGenerationError(f"Schema validation failed: {e}. Raw response: {raw_response}") from e

        # Validate source indices are within range
        self._validate_source_indices(draft.source_indices, grounding_chunks)

        return draft

    def _validate_source_indices(
        self,
        source_indices: list[int],
        grounding_chunks: list[SourceChunk],
    ) -> None:
        """Validate that source indices are within range.

        Args:
            source_indices: The source indices to validate.
            grounding_chunks: The grounding chunks to validate against.

        Raises:
            LessonSectionGenerationError: If any source index is out of range.
        """
        max_index = len(grounding_chunks) - 1
        for idx in source_indices:
            if idx < 0 or idx > max_index:
                raise LessonSectionGenerationError(
                    f"source_indices contains out-of-range index {idx}. Valid range is [0, {max_index}]."
                )

    def draft_to_citations(
        self,
        draft: LessonSectionDraft,
        grounding_chunks: list[SourceChunk],
    ) -> list[str]:
        """Convert a validated draft's source_indices into the actual
        citation_text strings from grounding_chunks, ready to pass
        directly into ContentService.commit_section()'s
        source_citations parameter. This is the ONLY place citation
        text is extracted — never let the LLM write its own citation
        text, only let it choose WHICH chunks it used, by index.

        Args:
            draft: The validated lesson section draft.
            grounding_chunks: The grounding chunks to extract citations from.

        Returns:
            The citation texts for the draft's source indices.
        """
        citations = []
        for idx in draft.source_indices:
            citations.append(grounding_chunks[idx].citation_text)
        return citations
