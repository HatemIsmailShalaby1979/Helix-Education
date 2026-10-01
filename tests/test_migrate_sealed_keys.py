import json
import os
import sys

from scripts import migrate_sealed_keys
from state_core.event_store import default_sealed_key_path


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


def test_cli_defaults_are_resolved_at_runtime(monkeypatch):
    """parse_args must not bake in a repo-root path as the default."""
    monkeypatch.setattr(sys, "argv", ["migrate_sealed_keys.py", "--vault-addr", "http://127.0.0.1:8200"])
    args = migrate_sealed_keys.parse_args()
    assert args.source_file is None
    assert args.backup_path is None


def test_resolved_default_source_is_outside_the_repository(monkeypatch):
    monkeypatch.delenv("HELIX_SEALED_KEY_PATH", raising=False)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    resolved = os.path.abspath(default_sealed_key_path())
    assert not resolved.lower().startswith(repo_root.lower())


def test_main_dry_run_uses_explicit_source(tmp_path, monkeypatch, capsys):
    src = tmp_path / "src.jsonl"
    rec = {"quiz_item_id": "qi_1", "required_keywords": ["a"], "forbidden_keywords": [], "min_length_chars": 0}
    src.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "migrate_sealed_keys.py",
            "--source-file",
            str(src),
            "--vault-addr",
            "http://127.0.0.1:8200",
            "--dry-run",
        ],
    )
    migrate_sealed_keys.main()
    assert "1 records would be migrated" in capsys.readouterr().out


def test_main_dry_run_falls_back_to_the_resolved_path(tmp_path, monkeypatch, capsys):
    """With no --source-file, main() reads HELIX_SEALED_KEY_PATH, not the cwd."""
    src = tmp_path / "resolved.jsonl"
    rec = {"quiz_item_id": "qi_9", "required_keywords": ["b"], "forbidden_keywords": [], "min_length_chars": 0}
    src.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    monkeypatch.setenv("HELIX_SEALED_KEY_PATH", str(src))
    monkeypatch.setattr(sys, "argv", ["migrate_sealed_keys.py", "--vault-addr", "http://127.0.0.1:8200", "--dry-run"])
    migrate_sealed_keys.main()
    assert "1 records would be migrated" in capsys.readouterr().out


def test_main_reports_a_missing_source_file(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "absent.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        ["migrate_sealed_keys.py", "--source-file", str(missing), "--vault-addr", "http://127.0.0.1:8200", "--dry-run"],
    )
    try:
        migrate_sealed_keys.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - main must exit
        raise AssertionError("expected SystemExit(2)")
    assert "Source file not found" in capsys.readouterr().err
