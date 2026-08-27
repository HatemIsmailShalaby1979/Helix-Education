"""Pure projection functions for computing state from an event log.

These functions have no side effects and perform no I/O. Given the same
list of Events in the same order, they always return the same result.
"""

from dataclasses import dataclass, field

from .event_models import (
    AnswerScoredEvent,
    AnswerSubmittedEvent,
    Event,
    JourneyEntryRecordedEvent,
    LearningSessionStartedEvent,
    ProfileDeltaApprovedEvent,
    ProfileDeltaProposedEvent,
    QuizItemCreatedEvent,
    RecommendationDecisionEvent,
    RecommendationProposedEvent,
    TopicBranchedEvent,
    TopicPassedEvent,
    TopicStartedEvent,
)


@dataclass
class TopicState:
    """Computed state for a single topic.

    Inputs:
        topic: The topic name.
        current_level: The computed level string (beginner/intermediate/expert).
        attempts_total: Total answer attempts for this topic.
        pass_count: Number of passing scores.
        fail_count: Number of failing scores.
        is_passed: Whether the topic has been officially passed.
        branch_children: List of child topics branched from this one.
        last_activity_timestamp: Most recent event timestamp for this topic.
        recent_attempts: Pass/fail results of recent attempts (most recent
            first), used by the leveling engine.
    """

    topic: str
    current_level: str = "beginner"
    attempts_total: int = 0
    pass_count: int = 0
    fail_count: int = 0
    is_passed: bool = False
    branch_children: list[str] = field(default_factory=list)
    last_activity_timestamp: str = ""
    recent_attempts: list[bool] = field(default_factory=list)


@dataclass
class LearnerProfile:
    """Computed learner profile from the full event log.

    Inputs:
        approved_traits: Traits that have been approved via
            ProfileDeltaApprovedEvent (never includes pending deltas).
        pending_deltas: Proposed deltas awaiting explicit approval.
        topics_studied: Unique list of topics the learner has engaged with.
    """

    approved_traits: dict = field(default_factory=dict)
    pending_deltas: list[ProfileDeltaProposedEvent] = field(default_factory=list)
    topics_studied: list[str] = field(default_factory=list)


def _get_topic_last_activity(events: list[Event], topic: str) -> str:
    """Find the latest timestamp among all events for a given topic."""
    latest = ""
    for e in events:
        ts = ""
        if hasattr(e, "topic") and getattr(e, "topic", None) == topic:
            ts = e.timestamp
        elif isinstance(e, AnswerSubmittedEvent) or isinstance(e, AnswerScoredEvent):
            if hasattr(e, "quiz_item_id"):
                ts = e.timestamp
        if ts and (not latest or ts > latest):
            latest = ts
    return latest


def project_topic_state(events: list[Event], topic: str) -> TopicState:
    """Compute the current state of a single topic by replaying events.

    Inputs:
        events: Full ordered list of Event instances.
        topic: The topic name to project state for.
    Returns:
        A TopicState dataclass with computed fields.
    """
    quiz_ids_for_topic: set[str] = set()
    for e in events:
        if isinstance(e, QuizItemCreatedEvent) and e.topic == topic:
            quiz_ids_for_topic.add(e.quiz_item_id)

    attempts_total = 0
    pass_count = 0
    fail_count = 0
    recent_attempts: list[bool] = []
    branch_children: list[str] = []
    is_passed = False
    final_level = "beginner"

    scored_events: list[AnswerScoredEvent] = []

    for e in events:
        if isinstance(e, TopicBranchedEvent) and e.parent_topic == topic:
            branch_children.append(e.child_topic)

        if isinstance(e, TopicPassedEvent) and e.topic == topic:
            is_passed = True
            final_level = e.final_level
            attempts_total = e.attempts_total

        if isinstance(e, AnswerScoredEvent):
            qid = e.quiz_item_id
            if qid in quiz_ids_for_topic:
                scored_events.append(e)
                attempts_total += 1
                if e.passed:
                    pass_count += 1
                else:
                    fail_count += 1

    recent_attempts = [e.passed for e in scored_events[-3:]]
    recent_attempts.reverse()

    last_ts = _get_topic_last_activity(events, topic)

    return TopicState(
        topic=topic,
        current_level=final_level if is_passed else "beginner",
        attempts_total=attempts_total,
        pass_count=pass_count,
        fail_count=fail_count,
        is_passed=is_passed,
        branch_children=branch_children,
        last_activity_timestamp=last_ts,
        recent_attempts=recent_attempts,
    )


