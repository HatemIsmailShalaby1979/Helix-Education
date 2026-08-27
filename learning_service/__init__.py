"""Learning Service — orchestration layer for the Helix Education Center.

Coordinates multi-step learning workflows across the State Core:
topic lifecycle, lesson management, quiz/answer scoring, and profile
management. Depends only on state_core components and uses the
EventStore as its communication backbone.
"""

from dataclasses import dataclass, field
from typing import Optional

from state_core.event_models import (
    AnswerScoredEvent,
    AnswerSubmittedEvent,
    Event,
    LessonSectionCommittedEvent,
    ProfileDeltaApprovedEvent,
    ProfileDeltaProposedEvent,
    QuizItemCreatedEvent,
    TopicBranchedEvent,
    TopicPassedEvent,
    TopicStartedEvent,
)
from state_core.event_store import EventStore
from state_core.leveling_engine import compute_level
from state_core.llm_evaluation import LLMEvaluationResult, LLMEvaluationService
from state_core.projections import (
    LearnerProfile,
    TopicState,
    project_learner_profile,
    project_topic_state,
)
from state_core.scoring_engine import AnswerKey
from state_core.security.encrypted_key_store import EncryptedSealedKeyStore


@dataclass
class AnswerRecord:
    """Record of a scored answer attempt.

    Inputs:
        quiz_item_id: The quiz item this answer was for.
        attempt_number: Which attempt number this was.
        raw_score: The computed score.
        passed: Whether the answer passed the threshold.
        missing_keywords: Required keywords not found.
    """

    quiz_item_id: str
    attempt_number: int
    raw_score: float
    passed: bool
    missing_keywords: list[str]


