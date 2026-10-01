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

## Related work

- [Helix Prime](https://github.com/HatemIsmailShalaby1979/Helix-Prime) — the operations core
- [Study Studio](https://github.com/HatemIsmailShalaby1979/Study-Studio) — local-first AI tutor
- [L&D Command Center](https://github.com/HatemIsmailShalaby1979/L-D-Command-Center) — desktop learning and career workstation
- [Blue Waves](https://github.com/HatemIsmailShalaby1979/Blue-Waves-) — content studio
- [LIVE Support Assistant](https://github.com/HatemIsmailShalaby1979/LIVE-Support-Assistant) — explainable support prototype
- [Full portfolio](https://github.com/HatemIsmailShalaby1979) — how this project fits the wider work

### The 2026 building attempts

- [WFM Forecasting Calculator](https://github.com/HatemIsmailShalaby1979/wfm-forecasting-calculator)
- [RTA Command Center](https://github.com/HatemIsmailShalaby1979/RTA_command_center)
- [CX Sentiment Sentinel](https://github.com/HatemIsmailShalaby1979/cx-sentiment-sentinel)
- [Dynamic Ops Automation Engine](https://github.com/HatemIsmailShalaby1979/Dynamic-Ops-Automation-Engine)

## Author

**Hatem Ismail Shalaby** — Operations Architect · AI Systems Engineer · Founder

- GitHub: [HatemIsmailShalaby1979](https://github.com/HatemIsmailShalaby1979)
- LinkedIn: [hatem-shalaby-202902127](https://www.linkedin.com/in/hatem-shalaby-202902127/)
- Email: hatemshalaby2025@gmail.com
- Education: BSc Managerial Sciences (Computer Section), Sadat Academy for Management Sciences; Business Analytics Nanodegree, Udacity

Based in Al Obour City, Al-Qalyubia Governorate, Egypt.

## Licence

MIT
