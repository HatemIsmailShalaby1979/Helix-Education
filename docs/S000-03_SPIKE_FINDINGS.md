S000-03: Helix Education — Technical Spike Findings (read-only)

Date: 2026-07-25
Owner: Spike orchestrator (human approval required)

1. Problem Statement

Helix Education requires deterministic, auditable scoring. Answer keys (AnswerKey) must be sealed and stored outside the event log. Previous in-memory store lacked durability; interim file-backed SealedAnswerKeyStore was added to address durability but stores plaintext JSONL on disk.

2. Current State

- Event-sourced architecture with deterministic scoring (state_core/scoring_engine.py).
- SealedAnswerKeyStore implemented as file-backed JSONL (.sealed_answer_keys.jsonl) and wired via StoreConfig.sealed_keys_path.
- Full test suite: 435 passing after changes.
- CI workflow added to ensure file exists with restrictive permissions.

3. Desired State

- Durable, encrypted, KMS-managed sealed answer key store.
- Migration path from current file-backed keys to KMS-encrypted store.
- CI and runtime ensure file/key creation follows least-privilege principals.

4. Gap Analysis

- Gap: plaintext keys on disk → risk: data exposure, compliance breach.
- Missing: key-management, rotation, RBAC, audit logs.

5. Impact Analysis

Systems affected:
- state_core (EventStore, SealedAnswerKeyStore)
- QuizEngine (uses stored keys)
- CI pipelines (must create/validate sealed keys file)
- Deployment/ops (secrets and KMS credentials)

6. Dependency Analysis

Direct dependencies:
- state_core.event_store (store implementation)
- state_core.scoring_engine (consumes keys)
- tests and CI pipeline (creation/permissions)

Potential external dependencies:
- Cloud KMS (AWS KMS, Azure Key Vault, GCP KMS) or on-prem HSM
- RBAC and audit tooling

7. Risks

- Confidentiality risk: plaintext persistence on disk (MEDIUM)
- Migration risk: key re-encryption may cause inconsistency if not atomic (MEDIUM)
- Operational risk: KMS misconfiguration, permission gaps (MEDIUM)

Mitigations:
- Restrict file permissions (CI + runtime)
- Enforce CI check that file exists and is limited to build user
- Implement migration tool with atomic swap and test-suite coverage
- Require review and rotation policy before production

8. Reusability

The sealed-store interface should be an adapter pattern with minimal surface:
- store(quiz_item_id, AnswerKey) -> key_hash
- retrieve(quiz_item_id) -> AnswerKey | None

This adapter can be implemented for file-backed, KMS-wrapped ciphertext, or a remote sealed-store service. The interface enables reuse across Sprint Tools if extracted later.

9. Architecture Impact

- Introduces a sealed-store boundary between state_core and storage implementation.
- Requires secret management in CI/CD and runtime orchestration.
- No change to existing event model or scoring algorithms; only storage adapter.

10. Dependency Map (high-level)

[QuizEngine] -> [state_core.scoring_engine] -> [state_core.SealedAnswerKeyStore adapter] -> [Local file | KMS service]

11. Risk Matrix (summary)

- Confidentiality: MEDIUM (mitigate: KMS, ACLs)
- Integrity: LOW (event sourcing protects state)
- Availability: LOW (keys are read-only for scoring; replicate sealed-store for HA)
- Operational: MEDIUM (migration & KMS ops)

12. Recommended Solution

Phase A (Immediate, low-effort)
- Retain file-backed SealedAnswerKeyStore for local/CI use.
- Enforce restrictive file permissions via CI and runtime startup.
- Record DEC-2026-0002 (done) and DEC-2026-0003 (proposed) to track migration.

Phase B (Planned migration)
- Implement KMS-backed sealed-store adapter using envelope encryption.
- Provide migration tool: read existing .sealed_answer_keys.jsonl, encrypt each key, write to new sealed-store, and atomically switch adapter config.
- Add CI integration tests for migration and key-rotation.

Phase C (Production hardening)
- Rotate keys, audit access, and require RBAC and monitoring for KMS usage.

13. Rejected Alternatives

- Keep file-only storage permanently — rejected due to security/compliance risk.
- Local GPG-based encryption — reduces risk but shifts key-management burden to team; not ideal for cloud deployment.

14. Estimated Complexity

- Phase A: Low (hours)
- Phase B: Medium (2-4 days engineering + ops validation)
- Phase C: Medium (policy, ops, monitoring)

15. Human Approval Request

Request: Approve DEC-2026-0003 (Migrate sealed answer keys to KMS-backed sealed store) and authorize Phase B implementation. Implementation requires explicit human approval per governance.

16. Next Actions (upon approval)

- Select KMS provider and document RBAC model.
- Implement sealed-store adapter and migration tool.
- Add CI job to validate migrated keys and rotate policy tests.
- Schedule ops review and roll-out plan.

Appendix: Relevant files reviewed
- state_core/event_store.py
- state_core/scoring_engine.py
- quiz_engine/quiz_service.py
- helix_education/agent_tools.py
- tests/* (full suite)