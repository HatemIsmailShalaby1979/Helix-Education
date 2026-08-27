# Helix Education Center — System Analysis & Architecture

---

## 1. SYSTEM OVERVIEW

The Helix Education Center is an **event-sourced learning state engine**
built as a standalone, zero-AI-dependency Python library. It tracks a
learner's journey through topics, lessons, quizzes, and proficiency
levels using an immutable append-only event log.

**Core Philosophy:**
- Every fact is an Event. State is always computed, never stored.
- Past events are immutable. Corrections are new events.
- Deterministic rules for scoring and leveling.
- No semantic/AI matching in the core — that's a separate layer.

**Actors:**
- **Learner** — studies topics, submits answers, progresses through levels
- **Instructor/System** — creates quiz items, commits lessons, approves profile deltas
- **Admin** — reviews pending deltas, manages content

---

## 2. ARCHITECTURE DIAGRAM

```text
┌────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                              │
│  (Future: CLI, Dashboard, API Consumer)                              │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│                      API LAYER (routes.py)                           │
│  REST endpoints that wrap the Orchestration Layer                    │
│                                                                      │
│  POST /topics          POST /lessons          GET /profile           │
│  POST /quizzes         POST /answers          GET /topics/{id}      │
│  POST /deltas          POST /approvals                              │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────────┐
│                  ORCHESTRATION LAYER                                  │
│              (learning_service.py)                                    │
│                                                                      │
│  Coordinates multi-step workflows across micro-engines:              │
│  • start_topic() → start lesson → create quiz items → sequence      │
│  • submit_answer() → score → check level → emit events              │
│  • propose_delta() → store → (later) approve_delta()                │
│  • get_state() → read events → project → return                     │
└──────┬──────────┬──────────┬──────────┬──────────┬──────────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│ CONTENT  │ │  QUIZ    │ │PROGRESS  │ │ DELIVERY │ │   STATE      │
│ ENGINE   │ │ ENGINE   │ │ ENGINE   │ │ ENGINE   │ │   CORE       │
│          │ │          │ │          │ │          │ │              │
│ Content  │ │ Quiz gen │ │ Learning │ │Feedback  │ │ Event Store  │
│ Models   │ │ Quiz     │ │ Paths    │ │Rendering │ │ Projections  │
│ Storage  │ │ Service  │ │Tracking  │ │Templates │ │ Leveling     │
│          │ │          │ │          │ │          │ │ Scoring      │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘
                                                              │
                                                              ▼
                                                    ┌──────────────────┐
                                                    │  EVENT LOG       │
                                                    │  (JSON Lines)    │
                                                    │  Append-only     │
                                                    │  Flushed on each │
                                                    │  write           │
                                                    └──────────────────┘
```

---

## 3. DATA FLOW — Complete Learning Cycle

```text
START TOPIC
    │
    ▼
[TopicStartedEvent] ─────────► event_store.append()
    │
    ▼
LESSON SECTION
    │
    ▼
[LessonSectionCommittedEvent] ──► event_store.append()
    │
    ▼
CREATE QUIZ ITEM
    │
    ├──► AnswerKey ──► SealedAnswerKeyStore.store()  (sealed, not in event log)
    └──► [QuizItemCreatedEvent] ──► event_store.append()  (hash only)
    │
    ▼
LEARNER SUBMITS ANSWER
    │
    ▼
[AnswerSubmittedEvent] ──► event_store.append()
    │
    ▼
SCORE ANSWER
    │
    ├──► scoring_engine.score_answer(answer, key_from_sealed_store)
    │
    ▼
[AnswerScoredEvent] ──► event_store.append()
    │
    ▼
PROJECT TOPIC STATE
    │
    ├──► projections.project_topic_state(all_events, topic)
    │
    ▼
CHECK LEVEL
    │
    ├──► leveling_engine.compute_level(topic_state)
    │
    ▼
IF PASSED: [TopicPassedEvent] ──► event_store.append()
IF DIG DEEPER: [TopicBranchedEvent] ──► event_store.append()
```

---

## 4. EVENT FLOW MAP

```text
TopicStartedEvent
    │
    ├──► LessonSectionCommittedEvent
    │       │
    │       └──► QuizItemCreatedEvent (answer_key_hash stored in event;
    │                                  raw key in SealedAnswerKeyStore)
    │               │
    │               └──► AnswerSubmittedEvent
    │                       │
    │                       └──► AnswerScoredEvent
    │                               │
    │                               ├──► TopicPassedEvent  (if threshold met)
    │                               │
    │                               └──► TopicBranchedEvent (if dig deeper)
    │
    └──► ProfileDeltaProposedEvent
            │
            └──► ProfileDeltaApprovedEvent  (separate approval gate)
```

