# Helix Education

Event-sourced learning state engine. Standalone. Well-tested. Not yet wired into Helix Prime.

## What it does

- **Event-sourced core** ? Append-only event store with full state reconstruction. No database needed.
- **Citation-grounded content** ? Generated material validated against a citation index to prevent hallucination.
- **Sealed quiz scoring** ? Answer keys sealed and exchanged through a store, not plaintext JSONL.
- **Adaptive paths** ? Learning paths adjust based on quiz performance.
- **Progress tracking** ? Milestones, scoring, state mutators.

## Honest status

**Alpha.** 447 passing tests (pytest, verified 2026-08-04). Core engine is solid.

What's not done: gRPC competency contract is defined but stubs aren't wired in ? no functional gRPC service yet. Not connected to Helix Prime in production. No client deployments.

Tests use mocked/stubbed external services (grounding search, LLM) ? correct testing practice, but means no live integration exercised.

## Install

`ash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
`

## Run tests

`ash
pytest -q
`

## Layout

`
state_core/        Event sourcing, scoring, projections, sealed-key store
content_engine/    Lesson/content generation with citation grounding
quiz_engine/       Quiz modeling and scoring
learning_path/     Adaptive path logic
grpc/              Competency contract (stubs not wired)
`

## Why this exists

I needed a learning engine that's auditable (event sourcing), honest (citation grounding), and testable (sealed keys). Built it separate so it can be used independently or plugged into Helix Prime later.

## Stack

- Python 3.11+ (targets 3.13)
- Pydantic for models
- pytest for tests (447)
- Zero AI dependencies in core engine

## License

MIT