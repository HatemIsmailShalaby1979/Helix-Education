# Auto-Orchestrator for Helix Education Phase 2
# Usage: python automate_phase2.py

import subprocess
import sys


def run_aider_task(prompt, files):
    """Executes Aider with a specific prompt and file list."""
    command = ["aider", "--model", "openrouter/deepseek/deepseek-chat-v3-0324:free", "--message", prompt] + files

    print("🚀 Executing Aider Task:")
    print(f"   Target Files: {', '.join(files)}")
    print(f"   Prompt: {prompt[:100]}...")

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Aider task completed successfully.")
            return True
        else:
            print(f"❌ Aider task failed:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ Error running Aider: {e}")
        return False


def run_pytest():
    """Runs the test suite and returns success status."""
    # Add Helix Prime and Sprint Tools to the path for integration tests
    sys.path.insert(0, r"E:\AI Engineer Story\Project Helix Prime")
    sys.path.insert(0, r"E:\AI Engineer Story\Sprint Tools")

    command = ["pytest", "tests/test_e2e_integration.py", "-v", "--tb=short"]
    print(f"🧪 Running Test Suite: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ All tests passed.")
            return True
        else:
            print(f"❌ Tests failed:\n{result.stdout}\n{result.stderr}")
            return False
    except Exception as e:
        print(f"⚠️ Error running tests: {e}")
        return False


if __name__ == "__main__":
    # Step 1: Create/Update E2E Tests via Aider
    files_to_edit = [
        "E:\\AI Engineer Story\\PRODUCTION_INTEGRATION_PLAN.md",
        "E:\\AI Engineer Story\\Project Helix Education\\dashboard\\wili_dashboard.py",
        "E:\\AI Engineer Story\\Project Helix Education\\tests\\test_phase1_contracts.py",
        "E:\\AI Engineer Story\\Project Helix Education\\tests\\test_e2e_integration.py",
    ]

    prompt = (
        "Ensure E:\\AI Engineer Story\\Project Helix Education\\tests\\test_e2e_integration.py "
        "is fully implemented with mocks for RTAEngine, B2BEngine, PERSEngine, ContentEngine, "
        "QuizEngine, ProgressEngine, and TMKPatternDetector. Verify the 'Prime → Education → Prime' cycle."
    )

    aider_success = run_aider_task(prompt, files_to_edit)

    # Step 2: Run Tests
    if aider_success:
        print("\n🚀 Proceeding to Test Execution...")
        run_pytest()
    else:
        print("\n⚠️ Skipping tests due to Aider failure.")