class LearningService:
    """High-level orchestration service for learning workflows.

    Wraps the event-sourced State Core into a convenient API.
    All mutations go through the EventStore (append-only).
    All state queries go through projection functions (pure).

    Inputs:
        event_store: An EventStore instance for persistence.
        key_store: A SealedAnswerKeyStore for answer key management.
        llm_evaluation: Optional LLMEvaluationService for semantic answer scoring.
            If not provided, falls back to keyword-based scoring.
    """

    def __init__(
        self,
        event_store: EventStore,
        key_store: EncryptedSealedKeyStore,
        llm_evaluation: LLMEvaluationService | None = None,
    ) -> None:
        self._event_store = event_store
        self._key_store = key_store
        self._llm_evaluation = llm_evaluation

    # ── Topic Lifecycle ──────────────────────────────────────────

    def start_topic(
        self,
        topic: str,
        requested_level: str | None = None,
        parent_topic: str | None = None,
        lesson_title: str | None = None,
        difficulty: str | None = None,
    ) -> TopicState:
        """Begin study of a new topic.

        Appends a TopicStartedEvent and returns the current topic state.

        Inputs:
            topic: The topic name.
            requested_level: Optional target level.
            parent_topic: Optional parent topic for branching.
            lesson_title: Optional lesson title for content rebuild.
            difficulty: Optional difficulty classification for lesson rebuild.
        Returns:
            The current TopicState after the event is appended.
        """
        event = TopicStartedEvent.create(
            topic=topic,
            requested_level=requested_level,
            parent_topic=parent_topic,
            lesson_title=lesson_title,
            difficulty=difficulty,
        )
        self._event_store.append(event)
        return self.get_topic_state(topic)

    def get_topic_state(self, topic: str) -> TopicState:
        """Compute the current state for a topic by replaying all events.

        Inputs:
            topic: The topic name.
        Returns:
            A TopicState dataclass.
        """
        events = self._event_store.read_all()
        return project_topic_state(events, topic)

    def compute_topic_level(self, topic: str) -> str:
        """Compute the deterministic mastery level for a topic.

        Inputs:
            topic: The topic name.
        Returns:
            One of 'beginner', 'intermediate', 'expert'.
        """
        state = self.get_topic_state(topic)
        return compute_level(state)

    def pass_topic(self, topic: str, final_level: str) -> TopicPassedEvent:
        """Officially mark a topic as passed at the given level.

        Inputs:
            topic: The topic name.
            final_level: The level achieved.
        Returns:
            The created TopicPassedEvent.
        """
        state = self.get_topic_state(topic)
        event = TopicPassedEvent.create(
            topic=topic,
            final_level=final_level,
            attempts_total=state.attempts_total,
        )
        self._event_store.append(event)
        return event

    def branch_topic(
        self,
        parent_topic: str,
        child_topic: str,
        reason: str,
    ) -> TopicBranchedEvent:
        """Create a dig-deeper branch from parent topic to child topic.

        Inputs:
            parent_topic: The existing topic to branch from.
            child_topic: The new subtopic name.
            reason: Why the branch was created.
        Returns:
            The created TopicBranchedEvent.
        """
        event = TopicBranchedEvent.create(
            parent_topic=parent_topic,
            child_topic=child_topic,
            reason=reason,
        )
        self._event_store.append(event)
        return event

    # ── Lesson Lifecycle ─────────────────────────────────────────

    def commit_lesson_section(
        self,
        topic: str,
        section_id: str,
        title: str,
        body: str,
        source_citations: list[str],
        lesson_title: str | None = None,
    ) -> None:
        """Commit a lesson section with source citations to the event log.

        Inputs:
            topic: The topic this section belongs to.
            section_id: Unique identifier for the section.
            title: The section title.
            body: The section body text.
            source_citations: List of source references.
            lesson_title: Optional lesson title for rebuild.
        """
        event = LessonSectionCommittedEvent.create(
            topic=topic,
            section_id=section_id,
            title=title,
            body=body,
            source_citations=source_citations,
            lesson_title=lesson_title,
        )
        self._event_store.append(event)

    # ── Quiz Lifecycle ───────────────────────────────────────────

    def create_quiz_item(
        self,
        topic: str,
        quiz_id: str,
        quiz_item_id: str,
        question: str,
        category: str,
        difficulty: str,
        answer_key: AnswerKey,
    ) -> QuizItemCreatedEvent:
        """Create a quiz item with a sealed answer key.

        The AnswerKey is stored in the SealedAnswerKeyStore (not in the
        event log). Only its SHA-256 hash appears in the event.

        Inputs:
            topic: The topic this quiz item belongs to.
            quiz_id: The quiz this item belongs to.
            quiz_item_id: Unique identifier for the quiz item.
            question: The question text.
            category: Question category (e.g., 'multiple_choice').
            difficulty: Difficulty level (e.g., 'easy', 'medium').
            answer_key: The AnswerKey defining correct answers.
        Returns:
            The created QuizItemCreatedEvent.
        """
        key_hash = self._key_store.store(quiz_item_id, answer_key)
        event = QuizItemCreatedEvent.create(
            topic=topic,
            quiz_id=quiz_id,
            quiz_item_id=quiz_item_id,
            question=question,
            category=category,
            difficulty=difficulty,
            answer_key_hash=key_hash,
        )
        self._event_store.append(event)
        return event

    def submit_and_score_answer(
        self,
        quiz_item_id: str,
        raw_answer: str,
        question: str = "",
        source_context: str = "",
    ) -> LLMEvaluationResult:
        """Submit an answer, evaluate it, and record both events.

        1. Appends AnswerSubmittedEvent.
        2. Retrieves AnswerKey from the sealed store.
        3. Evaluates the answer using LLM semantic evaluation (if available)
           or keyword-based fallback.
        4. Appends AnswerScoredEvent with evaluation method metadata.
        5. Returns the LLMEvaluationResult with score, reasoning, misconceptions, next_steps.

        Inputs:
            quiz_item_id: The quiz item being answered.
            raw_answer: The learner's answer text.
            question: The quiz question text (for LLM context).
            source_context: Source material context for grounding (for LLM context).
        Returns:
            An LLMEvaluationResult with score, pass/fail, reasoning, misconceptions, next_steps.
        Raises:
            ValueError: If the answer key is not found.
        """
        # Determine attempt number
        events = self._event_store.read_all()
        attempt_number = 1
        for e in events:
            if isinstance(e, AnswerSubmittedEvent) and e.quiz_item_id == quiz_item_id:
                attempt_number = max(attempt_number, e.attempt_number + 1)

        submit_event = AnswerSubmittedEvent.create(
            quiz_item_id=quiz_item_id,
            raw_answer=raw_answer,
            attempt_number=attempt_number,
        )
        self._event_store.append(submit_event)

        answer_key = self._key_store.retrieve(quiz_item_id)
        if answer_key is None:
            raise ValueError(f"No answer key found for quiz item: {quiz_item_id}")

        # Use LLM evaluation if available, otherwise fall back to keyword scoring
        if self._llm_evaluation is not None:
            result = self._llm_evaluation.evaluate_answer(
                quiz_item_id=quiz_item_id,
                raw_answer=raw_answer,
                question=question,
                source_context=source_context,
                attempt_number=attempt_number,
            )
        else:
            # Fallback to keyword scoring
            from state_core.scoring_engine import ScoreResult, score_answer_detailed

            keyword_result: ScoreResult = score_answer_detailed(raw_answer, answer_key, attempt_number=attempt_number)
            result = LLMEvaluationResult(
                score=keyword_result.raw_score,
                passed=keyword_result.passed,
                reasoning=f"Keyword scoring: matched {len(keyword_result.matched_keywords)}/{len(answer_key.required_keywords)} required keywords.",
                misconceptions=keyword_result.missing_keywords,  # For backward compatibility
                next_steps=["Review the missing key concepts."] if keyword_result.missing_keywords else [],
                confidence=0.4,
                evaluation_method="keyword_fallback",
                attempt_number=attempt_number,
                matched_keywords=keyword_result.matched_keywords,
            )

        score_event = AnswerScoredEvent.create(
            quiz_item_id=quiz_item_id,
            raw_score=result.score,
            passed=result.passed,
            scoring_method=result.evaluation_method,
        )
        self._event_store.append(score_event)

        return result

    # ── Profile Lifecycle ────────────────────────────────────────

    def propose_profile_delta(
        self,
        evidence: list[str],
        proposed_changes: dict,
    ) -> str:
        """Propose a change to the learner profile.

        The proposal must be explicitly approved via approve_profile_delta
        before it takes effect. This enforces the human-approval gate.

        Inputs:
            evidence: List of evidence strings supporting the change.
            proposed_changes: Dict of trait key-value pairs to add.
        Returns:
            The event_id of the created ProfileDeltaProposedEvent.
        """
        event = ProfileDeltaProposedEvent.create(
            evidence=evidence,
            proposed_changes=proposed_changes,
        )
        self._event_store.append(event)
        return event.event_id

    def approve_profile_delta(
        self,
        delta_event_id: str,
        approved_by: str = "user",
    ) -> None:
        """Explicitly approve a previously proposed profile delta.

        Inputs:
            delta_event_id: The event_id of the ProfileDeltaProposedEvent.
            approved_by: Who approved the change.
        """
        event = ProfileDeltaApprovedEvent.create(
            delta_event_id=delta_event_id,
            approved_by=approved_by,
        )
        self._event_store.append(event)

    def get_learner_profile(self) -> LearnerProfile:
        """Compute the full learner profile by replaying all events.

        Returns:
            A LearnerProfile with approved_traits, pending_deltas,
            and topics_studied.
        """
        events = self._event_store.read_all()
        return project_learner_profile(events)