---

## 5. COMPONENT ANALYSIS

### 5.1 State Core (BUILT — 74 tests passing)

| Module | Lines | Responsibility | Dependencies |
|--------|-------|----------------|-------------|
| `event_models.py` | 173 | 9 event types + serialization | stdlib only |
| `event_store.py` | 159 | Append-only JSON Lines + AnswerKeyStore stub | stdlib only |
| `projections.py` | 185 | Pure state projection functions | event_models |
| `leveling_engine.py` | 39 | Deterministic level rules | projections |
| `scoring_engine.py` | 104 | Keyword-based deterministic scoring | stdlib only |

**Strengths:**
- Zero external dependencies (stdlib only)
- Complete type hints
- Immutable event log, append-only
- Corruption-tolerant replay
- Approval-gate enforcement proven by test

**Gaps (out of scope for State Core but needed for full system):**
- No service/orchestration layer
- No content management
- No quiz generation logic
- No delivery/rendering
- No API
- No packaging/pyproject.toml

### 5.2 Content Engine (BUILT — 14 tests)

Manages lesson content, sections, and source materials with
event-sourced rebuild and auto-creation. See `content_engine/`.

### 5.3 Quiz Engine (BUILT — 21 tests)

Manages quiz creation, items, sessions, results, and summaries.
Active sessions are in-memory (lost on restart). See `quiz_engine/`.

### 5.4 Progress Engine (BUILT — 11 tests)

Computes milestones, learning paths, and topic summaries from the
event log. Pure query service. See `progress_engine/`.

### 5.5 Delivery Engine (BUILT — 12 tests)

Generates human-readable feedback for scores, topic progress, and
session logging. Pure transformations. See `delivery_engine/`.

### 5.6 API Layer (BUILT — 14 tests)

Framework-agnostic Router with 12 endpoints covering topics, lessons,
quizzes, sessions, answers, and knowledge map. See `api_layer/`.

### 5.7 Cognitive Engine (BUILT — untested ⚠️)

Knowledge maps, recommendations, metacognitive insights, session tracking,
and HITL approval. Powers the CLI and web UI recommendation flows.
See `cognitive_engine/`.

### 5.8 Agent Bridge (BUILT — untested ⚠️)

10 CLI commands for AI agent integration: create-lesson, add-section,
create-quiz, add-quiz-item, start-topic, list-topics, list-quizzes,
get-lesson, get-knowledge-map, get-profile. See `helix_education/agent_tools.py`.

---

## 6. CURRENT STATE ASSESSMENT

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **State Management** | ✅ Solid | Event-sourced, append-only, projection-based |
| **Test Coverage** | ✅ Strong | 165 tests, all passing, covers corruption, edge cases, leak-proof |
| **Type Safety** | ✅ Full | Complete type hints on all public functions |
| **Documentation** | ⚠️ Partial | README_STATE_CORE.md current; SYSTEM_ANALYSIS.md requires version sync |
| **Service Layer** | ✅ Built | LearningService orchestrates all engines |
| **Content Management** | ✅ Built | ContentService with lesson/section CRUD + event rebuild |
| **Quiz Management** | ✅ Built | QuizService with sessions, items, results, summaries |
| **Progress Tracking** | ✅ Built | ProgressService: milestones, learning paths, topic summaries |
| **Delivery / Feedback** | ✅ Built | FeedbackService: score + topic progress + session logging |
| **Cognitive Engine** | ✅ Built | Knowledge maps, recommendations, metacognitive insights, HITL |
| **API / Integration** | ✅ Built | Router (12 endpoints), agent_tools bridge (10 commands) |
| **Packaging** | ✅ Built | pyproject.toml, pip install, helix-learn + helix-web entry points |
| **CLI** | ✅ Built | Interactive CLI with dashboard, learn, quiz, profile, map, HITL |
| **Web UI** | ✅ Built | http.server-based UI with dashboard, lessons, quiz, map, recommendations |
| **CI/CD** | ❌ Missing | No test automation in CI |

---

