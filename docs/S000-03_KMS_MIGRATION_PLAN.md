S000-03 Phase B — KMS Migration Implementation Plan

Date: 2026-07-25
Owner: HatemShelby <hatem13071979@gmail.com>
Target timeline: Start immediately; complete in 7 days (due 2026-08-01)
Recommended provider: HashiCorp Vault (OSS) — free/self-hosted, transit & KV v2 engines

Goal

Migrate plaintext file-backed sealed answer keys to a KMS-backed sealed store with encryption-at-rest, key rotation, RBAC, and auditability. Provide an adapter pattern so the runtime can use either local file or Vault-backed store during rollout.

High-level approach

1. Adapter pattern: implement `SealedAnswerKeyStore` interface with two backends:
   - FileBackend (existing .sealed_answer_keys.jsonl) — local fallback
   - VaultKVBackend (preferred): stores each AnswerKey under KV v2 at `secret/data/helix/sealed_keys/<quiz_item_id>`

2. Migration tool (CLI): `migrate-sealed-keys` reads existing file, writes keys into Vault KV, verifies by readback and hash checks, then performs an atomic switch (marker file or config update).

3. CI integration: run migrations in staging-only pipeline using a Vault dev server (or real Vault in staging) with VAULT_ADDR and VAULT_TOKEN provided via secrets. CI job ensures vault token has minimal policy.

4. Rollback: migration creates a backup of the original file (.sealed_answer_keys.jsonl.bak). If verification fails or on rollback request, the migration tool restores the backup and removes newly written secrets (or marks them deprecated).

Detailed steps

Design (1 day)
- Finalize adapter interface (store/retrieve) and config scheme: `StoreConfig(sealed_keys_backend: 'file' | 'vault', sealed_keys_path: str | None, vault_addr: str | None, vault_token_env: str | None, vault_kv_mount: str='secret')`
- Specify migration CLI flags: `--source-file`, `--vault-addr`, `--vault-token-env`, `--vault-kv-mount`, `--dry-run`, `--backup-path`, `--atomic-swap`, `--remove-on-failure`, `--verbose`.
- Define verification algorithm: for each key, compute compute_key_hash(AnswerKey) and verify stored entry can be retrieved and matches hash.

Implement (3 days)
- Add `VaultSealedAnswerKeyStore` implementation (uses `hvac` or `requests` to call Vault API). Minimal dependency: `hvac` (Python) — add optional dependency in dev extras.
- Implement config loader to choose backend by `StoreConfig`.
- Implement migration CLI `scripts/migrate_sealed_keys.py`:
  - Read source JSONL file (same canonical fields used by compute_key_hash)
  - For each record, write to KV v2 at `<kv_mount>/data/helix/sealed_keys/<quiz_item_id>` with payload: `{"required_keywords": [...], "forbidden_keywords": [...], "min_length_chars": N}`
  - After write, read back and compute hash to compare with compute_key_hash outcome (or check retrieval equality)
  - On success for all items, create marker file `.sealed_answer_keys.migrated` and archive original file to `.sealed_answer_keys.jsonl.bak`.
  - If `--atomic-swap` is provided, update repository config (or environment) to point to `vault` backend (e.g., write `SEALED_KEYS_BACKEND=vault` in runtime config). Note: modifying runtime config requires ops approval; default: write local `config/_sealed_store_backend` marker for ops to apply.

Test (1 day)
- Unit tests for Vault adapter using Vault dev server (launch in background during tests or use `hvac` mock). Tests:
  - store/retrieve roundtrip
  - deterministic compute_key_hash preserved
  - migration CLI dry-run validates mapping
- Integration test: run migration end-to-end against Vault dev server in CI staging job; verify access using a CI-scoped token.

Ops (1 day)
- Provide runbook: install HashiCorp Vault, enable KV v2 and transit (optional), initialize and unseal, create policies, create a service token with limited rights to `secret/data/helix/sealed_keys/*` (create/read/delete) for the migration step and runtime read-only token for scoring (read only).
- Example policy (policy.hcl):

```
path "secret/data/helix/sealed_keys/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/metadata/helix/sealed_keys/*" {
  capabilities = ["list", "read"]
}
```

- For runtime scoring, create a policy with only `read` on `secret/data/helix/sealed_keys/*`.
- CI should use a migration token with `create` and `delete` permitted; the runtime token must be read-only.