def project_learner_profile(events: list[Event]) -> LearnerProfile:
    """Compute the full learner profile by replaying all events.

    CRITICAL: Pending deltas are NEVER merged into approved_traits.
    A delta is approved only when a matching ProfileDeltaApprovedEvent
    exists in the log referencing the proposed event's event_id.

    Inputs:
        events: Full ordered list of Event instances.
    Returns:
        A LearnerProfile dataclass with computed fields.
    """
    approved_delta_ids: set[str] = set()
    for e in events:
        if isinstance(e, ProfileDeltaApprovedEvent):
            approved_delta_ids.add(e.delta_event_id)

    approved_traits: dict = {}
    pending_deltas: list[ProfileDeltaProposedEvent] = []
    topics_set: set[str] = set()

    for e in events:
        if isinstance(e, ProfileDeltaProposedEvent):
            if e.event_id in approved_delta_ids:
                approved_traits.update(e.proposed_changes)
            else:
                pending_deltas.append(e)

        if isinstance(e, TopicStartedEvent):
            topics_set.add(e.topic)
        elif isinstance(e, TopicPassedEvent):
            topics_set.add(e.topic)
        elif isinstance(e, TopicBranchedEvent):
            topics_set.add(e.parent_topic)
            topics_set.add(e.child_topic)

    return LearnerProfile(
        approved_traits=approved_traits,
        pending_deltas=pending_deltas,
        topics_studied=sorted(topics_set),
    )


# ── Cognitive State Projection ─────────────────────────────────────


@dataclass
class CognitiveState:
    """Computed cognitive state from the full event log.

    Inputs:
        sessions: Reconstructed learning sessions from
            LearningSessionStartedEvent + JourneyEntryRecordedEvent replay.
        journey: All JourneyEntryRecordedEvent entries, sorted by timestamp.
        recommendations: Built from RecommendationProposedEvent, with
            .approved/.applied flags set only by a matching
            RecommendationDecisionEvent with decision="approved".
            REJECTED recommendations are excluded entirely.
    """

    sessions: dict[str, "LearningSession"] = field(default_factory=dict)
    journey: list["JourneyEntry"] = field(default_factory=list)
    recommendations: dict[str, "Recommendation"] = field(default_factory=dict)


def project_cognitive_state(events: list[Event]) -> CognitiveState:
    """Compute the full cognitive state by replaying all events.

    Inputs:
        events: Full ordered list of Event instances.
    Returns:
        A CognitiveState dataclass with computed fields.
    """
    from cognitive_engine.cognitive_models import (
        JourneyEntry,
        LearningSession,
        Recommendation,
    )

    # First pass: collect all events by type
    session_started_events: dict[str, LearningSessionStartedEvent] = {}
    journey_events: list[JourneyEntryRecordedEvent] = []
    recommendation_proposed: dict[str, RecommendationProposedEvent] = {}
    recommendation_decisions: dict[str, str] = {}  # recommendation_id -> decision

    for e in events:
        if isinstance(e, LearningSessionStartedEvent):
            session_started_events[e.session_id] = e
        elif isinstance(e, JourneyEntryRecordedEvent):
            journey_events.append(e)
        elif isinstance(e, RecommendationProposedEvent):
            recommendation_proposed[e.recommendation_id] = e
        elif isinstance(e, RecommendationDecisionEvent):
            recommendation_decisions[e.recommendation_id] = e.decision

    # Build sessions from LearningSessionStartedEvent + JourneyEntryRecordedEvent
    sessions: dict[str, LearningSession] = {}
    for session_id, start_event in session_started_events.items():
        session = LearningSession(
            session_id=session_id,
            topic=start_event.topic,
            started_at=start_event.timestamp,
        )
        # Replay journey entries for this session
        for je in journey_events:
            if je.session_id == session_id:
                if je.entry_type == "section_read":
                    if je.detail.startswith("Read section: "):
                        section_id = je.detail[len("Read section: ") :]
                        if section_id not in session.sections_read:
                            session.sections_read.append(section_id)
                elif je.entry_type == "dig_deeper":
                    session.dig_deeper_requests += 1
                elif je.entry_type == "quiz_completed":
                    session.quiz_taken = True
                    if je.score is not None:
                        session.quiz_score = je.score
                        session.quiz_passed = je.score >= 0.6
                    if je.timestamp:
                        session.completed_at = je.timestamp
        sessions[session_id] = session

    # Build journey - all JourneyEntryRecordedEvent sorted by timestamp
    journey = [
        JourneyEntry(
            timestamp=je.timestamp,
            entry_type=je.entry_type,
            topic=je.topic,
            detail=je.detail,
            score=je.score,
        )
        for je in sorted(journey_events, key=lambda x: x.timestamp)
    ]

    # Build recommendations - include pending and approved, exclude rejected
    recommendations: dict[str, Recommendation] = {}
    for rec_id, prop_event in recommendation_proposed.items():
        decision = recommendation_decisions.get(rec_id)
        if decision == "reject":
            # Rejected recommendations are excluded entirely
            continue
        rec = Recommendation(
            recommendation_id=prop_event.recommendation_id,
            concept=prop_event.concept,
            topic=prop_event.topic,
            reason=prop_event.reason,
            suggested_action=prop_event.suggested_action,
            evidence=prop_event.evidence,
            priority=prop_event.priority,
            timestamp=prop_event.timestamp,
            approved=(decision == "approved"),
            applied=(decision == "approved"),
        )
        recommendations[rec_id] = rec

    return CognitiveState(
        sessions=sessions,
        journey=journey,
        recommendations=recommendations,
    )
