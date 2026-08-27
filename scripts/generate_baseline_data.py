import json
from datetime import datetime

import numpy as np
import pandas as pd


def generate_baseline_data():
    """Generates 30 days of simulated operational data for Helix Prime."""
    dates = pd.date_range(end=datetime.now(), periods=30)
    np.random.seed(42)  # For reproducibility

    data = {
        "date": dates,
        "onboarding_time_hours": np.random.normal(48, 5, 30),
        "adherence_rate": np.random.normal(0.92, 0.03, 30),
        "churn_risk_score": np.random.normal(0.15, 0.05, 30),
        "sop_error_rate": np.random.normal(0.08, 0.02, 30),
        "assessment_pass_rate": np.random.normal(0.75, 0.04, 30),
    }
    return pd.DataFrame(data)


def calculate_metrics(df):
    """Calculates summary metrics from the baseline data."""
    metrics = {
        "avg_onboarding_time_hours": round(df["onboarding_time_hours"].mean(), 2),
        "avg_adherence_rate_pct": round(df["adherence_rate"].mean() * 100, 2),
        "avg_churn_risk_pct": round(df["churn_risk_score"].mean() * 100, 2),
        "avg_sop_error_rate_pct": round(df["sop_error_rate"].mean() * 100, 2),
        "avg_assessment_pass_rate_pct": round(df["assessment_pass_rate"].mean() * 100, 2),
        "time_to_hire_days": 14.5,  # Simulated value for PERS engine
    }
    return metrics


if __name__ == "__main__":
    df = generate_baseline_data()
    metrics = calculate_metrics(df)

    print("--- Baseline Metrics (30-Day Simulation) ---")
    print(json.dumps(metrics, indent=2))

    # Save to CSV for record-keeping
    csv_path = "data/baseline_metrics_30d.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nData saved to {csv_path}")
