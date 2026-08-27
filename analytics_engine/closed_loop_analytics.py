"""
Closed-Loop Analytics Engine.

Correlates training completion data with operational KPIs to measure
the tangible impact of Learning & Development on business outcomes.
"""

import logging

import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class ClosedLoopAnalytics:
    def __init__(self):
        self.training_data: list[dict] = []
        self.operational_data: list[dict] = []

    def ingest_training_metrics(self, metrics: list[dict]):
        """Ingests training completion and assessment scores."""
        self.training_data.extend(metrics)
        logger.info(f"Ingested {len(metrics)} training records.")

    def ingest_operational_kpis(self, kpis: list[dict]):
        """Ingests operational data (e.g., churn rates, adherence, AHT)."""
        self.operational_data.extend(kpis)
        logger.info(f"Ingested {len(kpis)} operational KPI records.")

    def calculate_correlation(self, training_col: str, kpi_col: str) -> dict:
        """
        Calculates the Pearson correlation between a training metric and an operational KPI.
        Returns r-value, p-value, and significance status.
        """
        df_train = pd.DataFrame(self.training_data)
        df_ops = pd.DataFrame(self.operational_data)

        # Merge on employee_id or date (simplified for this spike)
        if "employee_id" in df_train.columns and "employee_id" in df_ops.columns:
            merged = pd.merge(df_train, df_ops, on="employee_id")
        else:
            logger.warning("Cannot merge data: missing common key (employee_id).")
            return {"r": 0, "p": 1.0, "significant": False}

        if len(merged) < 3:
            return {"r": 0, "p": 1.0, "significant": False}

        r_val, p_val = stats.pearsonr(merged[training_col], merged[kpi_col])

        result = {"r": round(r_val, 4), "p": round(p_val, 4), "significant": p_val < 0.05}

        logger.info(f"Correlation ({training_col} vs {kpi_col}): r={result['r']}, p={result['p']}")
        return result
