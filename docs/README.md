# Helix Education — WILI L&D Department

**Status:** Phase 2 Complete — Ready for Phase 3 (Advanced Capabilities)  
**Integration:** Integrated as Learning & Development department of Helix Prime  
**Test Coverage:** 447 tests passing, >95% coverage verified

Event-sourced learning state engine. Zero AI dependencies at the core.

## What is this?

A deterministic, event-sourced state engine for educational content, now serving as the **Learning & Development (L&D) department** of Helix Prime under WILI (Learning & Development Director). It manages lesson sections, quiz items, scoring, and learner progression through an append-only event store. No LLM calls are made by the engine itself. AI integration, when needed, is isolated behind explicit client interfaces that live outside the core.

## Why is this necessary?

Educational state must be reproducible. If a learner answers a question, the system must produce the same score on the tenth run as it did on the first. Event sourcing guarantees this: every state change is recorded as an immutable fact, and current state is derived by replaying those facts. There is no hidden mutable state. There are no silent failures. The system either commits an event or it does not.

## Installation

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode along with development dependencies (`pytest`, `ruff`).

## Running the tests

```bash
pytest
```

447 tests. All must pass. The CI pipeline enforces this on every commit to `main`. Current coverage: >95%.

## Running the lesson generator

```bash
python -m scripts.run_full_lesson_with_quiz
```

This executes the full lesson generation pipeline against local stubs and a local Ollama instance. It produces three lesson sections and a three-item quiz, then verifies the event store contains the expected committed events.

## Linting and formatting

```bash
ruff format --check .
ruff check .
```

`ruff` is the sole linter and formatter. Configuration lives in `pyproject.toml`.

## Project structure

```text
state_core/          Event store, scoring engine, event models
learning_service/    Topic lifecycle, learner profiles
content_engine/      Lesson orchestration, section generation
quiz_engine/         Quiz creation, session management, scoring
progress_engine/     Milestones, learning paths
delivery_engine/     Feedback, session logging
cognitive_engine/    Knowledge maps, recommendations
grounding_engine/    External context retrieval (RAG stubs and clients)
cognitive_agent/     LLM client abstraction, section generation
api_layer/           HTTP router, request/response models
helix_education/     CLI entry point
scripts/             Runnable scripts for end-to-end verification
tests/               447 tests covering all engines (>95% coverage)
```

## Metacognitive Loop

The Metacognitive Loop is a self-improving framework that enables the system to:

1. **Monitor**: Track performance metrics, error rates, and user interactions
2. **Analyze**: Identify patterns, bottlenecks, and optimization opportunities
3. **Reflect**: Evaluate effectiveness and identify improvement areas
4. **Act**: Implement optimizations and enhancements

This loop is implemented through the Observability Dashboard and State Mutator components, creating a continuous improvement cycle.

## State Mutator

The State Mutator provides controlled, auditable state modifications while maintaining event sourcing principles:

- **Controlled Mutations**: Safe state updates with full audit trails
- **Event Validation**: Ensures all mutations follow business rules
- **Rollback Capability**: Can revert state changes through event replay
- **Compliance Enforcement**: Guarantees adherence to constitutional mandates

The State Mutator works in conjunction with the EventStore to maintain system integrity while allowing necessary operational flexibility.

## Observability Dashboard

The Observability Dashboard provides comprehensive system visibility:

- **Real-time Metrics**: Track system performance, response times, and error rates
- **Historical Analysis**: Review trends and patterns over time
- **Health Monitoring**: Monitor system health and compliance status
- **Alerting**: Configure notifications for critical events and anomalies

The dashboard integrates with all micro-engines to provide a unified view of system operations and supports the Metacognitive Loop's continuous improvement process.

## AI Protocol & Documentation Engine

The AI Protocol & Documentation Engine ensures:

- **Sign-In/Sign-Out**: All AI agents must authenticate through ROOT_BOOT.md
- **Documentation Compliance**: Every code change requires immediate .md file updates
- **Audit Trail**: Complete session records maintained in SESSION_LOG.md
- **Protocol Enforcement**: Constitutional mandates for AI interaction

This system is documented in:
- `ROOT_BOOT.md`: AI agent protocol and sign-in/sign-out requirements
- `CONSTITUTION.md`: Core mandates including AI protocol compliance
- `SESSION_LOG.md`: Complete audit trail of all agent sessions

## System Architecture

The system follows a micro-engine architecture with clear separation of concerns:

### Core Components
- **State Core**: Event-sourced state engine with zero AI dependencies
- **7 Micro-Engines**: Specialized components for different aspects of learning
- **API Layer**: HTTP interface for external interactions
- **CLI Entry Point**: Command-line interface for system operations

### Key Principles
1. **Event Sourcing**: State is derived, never stored directly
2. **Determinism**: Reproducible behavior for all learners
3. **Append-Only**: Immutable audit trail and full historical accuracy
4. **Explicit Interfaces**: Clear boundaries between components
5. **Zero AI Dependencies**: Core engine has no AI/LLM dependencies

### Compliance Framework
- **Constitutional Mandates**: 6 absolute constraints governing all development
- **Protocol Enforcement**: AI agent sign-in/sign-out requirements
- **Test Validation**: All 393 tests must pass before modifications
- **Documentation Requirements**: Immediate .md file updates for all changes

---

## Additional Resources

For more detailed information about specific components:

- **State Core Documentation**: `README_STATE_CORE.md` - Detailed event catalog and leveling rules
- **Architecture Documentation**: `docs/ARCHITECTURE.md` - Component responsibilities and design patterns
- **System Analysis**: `SYSTEM_ANALYSIS.md` - Technical architecture and implementation details
- **Learning Records**: `LEARNING-RECORDS/` - Historical learning session documentation

---

## Getting Started

1. **Install the system**:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Run tests**:
   ```bash
   pytest
   ```

3. **Generate lessons**:
   ```bash
   python -m scripts.run_full_lesson_with_quiz
   ```

4. **Lint and format**:
   ```bash
   ruff format --check .
   ruff check .
   ```

---

## Compliance Status

**Constitution Version**: 1.0
**Last Updated**: 2025-07-19
**Compliance Status**: ✅ COMPLIANT
**Active Mandates**: 6
**Components**: 7 micro-engines + 1 state core
**Metacognitive Loop**: ✅ IMPLEMENTED
**State Mutator**: ✅ OPERATIONAL
**Observability Dashboard**: ✅ ACTIVE
**AI Protocol**: ✅ ENFORCED

## CI Notes

- Ensure CI creates the sealed answer-key file used by tests at `.sealed_answer_keys.jsonl` with restrictive file permissions (owner-only read/write). On Linux runners set umask or use `install -m 600`/`chmod 600` after creation. On Windows runners restrict ACLs to the build user.
- CI must create the file (empty) before tests run to avoid permission or concurrency issues and ensure deterministic test environments.
- Add a dedicated CI step to validate the sealed keys file is present and unreadable by non-build users.
- Plan a follow-up decision/implementation to migrate sealed key storage to a KMS-backed sealed store (encrypt at rest, rotate keys, RBAC access). See DEC-2026-0002 for context.

