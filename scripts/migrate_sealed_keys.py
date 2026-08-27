"""Migration CLI: migrate plaintext .sealed_answer_keys.jsonl into Vault KV v2.

Usage (basic):
  python scripts/migrate_sealed_keys.py --source-file .sealed_answer_keys.jsonl --vault-addr http://127.0.0.1:8200 --vault-token-env VAULT_TOKEN --kv-mount secret

This script supports --dry-run and --backup-path and will verify writes by reading back.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from state_core.event_store import compute_key_hash
from state_core.scoring_engine import AnswerKey
from state_core.vault_store import VaultSealedAnswerKeyStore


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--source-file", default=".sealed_answer_keys.jsonl")
    p.add_argument("--vault-addr", required=True)
    p.add_argument("--vault-token-env", default="VAULT_TOKEN")
    p.add_argument("--kv-mount", default="secret")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--backup-path", default=".sealed_answer_keys.jsonl.bak")
    p.add_argument("--atomic-swap", action="store_true")
    return p.parse_args()


def load_source(path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            records.append(json.loads(s))
    return records


def to_answer_key(rec: dict[str, Any]) -> AnswerKey:
    return AnswerKey(
        required_keywords=rec.get("required_keywords", []),
        forbidden_keywords=rec.get("forbidden_keywords", []),
        min_length_chars=rec.get("min_length_chars", 0),
    )


def main():
    args = parse_args()
    token = os.environ.get(args.vault_token_env)
    if not token and not args.dry_run:
        print(f"Vault token environment variable {args.vault_token_env} is not set", file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(args.source_file):
        print(f"Source file not found: {args.source_file}", file=sys.stderr)
        sys.exit(2)

    records = load_source(args.source_file)
    if not records:
        print("No records found; nothing to migrate.")
        return

    if args.dry_run:
        print(f"Dry run: {len(records)} records would be migrated to {args.vault_addr} (mount {args.kv_mount})")
        return

    store = VaultSealedAnswerKeyStore(args.vault_addr, token, kv_mount=args.kv_mount)
    created = []
    for rec in records:
        quiz_item_id = rec.get("quiz_item_id")
        if not quiz_item_id:
            print("Skipping record with missing quiz_item_id", file=sys.stderr)
            continue
        key = to_answer_key(rec)
        try:
            store.store(quiz_item_id, key)
            # verify readback
            got = store.retrieve(quiz_item_id)
            if not got:
                raise RuntimeError("readback failed")
            if compute_key_hash(got) != compute_key_hash(key):
                raise RuntimeError("hash mismatch after write")
            created.append(quiz_item_id)
            print(f"Migrated {quiz_item_id}")
        except Exception as e:
            print(f"Failed migrating {quiz_item_id}: {e}", file=sys.stderr)
            # on failure attempt cleanup of created paths? leave for ops to inspect
            sys.exit(3)

    # archive source file
    os.rename(args.source_file, args.backup_path)
    # marker for ops
    if args.atomic_swap:
        with open(".sealed_answer_keys.migrated", "w", encoding="utf-8") as m:
            m.write("migrated\n")
    print(f"Migration complete. {len(created)} records migrated. Backup saved to {args.backup_path}")


if __name__ == "__main__":
    main()
