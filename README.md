<div align="center">

# Helix Education

**The event-sourced learning engine for Helix Codex.**

![Status](https://img.shields.io/badge/status-alpha-blue)
[![CI](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/workflows/python-package.yml/badge.svg?branch=main)](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/runs/36371517881)
![Licence](https://img.shields.io/badge/licence-MIT-blue)
![Python](https://img.shields.io/badge/python-3.11%2B%20%E2%80%93%203.13-3776ab)

</div>

## One-line identity

Helix Education is the event-sourced learning engine for Helix Codex — it turns
operational knowledge into structured, auditable learning that a learner can replay
and check, not just consume.

> [!NOTE]
> **Operating principle.** Learning records are evidence, not suggestions. Learner state is reconstructed from an append-only event log, so any claim about a person's progress can be replayed and verified rather than taken on trust. The core engine has no AI dependency, so a lesson or a scored quiz can be delivered without a model in the loop.

## What it does

- Event-sourced records with state reconstruction — every change is an event, and current state is a projection of the event log.
- Citation-grounded learning content, generated through `content_engine/`.
- Sealed quiz scoring — results are written once and cannot be edited after the fact.
- Adaptive learning paths (`progress_engine/adaptive_paths/`).
- Progress and milestone tracking with a portable, inspectable learning history.
- Zero AI dependency in the core engine.

## How it fits Helix Codex

Helix Education is a **component** — the learning foundation Helix Codex would use. It
is an **independent repository with no shared codebase** with Helix Prime. Its role in
the story is real; its wiring into the core is not yet built. **Designed to supply the
learning foundation; not yet integrated into Helix Prime.** The gRPC competency
service exists in business logic (`CompetencyProfileLogic`) but its bindings are not
generated and nothing mounts it, so the integration point is identified, not connected.

## Architecture

- `state_core/` — event sourcing, scoring, projections, sealed-key store.
- `content_engine/` — citation-grounded lesson generation.
- `quiz_engine/` — assessment and scoring.
- `progress_engine/adaptive_paths/` — adaptive learning logic.
- `api_layer/grpc/` — competency contract; service wiring remains pending.

## Production status & test coverage

Stated plainly and dated. This section is last by design.

| Item | State | Snapshot |
|---|---|---|
| Tests | 447 passed | 2026-09-28 — [run 36371517881](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/runs/36371517881) |
| Core event-sourced learning state | Implemented | 2026-09-27 |
| gRPC competency service | Business logic exists; bindings not generated, registration commented out, nothing mounts it | 2026-09-27 |
| External grounding | A deterministic stub, a generic HTTP client, and a web-search client ship; the tests use the stub | 2026-09-27 |
| Production client deployment | None | 2026-09-27 |
| External audit | None | 2026-09-27 |

> [!WARNING]
> The engine core has no AI dependency. The gRPC competency service is not wired, and external grounding or LLM services are mocked or stubbed in tests. The engine has not been integrated into Helix Prime. No external audit, no certified data isolation, no signed security review, no revenue.

## Run it

Python 3.11–3.13 are covered by the `Python package` CI matrix ([run 36371517812](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/runs/36371517812), 2026-09-28 — all three jobs green).

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Try it

Replay a learner's state from an event log, then check that a sealed quiz result cannot be edited. Run from the repository root.

```python
from tempfile import TemporaryDirectory
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.event_models import AnswerScoredEvent, QuizItemCreatedEvent
from state_core.scoring_engine import AnswerKey
from state_core.projections import project_topic_state
from learning_service import LearningService

with TemporaryDirectory() as tmp:
    store = EventStore(StoreConfig(path=f"{tmp}/learner.jsonl"))
    svc = LearningService(store, SealedAnswerKeyStore(StoreConfig(path="", sealed_keys_path=f"{tmp}/keys.jsonl")))
    svc.create_quiz_item("safeguarding", "saf-1", "q1", "Name the four categories.", "short_answer", "easy",
                         AnswerKey(required_keywords=["physical", "emotional", "neglect", "sexual"]))
    svc.submit_and_score_answer("q1", "physical, emotional, neglect and sexual harm")
    state = project_topic_state(store.read_all(), "safeguarding")
    next(e for e in store.read_all() if isinstance(e, AnswerScoredEvent)).raw_score = 0.0  # rewrite attempt
    print("replayed :", state.topic, "| attempts", state.attempts_total, "| passes", state.pass_count)
    print("sealed   :", next(e.answer_key_hash for e in store.read_all() if isinstance(e, QuizItemCreatedEvent))[:16])
    print("edit API :", [m for m in ("update", "delete", "remove") if hasattr(store, m)] or "none (append-only)")
    print("persisted:", next(e.raw_score for e in store.read_all() if isinstance(e, AnswerScoredEvent)))
```

Real output (2026-10-01, Python 3.13.12):

```
replayed : safeguarding | attempts 1 | passes 1
sealed   : 6ec99c50195ae0a7
edit API : none (append-only)
persisted: 1.0
```

The learner state is rebuilt from the log alone — nothing is carried in memory between the write and the replay. The last three lines are the sealing check: the store exposes no `update`, `delete` or `remove`, only `append`, so the rewrite attempt on the in-memory event never reaches the persisted record, which still reads `1.0`. The answer key is never written to the log; only its SHA-256 hash appears in the `QuizItemCreatedEvent`.

Scope of that guarantee, stated precisely: it is an append-only guarantee at the store API level. The key store writes plaintext JSONL, and neither the log nor the key file is cryptographically tamper-evident on disk. `EncryptedSealedKeyStore` and the Vault adapter exist in the tree but are not the default path.

## Related work

- [How this project fits the wider work](https://github.com/HatemIsmailShalaby1979/HatemIsmailShalaby1979)

## Author

**Hatem Ismail Shalaby** — Operations Architect · AI Systems Engineer · Founder

- GitHub: [HatemIsmailShalaby1979](https://github.com/HatemIsmailShalaby1979)
- LinkedIn: [hatem-shalaby-202902127](https://www.linkedin.com/in/hatem-shalaby-202902127/)
- Email: hatemshalaby2025@gmail.com
- Education: BSc Managerial Sciences (Computer Section), Sadat Academy for Management Sciences; Business Analytics Nanodegree, Udacity

Based in Al Obour City, Al-Qalyubia Governorate, Egypt.

## Licence

MIT
