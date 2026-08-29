![CI](https://github.com/HatemIsmailShalaby1979/helix-education/actions/workflows/python-app.yml/badge.svg)
![License](https://img.shields.io/github/license/HatemIsmailShalaby1979/helix-education)
![Release](https://img.shields.io/github/v/release/HatemIsmailShalaby1979/helix-education)

# Helix Education

> **An event-sourced learning engine built for accountable progress.**

Helix Education is a standalone learning-state engine designed around replayable events, citation-grounded content, sealed assessment, adaptive paths, and inspectable learner progress.

It is a sibling system in the Helix ecosystem — not yet a production-integrated module of Helix Prime.

## Verified status

- **Alpha / research product**
- **447 tests passing** in the current CI-supported build
- Core event-sourced learning state is implemented
- External grounding and LLM services are mocked or stubbed in tests
- gRPC competency contracts exist, but a functional gRPC service is not yet wired
- No production client deployment is claimed

## Core capabilities

- Event-sourced records with state reconstruction
- Citation-grounded learning content
- Sealed quiz scoring
- Adaptive learning paths
- Progress and milestone tracking
- Portable, inspectable learning history
- Zero AI dependency in the core engine

## Why it matters to Helix Codex

Helix Education provides the learning and development foundation for the broader Codex direction: operational knowledge can become structured learning, outcomes can improve future training, progress can remain auditable, and learning records can preserve context.

## Download and install

- [Download current source ZIP](https://github.com/HatemIsmailShalaby1979/Helix-Education/archive/refs/heads/main.zip)
- [View releases](https://github.com/HatemIsmailShalaby1979/Helix-Education/releases)

### Windows

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
```

### Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
```

Python 3.11–3.13 are supported by current CI workflows.

## Layout

- `state_core/` — event sourcing, scoring, projections, sealed-key store
- `content_engine/` — citation-grounded lesson generation
- `quiz_engine/` — assessment and scoring
- `learning_path/` — adaptive learning logic
- `grpc/` — competency contract; service wiring remains pending

## Honest boundary

The project is a verified standalone engine and a strong ecosystem component. It is not presented as a production learning platform or as fully integrated with Helix Prime.

## Related projects

- [Helix Prime](https://github.com/HatemIsmailShalaby1979/Helix-Prime)
- [Study Studio](https://github.com/HatemIsmailShalaby1979/Study-Studio)
- [L&D Command Center](https://github.com/HatemIsmailShalaby1979/L-D-Command-Center)

## License

MIT

Part of a larger body of work — see [Hatem Shalaby's profile](https://github.com/HatemIsmailShalaby1979) for the full story.
