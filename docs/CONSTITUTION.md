# ═══════════════════════════════════════════════════════════════
# HELIX EDUCATION CENTER — CONSTITUTION
# ═══════════════════════════════════════════════════════════════
# This document contains the absolute mandates and constraints that govern
# all development in the Helix Learning & Development system.
# ═══════════════════════════════════════════════════════════════

---

## Core Mandates

### Mandate 1: Event Sourcing is the Only Source of Truth
- **Constraint**: State is derived, never stored directly
- **Implementation**: Every fact is an immutable, timestamped event
- **Consequence**: Current state is always computed by replaying events through pure projection functions
- **Enforcement**: No direct state mutations allowed

### Mandate 2: Zero AI Dependencies in the Core
- **Constraint**: The core state engine has no AI/LLM dependencies
- **Implementation**: LLM calls are external integrations behind explicit boundaries
- **Consequence**: If AI is unavailable, the engine functions normally
- **Enforcement**: Strict import controls and interface segregation

### Mandate 3: Determinism Over Cleverness
- **Constraint**: Given the same events, the system must produce the same state
- **Implementation**: Pure functions, no hidden mutable state
- **Consequence**: Reproducible behavior for all learners
- **Enforcement**: Comprehensive testing and deterministic algorithms

### Mandate 4: Append-Only Durability
- **Constraint**: Events are never mutated or deleted
- **Implementation**: Corrections are new events, history is sacred
- **Consequence**: Immutable audit trail and full historical accuracy
- **Enforcement**: Event store enforces append-only semantics

### Mandate 5: Explicit Interfaces Over Implicit Coupling
- **Constraint**: Components communicate through defined contracts
- **Implementation**: Public APIs, clear boundaries, no internal dependencies
- **Consequence**: Maintainable, testable, modular architecture
- **Enforcement**: Interface segregation and dependency inversion

### Mandate 6: AI Protocol Compliance (NEW)
- **Constraint**: Any model interacting with this repository MUST sign in and out of ROOT_BOOT.md. Furthermore, any codebase modification MUST be accompanied by an immediate update to the relevant .md documentation files.
- **Implementation**: All AI agents must follow the sign-in/sign-out protocol in ROOT_BOOT.md
- **Consequence**: Full auditability and documentation of all changes
- **Enforcement**: Protocol violation results in rejected changes

---

## Component Responsibilities

### EventStore (`state_core/event_store.py`)

**Responsibility:** Append-only persistence of domain events.

The EventStore writes events to a JSONL file. It reads them back in order. It does not interpret them. It does not enforce business rules. It does not query by topic or filter by type. It appends, and it replays. That is all.

- Writes are atomic: each event is serialized to JSON and flushed immediately.
- Reads return all events since a given timestamp, or all events if no timestamp is provided.
- Corrupt lines are skipped with a warning. The store does not halt on malformed data.
- The SealedAnswerKeyStore is a companion: it stores answer key hashes for quiz items, ensuring scoring keys are immutable once committed.

### CognitiveEngine (`cognitive_engine/`)

**Responsibility:** Isolate all LLM and AI-dependent logic behind explicit boundaries.

The CognitiveEngine does not call LLMs. It maintains knowledge maps, tracks learner sessions, generates recommendations, and produces metacognitive insights — all from events. It reads events, updates its projections, and returns results. When an LLM is needed (e.g., to generate a lesson section), the request is routed through `cognitive_agent/`, which wraps the LLM client behind a `CognitiveAgentClient` interface.

- KnowledgeMap: projected from events. Shows weak areas, strong areas, topic progress.
- Sessions: records section reads, dig-deeper requests, quiz results.
- Recommendations: proposes next actions based on knowledge gaps.
- The LLM lives behind `OllamaAgentClient` or `StubCognitiveAgentClient`. It is never imported by the core.

### ContentEngine (`content_engine/`)

**Responsibility:** Lesson orchestration — generating, committing, and retrieving lesson sections.

The ContentEngine owns the lifecycle of lesson content. It coordinates between the grounding engine (which fetches external context), the agent service (which generates section text), and the learning service (which persists the committed section).

