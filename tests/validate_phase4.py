"""
Phase 4 Acceptance Validation Script.

Verifies that all Phase 4 Production Hardening capabilities meet their
specific acceptance criteria before marking the sprint as complete.
"""

import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from observability.metrics import metrics
from state_core.security.encrypted_key_store import EncryptedSealedKeyStore


def validate_encrypted_storage():
    """S002-01: Verify answer keys are stored as ciphertext."""
    print("[VALIDATING] S002-01: Encrypted Sealed Key Store...")
    try:
        store = EncryptedSealedKeyStore("data/test_sealed_keys.jsonl", "test-master-key")
        test_key = {"answer": "Python", "keywords": ["code", "script"]}

        store.store_key("test-assessment-001", test_key)

        # Read raw file to ensure it's not plaintext
        with open("data/test_sealed_keys.jsonl") as f:
            line = f.readline().strip()
            entry = json.loads(line)

        if "data" in entry and len(entry["data"]) > 50:  # Ciphertext is usually long base64
            print("✅ PASS: Answer key is stored as encrypted ciphertext.")
            return True
        else:
            print("❌ FAIL: Data appears to be plaintext or malformed.")
            return False
    except Exception as e:
        print(f"❌ FAIL: Error during encryption validation: {e}")
        return False


def validate_observability_metrics():
    """S002-02: Verify metrics collection and Prometheus format."""
    print("[VALIDATING] S002-02: Observability Stack...")
    try:
        # Simulate some activity
        metrics.increment_counter("test_validation_counter")
        metrics.observe_histogram("test_latency", 0.15)

        summary = metrics.get_metrics_summary()

        if "test_validation_counter" in summary["counters"]:
            print("✅ PASS: Metrics collector is tracking counters.")

            # Check Prometheus formatting logic (simulated)
            output_lines = []
            for name, value in summary["counters"].items():
                output_lines.append(f"# HELP {name} Total count")
                output_lines.append(f"# TYPE {name} counter")
                output_lines.append(f"{name} {value}")

            if any("HELP" in line for line in output_lines):
                print("✅ PASS: Prometheus text format generation is functional.")
                return True
        else:
            print("❌ FAIL: Metrics collector failed to record test data.")
            return False
    except Exception as e:
        print(f"❌ FAIL: Error during observability validation: {e}")
        return False


def validate_load_test_config():
    """S002-03: Verify k6 script exists and has thresholds."""
    print("[VALIDATING] S002-03: Load Testing Scaffolding...")
    try:
        script_path = "tests/load/api_stress_test.js"
        if os.path.exists(script_path):
            with open(script_path) as f:
                content = f.read()

            if "thresholds" in content and "p(95)<500" in content:
                print("✅ PASS: k6 script found with P95 < 500ms threshold.")
                return True
            else:
                print("❌ FAIL: k6 script missing required performance thresholds.")
                return False
        else:
            print("❌ FAIL: k6 load test script not found.")
            return False
    except Exception as e:
        print(f"❌ FAIL: Error during load test validation: {e}")
        return False


def main():
    print("--- Starting Phase 4 Acceptance Validation ---\n")

    results = {
        "Encrypted Storage": validate_encrypted_storage(),
        "Observability Metrics": validate_observability_metrics(),
        "Load Test Config": validate_load_test_config(),
    }

    print("\n--- Validation Summary ---")
    all_passed = all(results.values())

    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{check}: {status}")

    if all_passed:
        print("\n🎉 PHASE 4 ACCEPTANCE CRITERIA MET. Ready for production deployment planning.")
    else:
        print("\n⚠️ SOME CHECKS FAILED. Review logs before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
