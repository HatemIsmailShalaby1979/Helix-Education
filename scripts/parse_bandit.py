"""Parse Bandit JSON output and produce a breakdown by directory and severity."""

import json
import sys
from collections import Counter


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_bandit.py <bandit_json_path>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    results = data.get("results", [])
    print(f"Total findings: {len(results)}")

    sev_counts = Counter(r["issue_severity"] for r in results)
    print(f"By severity: {dict(sev_counts)}")

    high = [r for r in results if r["issue_severity"] == "HIGH"]
    print(f"\nHIGH severity findings ({len(high)}):")
    for r in high:
        fname = r["filename"]
        # Normalize to relative path from project root
        top_dir = fname.replace("\\", "/").split("/")[0]
        print(f"  [{r['test_id']}] {fname}")
        print(f"    Line {r['line_number']}: {r['issue_text'][:120]}")
        print(f"    Top-level dir: {top_dir}")
        print()

    # Group all findings by top-level directory
    dir_counts = Counter()
    dir_high = Counter()
    for r in results:
        fname = r["filename"].replace("\\", "/")
        parts = fname.split("/")
        top = parts[0] if len(parts) > 1 else "<root>"
        dir_counts[top] += 1
        if r["issue_severity"] == "HIGH":
            dir_high[top] += 1

    print("Findings by top-level directory:")
    print(f"  {'Directory':<30} {'Total':>6} {'HIGH':>6}")
    print(f"  {'-' * 30} {'-' * 6} {'-' * 6}")
    for d, c in dir_counts.most_common():
        h = dir_high.get(d, 0)
        print(f"  {d:<30} {c:>6} {h:>6}")


if __name__ == "__main__":
    main()
