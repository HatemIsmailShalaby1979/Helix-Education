# Architecture

## Constitution 000 — Day Zero

The following principles are not aspirational. They are constraints. Every design decision in this codebase was made under them, and every future decision must obey them.

1. **Event sourcing is the only source of truth.** State is derived, never stored directly. If it cannot be reconstructed from events, it does not exist.
2. **No AI dependencies in the core.** LLM calls are external integrations. The engine scores, stores, and retrieves without them. If the AI is unavailable, the engine functions.
3. **Determinism over cleverness.** Given the same events, the system must produce the same state. Every time. Without exception.
4. **Append-only durability.** Events are never mutated or deleted. Corrections are new events. History is sacred.
5. **Explicit interfaces over implicit coupling.** Components communicate through defined contracts. One component does not reach into another's internals.

These are not guidelines. They are the constitution. Violations are bugs, regardless of whether they pass tests.

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

### State Mutator (`state_core/state_mutator.py`)

**Responsibility:** Controlled, auditable state modifications while maintaining event sourcing principles.

The State Mutator provides safe state updates with full audit trails:

- **Controlled Mutations**: Safe state updates with full audit trails
- **Event Validation**: Ensures all mutations follow business rules
- **Rollback Capability**: Can revert state changes through event replay
- **Compliance Enforcement**: Guarantees adherence to constitutional mandates

The State Mutator works in conjunction with the EventStore to maintain system integrity while allowing necessary operational flexibility. It ensures that all state changes are properly documented and auditable.

### Observability Dashboard (`observability/`)  

**Responsibility:** Comprehensive system visibility and monitoring.

The Observability Dashboard provides real-time system insights:

- **Real-time Metrics**: Track system performance, response times, and error rates
- **Historical Analysis**: Review trends and patterns over time
- **Health Monitoring**: Monitor system health and compliance status
- **Alerting**: Configure notifications for critical events and anomalies

The dashboard integrates with all micro-engines to provide a unified view of system operations and supports the Metacognitive Loop's continuous improvement process.

### Metacognitive Loop (`cognitive_engine/metacognitive_loop.py`)

**Responsibility:** Self-improving framework for continuous system enhancement.

The Metacognitive Loop enables the system to:

1. **Monitor**: Track performance metrics, error rates, and user interactions
2. **Analyze**: Identify patterns, bottlenecks, and optimization opportunities
3. **Reflect**: Evaluate effectiveness and identify improvement areas
4. **Act**: Implement optimizations and enhancements

This loop is implemented through the Observability Dashboard and State Mutator components, creating a continuous improvement cycle that enhances system performance and user experience over time.

### AI Protocol & Documentation Engine (`ROOT_BOOT.md`, `CONSTITUTION.md`, `SESSION_LOG.md`)

**Responsibility:** AI agent protocol and documentation compliance.

The AI Protocol & Documentation Engine ensures:

- **Sign-In/Sign-Out**: All AI agents must authenticate through ROOT_BOOT.md
- **Documentation Compliance**: Every code change requires immediate .md file updates
- **Audit Trail**: Complete session records maintained in SESSION_LOG.md
- **Protocol Enforcement**: Constitutional mandates for AI interaction

This system is documented in:
- `ROOT_BOOT.md`: AI agent protocol and sign-in/sign-out requirements
- `CONSTITUTION.md`: Core mandates including AI protocol compliance
- `SESSION_LOG.md`: Complete audit trail of all agent sessions
