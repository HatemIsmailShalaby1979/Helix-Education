Vault Runbook — Sealed Answer Key Store (HashiCorp Vault)

Purpose

Provide operational guidance to install, configure, and operate Vault for the sealed answer key store used by Helix Education.

Quick start (dev)

1. Start Vault dev server (not for production):
   vault server -dev -dev-root-token-id="root"
2. Export env:
   export VAULT_ADDR=http://127.0.0.1:8200
   export VAULT_TOKEN=root
3. Enable KV v2 (if not already):
   vault secrets enable -path=secret kv-v2

Production (recommended architecture)

- Deploy Vault in HA mode (consul or integrated storage).
- Secure network access; bind to private endpoints.
- Use secure seal/unseal mechanism (auto-unseal via KMS/HSM).

Policies

Migration policy (used by migration job):

```
path "secret/data/helix/sealed_keys/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/metadata/helix/sealed_keys/*" {
  capabilities = ["list", "read"]
}
```

Runtime (scoring) policy (read-only):

```
path "secret/data/helix/sealed_keys/*" {
  capabilities = ["read", "list"]
}
```

Service accounts & tokens

- Create a migration service identity with migration policy and short TTL.
- Create a runtime service identity with read-only policy.
- Prefer AppRole/OCI/OIDC for short-lived tokens; avoid long-lived static tokens if possible.

Backup & migration

- Backup KV by exporting via `vault kv get -format=json` or using replication.
- Migration tool will create `.sealed_answer_keys.jsonl.bak` as local backup before marking success.
- For rollbacks, restore from backup and remove created KV paths (migration tool logs created paths).

Monitoring & auditing

- Enable Vault audit logging to a file or syslog.
- Monitor access patterns and rotate keys per policy.

Secrets handling in CI/CD

- Use repository secrets to store migration tokens for staging only.
- For production, use short-lived credentials via a secure identity provider.

Operational checklist (pre-production)

- Ensure Vault HA and auto-unseal configured
- Validate policy least-privilege and run a permission audit
- Confirm backup and restore playbook works
- Validate migration in staging with dev server and real tokens
- Perform security review and approval prior to production rollout

Contact

Ops team: ops@example.com
Security: secops@example.com