## 7. RISK ANALYSIS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LLM dependency creep | Medium | High | Enforce "zero AI deps" in CI; code review gate |
| Event schema drift | Low | High | Versioned event types with migration tests |
| File corruption | Low | Medium | Per-line corruption tolerance + logging |
| Concurrency on event store | Low | Medium | Flush-on-write + append-only (no locking needed for single writer) |
| Scope creep (building too much) | Medium | Medium | Micro-engine strategy — each is independently buildable |
| Hardcoded paths | Low | Medium | Config-injection pattern enforced |

---

## 8. COMPETITIVE STRATEGY ANALYSIS

Two fundamentally different architectures were evaluated for extending
the State Core into a complete Education Center.

---

### STRATEGY A: Unified Monolithic Service Layer

**Concept:** Build a single `learning_service.py` that imports from all
engines directly. All business logic lives in one package with internal
module separation but no package boundaries.

**Architecture:**
```text
helix_education/
├── state_core/          (5 files — existing)
├── learning_service.py  (single orchestrator)
├── content/             (module)
├── quiz/                (module)
├── progress/            (module)
├── delivery/            (module)
├── api.py               (simple HTTP wrapper)
└── pyproject.toml
```

**Communication:** Direct Python function calls. Engine A calls Engine B.

**Pros:**
- Simplest to build — one package, one import graph
- Fastest time-to-completion
- Single test suite, single pytest run
- Easy to debug (linear call stack)
- No inter-process or serialization overhead

**Cons:**
- Tight coupling — changing Engine A can break Engine B
- Cannot develop/test engines independently in isolation
- Monolith grows without clear boundaries
- Hard to replace an engine without touching everything
- Violates Single Responsibility Principle over time
- If one module has a bug, the whole system is down

**Test Strategy:** One `test_learning_service.py` with integration tests
that exercise the full stack. Unit tests for individual modules.

**Scalability:** Poor. The entire system must be deployed as one unit.

**Best for:** Prototypes, small teams, simple workflows with < 5 developers.

---

### STRATEGY B: Event-Driven Micro-Engine Architecture

**Concept:** Each engine is an independent package with its own namespace,
test suite, and lifecycle. Engines communicate *exclusively* through the
EventStore — Engine A appends an event; Engine B reads and reacts.

**Architecture:**
```text
helix_education/                    ← umbrella namespace
├── state_core/                     ← foundation package
│   ├── event_models.py
│   ├── event_store.py
│   ├── projections.py
│   ├── leveling_engine.py
│   └── scoring_engine.py
├── content_engine/                 ← independent micro-engine
├── quiz_engine/                    ← independent micro-engine
├── progress_engine/                ← independent micro-engine
├── delivery_engine/                ← independent micro-engine
├── api_layer/                      ← REST adapter
├── shared/                         ← shared config, types, test helpers
├── conftest.py                     ← root test fixtures
└── pyproject.toml
```

**Communication:** Events via EventStore + direct queries via projection
functions. Engine A has no reference to Engine B's internals.

```text
Engine A → EventStore.append(event)
Engine B → EventStore.read_all() → project(event) → react
```

**Pros:**
- **Loose coupling** — engines depend only on state_core, not each other
- **Independent testability** — each engine's tests run in isolation
- **Parallel development** — multiple engines can be built simultaneously
- **Swap-ability** — replace any engine without touching others
- **Event-sourcing alignment** — this pattern is the natural extension of
  the existing event-sourced foundation
- **Scalability** — each engine can be deployed independently if needed
- **Resilience** — one engine's bug does not crash the others

**Cons:**
- More complex upfront design
- Higher initial development time
- Requires careful interface contracts
- More test infrastructure (per-engine conftest.py, fixtures)
- Over-engineered if the system never grows beyond 3 engines

**Test Strategy:**
- Each engine has its own test file(s) with isolated fixtures
- Integration tests span engines via the EventStore
- The critical leak-proof test lives at the projection level

**Scalability:** Excellent. Engines can be split into separate processes
or services if needed, connected by the same event log.

**Best for:** Long-lived systems, multiple developers, event-sourced
architectures, systems that will grow over time.

---

### HEAD-TO-HEAD COMPARISON

