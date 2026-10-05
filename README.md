<div align="center">

# Helix Education


<!-- badges:start -->

[![CI](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/workflows/Python%20application/badge.svg)](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions)
![licence](https://img.shields.io/badge/licence-MIT-blue)
[![last commit](https://img.shields.io/github/last-commit/HatemIsmailShalaby1979/Helix-Education)](https://github.com/HatemIsmailShalaby1979/Helix-Education/commits/main)
![status](https://img.shields.io/badge/ci-success-brightgreen?label=success%20(2026-10-05))

*Measured 2026-10-06 — CI **success**; head `bd66e8f` (2026-10-05); Python.*

<!-- No static test or coverage count is shown here: a frozen
     number decays silently. Run the suite for a current figure;
     the CI badge above is the live status. -->
<!-- badges:end -->

**The event-sourced learning engine for Helix Codex.**

![Status](https://img.shields.io/badge/status-alpha-blue)
[![CI](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/workflows/python-package.yml/badge.svg?branch=main)](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/runs/36807198469)
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
- Sealed quiz scoring — a scored result is appended once, and the store exposes no way to edit it. See *Try it* for what that does and does not guarantee.
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
| Tests | 465 passed | 2026-10-01 — [run 36807198469](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/runs/36807198469) at `4bd6c02` (latest code change; later commits are docs-only, see the live badge) |
| Core event-sourced learning state | Implemented | 2026-09-27 |
| gRPC competency service | Business logic exists; bindings not generated, registration commented out, nothing mounts it | 2026-09-27 |
| External grounding | A deterministic stub, a generic HTTP client, and a web-search client ship; the tests use the stub | 2026-09-27 |
| Production client deployment | None | 2026-09-27 |
| External audit | None | 2026-09-27 |

> [!WARNING]
> The engine core has no AI dependency. The gRPC competency service is not wired, and external grounding or LLM services are mocked or stubbed in tests. The engine has not been integrated into Helix Prime. No external audit, no certified data isolation, no signed security review, no revenue.

## Run it

Python 3.11–3.13 are covered by the `Python package` CI matrix ([run 36807198387](https://github.com/HatemIsmailShalaby1979/Helix-Education/actions/runs/36807198387), 2026-10-01 — `465 passed` on 3.11, 3.12 and 3.13).

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Try it

Replay a learner's state from an event log, then check that a sealed quiz result cannot be edited through the store API. Run from the repository root.

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

What "sealed" guarantees, stated exactly:

- **Append-only at the store API level.** `EventStore` exposes `append` and the read methods, and no operation that rewrites or removes an event already written. That is an API contract, not tamper-evidence: the log is a plain JSONL file, and anything with write access to the filesystem can edit it.
- **Where keys live.** The answer key is held in a separate key store, never in the event log. The default location is `<user data dir>/helix-education/sealed_answer_keys.jsonl` — `%LOCALAPPDATA%` on Windows, `$XDG_DATA_HOME` or `~/.local/share` elsewhere. Override it with the `HELIX_SEALED_KEY_PATH` environment variable, or pass `StoreConfig.sealed_keys_path`. The working directory is never used, so running the engine cannot write state into a checkout.
- **Not encrypted by default.** The default key store is plaintext JSONL. `EncryptedSealedKeyStore` (which now refuses to start without a configured master key rather than falling back to a built-in default) and the Vault adapter both exist in the tree, but neither is wired in.

## Related work

- [How this project fits the wider work](https://github.com/HatemIsmailShalaby1979/HatemIsmailShalaby1979)

## Author

Built by Hatem Ismail Shalaby, Contact Centre Operations & AI Implementation Lead | WFM & CX Transformation. Background: https://github.com/HatemIsmailShalaby1979

## Licence

MIT
