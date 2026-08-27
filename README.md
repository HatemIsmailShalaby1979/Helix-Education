# Helix Education L&D Engine

Helix Education is an event-sourced learning state engine for building and tracking
learning journeys. It is a standalone, well-tested codebase that is not yet connected
to Helix Prime in production.

## Current status

Helix Education is **alpha**. It is a real and built learning engine with an extensive
test suite, but live end-to-end operation is not yet separately verified: its test suite
uses mocked or stub clients for external services (grounding search, LLM), which is
correct testing practice but means no production integration has been exercised yet.

- **447 passing tests** (pytest, verified 2026-08-04).
- Not connected to Helix Prime in production.
- No client deployments and no production enterprise usage.
- A gRPC competency contract is defined, but network bindings are pending: generated
  stubs are not wired in, so there is no functional gRPC service yet.

## What it does

- **Event-sourced state core:** append-only event store with full state reconstruction.
- **Content generation with citation grounding:** generated content is validated
  against a citation index to prevent hallucinated material.
- **Quiz scoring with sealed answer keys:** answer keys are sealed and exchanged
  through a store, replacing plaintext JSONL storage.
- **Adaptive learning paths:** learning paths adjust based on quiz performance.
- **Progress tracking and projections:** milestones, scoring, and state mutators.

## Tech stack

- Python 3.11+ (targets 3.13)
- Event sourcing (no database dependency)
- Pydantic models
- Tested with pytest (447 tests)
- Zero AI dependencies in the core engine

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
```

## Run tests

```bash
pytest -q
```

## Repository layout

```text
state_core/        Event sourcing, scoring, projections, sealed-key store
content_engine/    Lesson and content generation with citation grounding
quiz_engine/       Quiz modeling and scoring
progress_engine/   Progress tracking, adaptive paths, promotion readiness
learning_service/  Learning service layer
api_layer/         REST and gRPC contract definitions
cognitive_engine/  Cognitive engine and ML model experiments
grounding_engine/  Grounding client and models
helix_education/   Package entry points (CLI, web servers)
tests/             Test suite
```

## Verification status

The 447-test suite passes. This covers content generation with citation-grounding
validation, quiz scoring, adaptive learning paths, and full event-sourcing state
reconstruction. Live end-to-end operation with real external services is not yet
separately verified.

There is known, non-functional lint debt (ruff findings, mostly line length and
style) that is real but low-priority cleanup.

Part of a larger body of work — see [Hatem Shalaby's profile](https://github.com/HatemShelby) for the full story.
