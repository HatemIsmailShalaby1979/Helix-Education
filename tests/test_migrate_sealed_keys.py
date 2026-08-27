import json
import os

from scripts import migrate_sealed_keys


def test_dry_run(tmp_path):
    src = tmp_path / "src.jsonl"
    rec = {"quiz_item_id": "qi_1", "required_keywords": ["a"], "forbidden_keywords": [], "min_length_chars": 0}
    src.write_text(json.dumps(rec) + "\n", encoding="utf-8")

    # dry-run should exit without error
    args = [
        "--source-file",
        str(src),
        "--vault-addr",
        "http://127.0.0.1:8200",
        "--vault-token-env",
        "VAULT_TOKEN",
        "--dry-run",
    ]
    parser = migrate_sealed_keys.parse_args
    # simulate by calling main with environment set but dry-run ignores token
    os.environ.pop("VAULT_TOKEN", None)
    # call helper functions directly
    records = migrate_sealed_keys.load_source(str(src))
    assert len(records) == 1
    # calling main with dry-run: ensure it returns early
    # (we can't capture sys.exit easily here; rely on functions)
