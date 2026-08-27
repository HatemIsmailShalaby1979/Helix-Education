# Learning Engine — State Core

Event-sourced state engine for the Helix Learning & Development system.
This is a standalone, production-grade library with **zero AI/LLM dependencies**.

> **This module has no AI/LLM dependency and must remain that way.**

---

## Event Types

| Event | Type String | Payload |
|---|---|---|
| `TopicStartedEvent` | `topic_started` | `topic: str`, `requested_level: Optional[str]`, `parent_topic: Optional[str]`, `lesson_title: Optional[str]` |
| `LessonSectionCommittedEvent` | `lesson_section_committed` | `topic: str`, `section_id: str`, `source_citations: list[str]` |
| `QuizItemCreatedEvent` | `quiz_item_created` | `topic: str`, `quiz_item_id: str`, `category: str`, `difficulty: str`, `answer_key_hash: str` |
| `AnswerSubmittedEvent` | `answer_submitted` | `quiz_item_id: str`, `raw_answer: str`, `attempt_number: int` |
| `AnswerScoredEvent` | `answer_scored` | `quiz_item_id: str`, `raw_score: float`, `passed: bool`, `scoring_method: str` |
| `TopicPassedEvent` | `topic_passed` | `topic: str`, `final_level: str`, `attempts_total: int` |
| `TopicBranchedEvent` | `topic_branched` | `parent_topic: str`, `child_topic: str`, `reason: str` |
| `ProfileDeltaProposedEvent` | `profile_delta_proposed` | `evidence: list[str]`, `proposed_changes: dict`, `approved: bool = False` |
| `LessonDeletedEvent` | `lesson_deleted` | `topic: str` |
| `ProfileDeltaApprovedEvent` | `profile_delta_approved` | `delta_event_id: str`, `approved_by: str = "user"` |

> **Note:** The event catalog is no longer a purely closed set as originally specified. Any future new event type additions must be documented in this same table at the time they are introduced.
| `LessonDeletedEvent` | `lesson_deleted` | `topic: str` |
| `ProfileDeltaApprovedEvent` | `profile_delta_approved` | `delta_event_id: str`, `approved_by: str = "user"` |
| `LearningSessionStartedEvent` | `learning_session_started` | `session_id: str`, `topic: str` |
| `JourneyEntryRecordedEvent` | `journey_entry_recorded` | `session_id: str`, `entry_type: str`, `topic: str`, `detail: str`, `score: Optional[float] = None` |
| `RecommendationProposedEvent` | `recommendation_proposed` | `recommendation_id: str`, `concept: str`, `topic: str`, `reason: str`, `suggested_action: str`, `evidence: str`, `priority: str` |
| `RecommendationDecisionEvent` | `recommendation_decision` | `recommendation_id: str`, `decision: str` ("approved" or "reject") |

> **Note:** The event catalog is no longer a purely closed set as originally specified. Any future new event type additions must be documented in this same table at the time they are introduced.

---

## Topic Deletion Behavior

Topic deletion is **reversible**. A topic is considered deleted only if its most recent lifecycle event (by timestamp) is a `LessonDeletedEvent`. If a `TopicStartedEvent` for that topic appears with a **later** timestamp than the most recent `LessonDeletedEvent`, the topic is reactivated and replays normally. This applies to both `TopicStartedEvent` and `LessonSectionCommittedEvent` during event replay.

---

## Leveling Rules

| Level | Condition |
|---|---|
| `beginner` | `pass_count == 0` |
| `intermediate` | `pass_count >= 1` and `fail_count <= pass_count` |
| `expert` | `pass_count >= 3` and `fail_count == 0` in the last 3 attempts |

These rules are deterministic, auditable, and implemented exactly as specified
in `leveling_engine.py`. No heuristics or ML are involved.

---

## Scoring Engine

The scoring engine (`scoring_engine.py`) implements a purely keyword-based
deterministic floor:

- Base score = matched required keywords / total required keywords
- Penalty = 0.1 per forbidden keyword found (clamped to 0.0 minimum)
- Pass threshold >= 0.6

Semantic matching, embeddings, or LLM verification is **out of scope** for this
deliverable and reserved for a later external layer.

---

## Architecture

```
event_models.py      - Immutable event dataclasses + serialization
event_store.py       - Append-only JSON Lines persistence + AnswerKeyStore stub
projections.py       - Pure projection functions (no side effects)
leveling_engine.py   - Deterministic level promotion/demotion rules
scoring_engine.py    - Deterministic keyword-based answer scoring
```

### Event Sourcing Invariant

- State is **never** stored directly.
- Every fact is an immutable, timestamped `Event` appended to a log.
- Current state is always **computed** by replaying events through a pure
  projection function.
- Past events are **never mutated** — only appended.

### Profile Delta Approval Gate

- `ProfileDeltaProposedEvent` has `approved: bool = False` at all times.
  This is enforced at the model level via `__post_init__`.
- Approval is granted **only** by a separate `ProfileDeltaApprovedEvent` in
  the log referencing the proposed event's `event_id`.
- The projection function (`project_learner_profile`) **never** checks the
  `approved` field on the proposed event — it looks exclusively for the
  matching approval event.
- This ensures that no unapproved delta can ever leak into `approved_traits`
  under any replay order.

---

## Running Tests

```bash
pytest -v
```
