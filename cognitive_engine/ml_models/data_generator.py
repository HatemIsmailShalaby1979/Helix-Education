"""
Synthetic Data Generator for Predictive Gap Analysis.

Generates historical assessment data with known patterns to validate
the ML model's ability to forecast skill deficiencies.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def generate_historical_assessments(num_employees=100, days_history=90):
    """
    Generates a DataFrame of synthetic assessment records.

    Includes:
    - Proficiency levels (0.0 to 1.0)
    - Learning velocity (change in proficiency per day)
    - Operational gap severity (from TMK Loop simulation)
    - Future deficiency score (the target variable for prediction)
    """
    records = []
    end_date = datetime.now()

    skills = ["Python", "FastAPI", "WFM_Forecasting", "RTA_Adherence", "Churn_Analysis"]
    roles = ["Junior_Engineer", "Senior_Engineer", "Ops_Manager"]
    role_complexity = {"Junior_Engineer": 0.3, "Senior_Engineer": 0.7, "Ops_Manager": 0.9}

    for i in range(num_employees):
        employee_id = f"EMP-{i + 1:04d}"
        role = np.random.choice(roles)

        for skill in skills:
            # Simulate a learning curve
            base_proficiency = np.random.uniform(0.2, 0.8)
            velocity = np.random.uniform(-0.01, 0.02)  # Daily change

            # Current state
            current_prof = min(max(base_proficiency + (velocity * days_history), 0.0), 1.0)
            days_since = np.random.randint(1, 30)
            gap_severity = np.random.uniform(0.0, 1.0)

            # Target: Deficiency score in 30 days (higher is worse)
            # If velocity is negative or gap severity is high, deficiency increases
            future_deficiency = max(0, (1.0 - (current_prof + (velocity * 30))) + (gap_severity * 0.5))

            records.append(
                {
                    "employee_id": employee_id,
                    "skill_name": skill,
                    "role_id": role,
                    "proficiency_level": current_prof,
                    "proficiency_change_per_day": velocity,
                    "days_since_last_assessment": days_since,
                    "gap_severity": gap_severity,
                    "role_complexity": role_complexity[role],
                    "future_deficiency_score": future_deficiency,
                    "assessment_date": (end_date - timedelta(days=days_since)).isoformat(),
                }
            )

    return pd.DataFrame(records)


if __name__ == "__main__":
    df = generate_historical_assessments()
    print(df.head())
    print(f"Generated {len(df)} assessment records.")
    df.to_csv("data/synthetic_assessments.csv", index=False)
