"""
Training script for the Predictive Gap Analysis Model.

Loads synthetic data, trains the model, and reports performance metrics.
"""

import os
import sys

import pandas as pd

# Add project root to path to ensure imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cognitive_engine.ml_models.predictive_gap_model import PredictiveGapModel


def main():
    print("Loading synthetic assessment data...")
    try:
        df = pd.read_csv("data/synthetic_assessments.csv")
        print(f"Loaded {len(df)} records.")
    except FileNotFoundError:
        print("Error: 'data/synthetic_assessments.csv' not found. Run data_generator.py first.")
        return

    print("Initializing Predictive Gap Model...")
    model = PredictiveGapModel()

    print("Training model on historical data...")
    metrics = model.train(df)

    if metrics:
        print("\n--- Training Results ---")
        print(f"RMSE: {metrics['rmse']:.4f}")
        print(f"R2 Score: {metrics['r2']:.4f}")

        # Check against sprint targets
        if metrics["r2"] > 0.75:
            print("✅ Target R2 > 0.75 achieved!")
        else:
            print("⚠️ Target R2 > 0.75 not yet achieved. Further feature engineering may be required.")

        # Save the model
        model.save_model("data/predictive_gap_model.joblib")
        print("Model saved to data/predictive_gap_model.joblib")
    else:
        print("Training failed due to insufficient data.")


if __name__ == "__main__":
    main()
