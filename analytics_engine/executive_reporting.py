"""
Executive Reporting Engine.

Generates automated monthly ROI reports for SAMI (CEO) showing the
tangible value of L&D investment through operational KPI improvements.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ExecutiveReportGenerator:
    def __init__(self):
        self.report_history: list[dict] = []

    def generate_monthly_roi_report(self, metrics: dict) -> dict:
        """
        Compiles a high-level summary of L&D impact for executive review.

        Args:
            metrics: Dictionary containing aggregated data from ClosedLoopAnalytics.
        Returns:
            A structured report dictionary.
        """
        report = {
            "report_date": datetime.utcnow().isoformat(),
            "period": "Monthly",
            "summary": {
                "total_employees_trained": metrics.get("employees_trained", 0),
                "avg_competency_lift": metrics.get("avg_competency_lift", 0),
                "operational_impact": {
                    "churn_reduction_pct": metrics.get("churn_reduction", 0),
                    "adherence_improvement_pct": metrics.get("adherence_improvement", 0),
                    "estimated_cost_savings": metrics.get("cost_savings", 0),
                },
            },
            "recommendations": self._generate_recommendations(metrics),
        }

        self.report_history.append(report)
        logger.info("Executive ROI report generated.")
        return report

    def _generate_recommendations(self, metrics: dict) -> list[str]:
        """Provides actionable insights based on the data."""
        recs = []
        if metrics.get("churn_reduction", 0) < 5:
            recs.append("Increase focus on customer empathy training modules.")
        if metrics.get("avg_competency_lift", 0) < 10:
            recs.append("Review adaptive learning paths for difficulty alignment.")
        if not recs:
            recs.append("L&D program is performing within optimal parameters.")
        return recs
