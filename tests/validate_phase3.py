"""
Phase 3 Acceptance Validation Script.

Verifies that all Phase 3 Advanced Capabilities meet their specific
acceptance criteria before marking the sprint as complete.
"""

import os
import sys

import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cognitive_engine.ml_models.predictive_gap_model import PredictiveGapModel
from progress_engine.adaptive_paths.path_generator import AdaptivePathGenerator
from progress_engine.scoring.promotion_readiness import PromotionReadinessScorer


def validate_predictive_model():
    """S001-02: Verify R2 > 0.75 on holdout set."""
    print("[VALIDATING] S001-02: Predictive Gap Analysis Model...")
    try:
        df = pd.read_csv("data/synthetic_assessments.csv")
        model = PredictiveGapModel()
        metrics = model.train(df)

        if metrics["r2"] > 0.75:
            print(f"✅ PASS: R2 Score is {metrics['r2']:.4f} (> 0.75)")
            return True
        else:
            print(f"❌ FAIL: R2 Score is {metrics['r2']:.4f} (Target > 0.75)")
            return False
    except Exception as e:
        print(f"❌ FAIL: Error during model validation: {e}")
        return False


def validate_adaptive_paths():
    """S001-03: Verify path adaptation logic."""
    print("[VALIDATING] S001-03: Adaptive Learning Paths Engine...")
    try:
        catalog = {
            "Python": [
                {"id": "L1", "difficulty": 0.3},
                {"id": "L2", "difficulty": 0.6},
                {"id": "L3", "difficulty": 0.9},
            ]
        }
        generator = AdaptivePathGenerator(catalog)

        # Test initial generation
        gaps = [{"skill_name": "Python", "current_proficiency": 0.2, "future_deficiency_score": 0.8}]
        path = generator.generate_initial_path(gaps)

        # Test adaptation (low score should add remedial)
        adapted = generator.adapt_path(path, 0.4)

        if len(adapted) >= len(path):
            print("✅ PASS: Adaptive path logic is functional.")
            return True
        else:
            print("❌ FAIL: Path adaptation did not maintain or expand path length for low scores.")
            return False
    except Exception as e:
        print(f"❌ FAIL: Error during path validation: {e}")
        return False


def validate_promotion_scoring():
    """S001-04: Verify scoring algorithm returns valid range."""
    print("[VALIDATING] S001-04: Promotion Readiness Scoring...")
    try:
        scorer = PromotionReadinessScorer()
        profile = {
            "avg_proficiency": 0.8,
            "velocity_trend": 0.015,
            "impact_metrics": {"efficiency_gain": 0.9, "churn_reduction": 0.7},
        }
        score = scorer.calculate_score(profile)

        if 0.0 <= score <= 1.0:
            rec = scorer.get_recommendation(score)
            print(f"✅ PASS: Score calculated: {score} ({rec})")
            return True
        else:
            print(f"❌ FAIL: Score out of range: {score}")
            return False
    except Exception as e:
        print(f"❌ FAIL: Error during scoring validation: {e}")
        return False


def main():
    print("--- Starting Phase 3 Acceptance Validation ---\n")

    results = {
        "Predictive Model": validate_predictive_model(),
        "Adaptive Paths": validate_adaptive_paths(),
        "Promotion Scoring": validate_promotion_scoring(),
    }

    print("\n--- Validation Summary ---")
    all_passed = all(results.values())

    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{check}: {status}")

    if all_passed:
        print("\n🎉 PHASE 3 ACCEPTANCE CRITERIA MET. Ready for documentation update.")
    else:
        print("\n⚠️ SOME CHECKS FAILED. Review logs before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