- `ContentService`: creates lessons, commits sections, manages section ordering.
- `GenerationOrchestrator`: composes grounding, agent, and content services to produce a section from a topic and section spec.
- `LessonOrchestrator`: the top-level pipeline. Takes a topic, section specs, and quiz specs. Generates sections, creates the quiz, commits everything, and returns a `LessonResult`.
- Sections are committed as `LessonSectionCommittedEvent` instances. The event contains the title, body, source citations, and section ID.

### QuizEngine (`quiz_engine/`)

**Responsibility:** Deterministic scoring and quiz lifecycle management.

The QuizEngine creates quizzes, manages quiz sessions, scores answers, and tracks attempt numbers. Scoring is deterministic: given the same answer and the same AnswerKey, the score is identical on every run.

- `QuizService`: creates quizzes, adds items, starts sessions, scores answers.
- Scoring is performed by `state_core/scoring_engine.py`, not by the quiz engine itself. The quiz engine delegates to it.
- Answer keys are sealed (SHA-256 hashed) at creation time. They cannot be modified after a quiz item is committed.
- Attempt numbers increment across sessions. A learner's second attempt on the same quiz item is scored against the same AnswerKey, but the attempt number is recorded.

### ProgressEngine (`progress_engine/`)

**Responsibility:** Milestones and learning path projection.

Reads events to compute milestones (section read, quiz passed, topic completed) and learning paths (ordered sequences of topics with completion status). Pure projection — no writes, no side effects.

### DeliveryEngine (`delivery_engine/`)

**Responsibility:** Feedback messages and session logging.

Generates human-readable feedback for quiz answers and session summaries. Reads events, produces feedback strings. No persistence beyond what the event store already provides.

### GroundingEngine (`grounding_engine/`)

**Responsibility:** Retrieve external context for content generation.

Provides `GroundingClient` (abstract), `StubGroundingClient` (for tests), and `HttpGroundingClient` (for production). The `GroundingService` wraps the client and adds caching. Chunks are retrieved by topic, truncated to `max_chunks`, and returned as `GroundingResult` objects.

- Stubs return canned responses.
- HTTP clients call an external retrieval API.
- The engine does not generate content. It retrieves context that the agent uses to generate content.

### CognitiveAgent (`cognitive_agent/`)

**Responsibility:** LLM client abstraction and structured response parsing.

Wraps raw LLM calls behind `CognitiveAgentClient`. Parses JSON responses into `LessonSectionDraft` objects. Validates source indices against available grounding chunks. Raises `LessonSectionGenerationError` on malformed output.

- `StubCognitiveAgentClient`: returns canned responses for tests.
- `OllamaAgentClient`: calls a local Ollama instance.
- `CognitiveAgentService`: wraps the client, exposes `generate_section()`.

---

## Compliance Requirements

### Protocol Compliance
1. **Sign-In**: All AI agents must record entry in docs/SESSION_LOG.md with agent name, timestamp, and purpose
2. **Documentation**: All modifications must update relevant .md files immediately
3. **Test Validation**: All tests must pass before modifications are accepted
4. **Audit Trail**: Complete session records must be maintained in docs/SESSION_LOG.md

### Code Quality
1. **Determinism**: All functions must be pure and deterministic
2. **Event Sourcing**: No direct state mutations allowed
3. **Interface Segregation**: Clear boundaries between components
4. **Append-Only**: No event mutations or deletions

---

## Enforcement Mechanisms

### Automated Checks
- Protocol compliance validation
- Test suite execution
- Documentation completeness verification
- Interface contract validation

### Manual Reviews
- Architecture review processes
- Code review checklists
- Documentation quality assurance
- Compliance audit procedures

---

## Future Evolution

This constitution may be updated as the system evolves. All changes:
1. Must maintain backward compatibility
2. Must follow the same constraint-based approach
3. Must be documented in this file
4. Must be approved through established processes

---

## Current Status

**Constitution Version**: 1.0
**Last Updated**: 2025-07-19
**Compliance Status**: ✅ COMPLIANT
**Active Mandates**: 6
**Components**: 7 micro-engines + 1 state core

---

## Contact & Support

For constitution violations or compliance issues:
1. Check docs/SESSION_LOG.md for recent activity
2. Review ROOT_BOOT.md for protocol requirements
3. Run compliance validation scripts
4. Contact system administrator for guidance