| Criteria | Strategy A (Monolithic) | Strategy B (Micro-Engine) |
|----------|------------------------|--------------------------|
| Build speed | ✅ Fast | ⚠️ Medium |
| Test isolation | ❌ Weak | ✅ Strong |
| Coupling | ❌ Tight | ✅ Loose |
| Aligns with event sourcing | ❌ No | ✅ Yes |
| Independent deployability | ❌ No | ✅ Yes |
| Swap-ability | ❌ Hard | ✅ Easy |
| Over-engineering risk | ✅ Low | ⚠️ Medium |
| Debug-ability | ✅ Easy | ⚠️ Needs event tracing |
| Long-term maintainability | ❌ Poor | ✅ Excellent |

---

## 9. WINNER: STRATEGY B — Event-Driven Micro-Engine Architecture

### Rationale

Strategy B is the winner for these non-negotiable reasons:

1. **Event sourcing demands event-driven communication.**
   The State Core already treats every fact as an Event. Extending this
   pattern to inter-engine communication is the natural, consistent
   evolution. Strategy A would create a schism where the state layer is
   event-sourced but the service layer uses direct calls — architectural
   inconsistency.

2. **The approval-gate enforcement pattern scales to engines.**
   Just as a `ProfileDeltaProposedEvent` requires a separate
   `ProfileDeltaApprovedEvent`, an engine reacting to another engine's
   events via the store enforces temporal decoupling. This is proven
   working by the existing 74-test suite.

3. **Independent testability is a hard requirement.**
   The spec demands "every module must be independently unit-testable."
   Strategy B makes this natural — each engine has its own test suite
   with in-memory EventStores as fixtures. Strategy A makes it
   impossible without significant test doubles.

4. **Zero-AI constraint is easier to enforce.**
   With micro-engines, the gate is clear: each engine's `requirements.txt`
   is auditable. Strategy A's single import graph makes it easy for an
   LLM dependency to leak in through a side import.

5. **Future LLM adapter layer slots in cleanly.**
   When the semantic verification layer is added later, it becomes
   another micro-engine that reads events and appends results. No
   existing code changes.

### Implementation Plan

The build order follows dependency chains:

```text
Phase 1: Shared Infrastructure (now)
├── pyproject.toml + conftest.py
├── Move state_core into subdirectory
└── Verify: 74 tests still pass

Phase 2: Learning Service (winning strategy execution)
├── learning_service.py    ← orchestrates workflows
├── test_learning_service.py
└── Verify: new tests pass

Phase 3: Content Engine
├── content_engine/
│   ├── __init__.py
│   ├── content_models.py
│   ├── content_service.py
│   └── test_content_service.py
└── Verify: new tests pass + all prior pass

Phase 4: Quiz Engine
├── quiz_engine/
│   ├── __init__.py
│   ├── quiz_models.py
│   ├── quiz_service.py
│   └── test_quiz_service.py
└── Verify: new tests pass + all prior pass

Phase 5: Progress Engine
├── progress_engine/
│   ├── __init__.py
│   ├── progress_models.py
│   ├── pathway_service.py
│   └── test_progress_service.py
└── Verify: new tests pass + all prior pass

Phase 6: Delivery Engine
├── delivery_engine/
│   ├── __init__.py
│   ├── delivery_models.py
│   ├── feedback_service.py
│   └── test_delivery_service.py
└── Verify: new tests pass + all prior pass

Phase 7: API Layer
├── api_layer/
│   ├── __init__.py
│   ├── routes.py
│   └── test_api.py
└── Verify: new tests pass + all prior pass

Phase 8: Package + Deploy
├── Build wheel
├── pip install
├── Full test suite
└── Tag release
```

---

## 10. BUILD + TEST + DOCUMENT LOOP

Each phase follows this cycle:

```text
┌──────────────────┐
│  DESIGN          │  Write module docstring + public API
│  (doc first)     │  Define dataclasses / function signatures
└────────┬─────────┘
         ▼
┌──────────────────┐
│  BUILD           │  Implement functions (pure where possible)
│  (test first)    │  Write test BEFORE implementation
└────────┬─────────┘
         ▼
┌──────────────────┐
│  TEST            │  Run `pytest -v --tb=short`
│  (verify)        │  ALL tests must pass
└────────┬─────────┘
         ▼
┌──────────────────┐
│  DOCUMENT        │  Update README, module docstrings
│  (commit)        │  Record in SESSION_LOG.md
└────────┬─────────┘
         ▼
    NEXT PHASE
```

---

*Analysis updated 2026-07-17. Architecture: Strategy B — Event-Driven Micro-Engine Architecture.
System baseline: 201 tests passing (165 prior + 36 new for cognitive engine + agent tools),
stdlib-only core, AI agent layer via opencode bridge.*

