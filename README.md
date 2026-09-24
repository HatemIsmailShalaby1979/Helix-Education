> **Status: Alpha / research product — 447 tests passing (snapshot 2026-08-29) / not production-integrated / no external audit / no release tag.**
>
> Event-sourced learning engine: replayable events, sealed assessments, reconstructed paths. Built solo, self-taught, after a career switch. No team, no funding.

# Helix Education

**A component of Helix Codex. An event-sourced learning engine built for accountable progress.**

Helix Education supplies the learning foundation that Helix Codex would use. It is a standalone engine built around replayable events, citation-grounded content, sealed assessment, adaptive paths, and inspectable learner progress.

It is not Helix Prime. It is a component, and it is not yet wired into the core.

## Verified status

| Item | State | Snapshot |
|---|---|---|
| Tests | 447 passing | 2026-08-29 |
| Core event-sourced learning state | Implemented | 2026-08-29 |
| gRPC competency service | Contracts exist; service not wired | 2026-08-29 |
| External grounding and LLM services | Mocked or stubbed in tests | 2026-08-29 |
| Production client deployment | None | 2026-08-29 |
| External audit | None | 2026-08-29 |

The engine core has no AI dependency. Every figure above was measured on 2026-08-29 and has not been re-measured since.

## Core capabilities

- Event-sourced records with state reconstruction
- Citation-grounded learning content
- Sealed quiz scoring
- Adaptive learning paths
- Progress and milestone tracking
- Portable, inspectable learning history
- Zero AI dependency in the core engine

## Why it matters to Helix Codex

Operational knowledge can become structured learning. Outcomes can improve future training. Progress stays auditable, and learning records keep their context. That is the capability this repository supplies to Helix Codex.

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

The gRPC competency service is not wired. External grounding and LLM services are mocked or stubbed in tests. No production client deployment exists, and the engine has not been integrated into Helix Prime.

This is not a production deployment claim. There is no external audit, no certified data isolation, and no signed security review. No revenue has been realised.

## Related work

- [Helix Prime](https://github.com/HatemIsmailShalaby1979/Helix-Prime) — the operations core
- [Study Studio](https://github.com/HatemIsmailShalaby1979/Study-Studio) — local-first AI tutor
- [L&D Command Center](https://github.com/HatemIsmailShalaby1979/L-D-Command-Center) — desktop learning and career workstation
- [Blue Waves](https://github.com/HatemIsmailShalaby1979/Blue-Waves-) — content studio
- [LIVE Support Assistant](https://github.com/HatemIsmailShalaby1979/LIVE-Support-Assistant) — explainable support prototype
- [Full portfolio](https://github.com/HatemIsmailShalaby1979) — the front door

### The 2026 building attempts

- [WFM Forecasting Calculator](https://github.com/HatemIsmailShalaby1979/wfm-forecasting-calculator)
- [RTA Command Center](https://github.com/HatemIsmailShalaby1979/RTA_command_center)
- [CX Sentiment Sentinel](https://github.com/HatemIsmailShalaby1979/cx-sentiment-sentinel)
- [Dynamic Ops Automation Engine](https://github.com/HatemIsmailShalaby1979/Dynamic-Ops-Automation-Engine)

## The founder's story

I spent twenty-eight years in operations. The first fourteen were the
foundation: ground operations and real-time traffic management at Hurghada
International Airport, then Air Berlin, where I directed ground operations
through the 2011 regional transition and held SLA compliance under conditions
that had no playbook. Alongside that, international logistics at Shorouk
International Bookshop and hybrid IT operations at Nefertari American School.

The second fourteen were about automation. I built AI-driven automation for
contact centres at ByteDance, Vodafone and Uber: NLP pipelines that turn
unstructured customer language into signal, Erlang C forecasting that turns
volume into staffing, and the reporting layers that made both usable by people
on the floor. The hard part was never the model. It was the handover — who owns
the decision, what evidence supports it, and what happens when the system is
wrong.

In April 2026 I left that career and started building full time — alone, and
teaching myself to write software as I went. The first four tools were published
six weeks later, in May and June 2026. Each one took a single operational problem
and solved it properly. They were not impressive. They were correct.

Those four tools converged into one idea: **Helix Codex**, an accountable AI
operating organization. Not an autonomous agent. An organization with a
constitution, named roles with bounded authority, evidence trails, and a human at
every consequential boundary. Helix Prime is its operations core.

Helix Education is a component of Helix Codex. It is maintained by one person, with no team and
no funding. It has not been externally audited and it has not made revenue. Where
it is unfinished, this document says so.

## Author

**Hatem Ismail Shalaby** — Operations Architect · AI Systems Engineer · Founder

- GitHub: [HatemIsmailShalaby1979](https://github.com/HatemIsmailShalaby1979)
- LinkedIn: [hatem-shalaby-202902127](https://www.linkedin.com/in/hatem-shalaby-202902127/)
- Email: hatemshalaby2025@gmail.com
- Education: BSc Managerial Sciences (Computer Section), Sadat Academy for Management Sciences; Business Analytics Nanodegree, Udacity

Based in Al Obour City, Al-Qalyubia Governorate, Egypt.

## Licence

MIT