Security notes
- Use Vault KV v2 (secrets are encrypted at rest by Vault). For stricter separation, use Transit to encrypt with envelope keys and store ciphertext in KV or in a separate store.
- Limit tokens with policies and use short-lived tokens where possible (Vault AppRole or OIDC).
- Avoid embedding tokens in code; use environment variables or CI secrets manager.

Vault CLI / API snippets

Enable KV v2 (admin):

```
vault secrets enable -path=secret kv-v2
```

Write a secret (KV v2 via CLI):

```
vault kv put secret/helix/sealed_keys/<quiz_item_id> required_keywords='["a"]' forbidden_keywords='[]' min_length_chars=0
```

Read a secret:

```
vault kv get -format=json secret/helix/sealed_keys/<quiz_item_id>
```

Python adapter sketch (using hvac)

```py
import hvac


class VaultSealedAnswerKeyStore:
    def __init__(self, vault_addr, token, kv_mount="secret"):
        self.client = hvac.Client(url=vault_addr, token=token)
        self.kv_mount = kv_mount

    def store(self, quiz_item_id, key: AnswerKey) -> str:
        path = f"{self.kv_mount}/data/helix/sealed_keys/{quiz_item_id}"
        payload = {
            "data": {
                "required_keywords": key.required_keywords,
                "forbidden_keywords": key.forbidden_keywords,
                "min_length_chars": key.min_length_chars,
            }
        }
        self.client.secrets.kv.v2.create_or_update_secret(
            path=f"helix/sealed_keys/{quiz_item_id}", secret=payload["data"], mount_point=self.kv_mount
        )
        return compute_key_hash(key)

    def retrieve(self, quiz_item_id):
        try:
            res = self.client.secrets.kv.v2.read_secret_version(
                path=f"helix/sealed_keys/{quiz_item_id}", mount_point=self.kv_mount
            )
            data = res["data"]["data"]
            return AnswerKey(
                required_keywords=data.get("required_keywords", []),
                forbidden_keywords=data.get("forbidden_keywords", []),
                min_length_chars=data.get("min_length_chars", 0),
            )
        except hvac.exceptions.InvalidPath:
            return None
```

Migration CLI spec

```
usage: migrate_sealed_keys.py [--source-file FILE] [--vault-addr ADDR] [--vault-token-env ENVVAR] [--kv-mount secret] [--dry-run] [--backup-path PATH] [--atomic-swap]

--source-file: path to existing .sealed_answer_keys.jsonl (default: .sealed_answer_keys.jsonl)
--vault-addr: VAULT_ADDR
--vault-token-env: environment variable name that contains Vault token (default: VAULT_TOKEN)
--kv-mount: KV mount point (default: secret)
--dry-run: validate mapping without writing to Vault
--backup-path: path to store original backup (default: .sealed_answer_keys.jsonl.bak)
--atomic-swap: on success, create marker and optionally update runtime config
```

Atomic migration and config switch
- Implement `--atomic-swap` as: after successful writes and verification, write a marker file `.sealed_answer_keys.migrated` and copy original file to backup. Do NOT automatically change production runtime configs; instead write the recommended env var change to `config/.sealed_store_backend` for ops to apply.

CI integration (job snippet)

- Add a staging job that runs Vault (dev server) for migration test:
  - Start Vault dev server in background (vault server -dev -dev-root-token-id="root")
  - Export VAULT_ADDR and VAULT_TOKEN
  - Run `scripts/migrate_sealed_keys.py --source-file .sealed_answer_keys.jsonl --vault-addr ${VAULT_ADDR} --vault-token-env VAULT_TOKEN --kv-mount secret --dry-run` then real run in staging

Rollback strategy

- Keep original file backup `.sealed_answer_keys.jsonl.bak`
- If migration fails, use the backup to restore and remove newly created KV secrets (migration tool can record created paths in a log and remove them on rollback).

Deliverables

- VaultSealedAnswerKeyStore adapter (code + tests)
- Migration CLI `scripts/migrate_sealed_keys.py` (code + tests)
- CI staging job that tests migration with Vault dev server
- Ops runbook (installation, policies, tokens)
- Integration tests and a small post-migration verification script

Estimate per subtask

- Design: 1 day
- Implement: 3 days
- Test: 1 day
- Ops/runbook: 1 day

Start design subtask now: status updated to in_progress and design doc created here.
