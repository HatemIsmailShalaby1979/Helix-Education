"""
Promotion Readiness Scoring Algorithm.

Calculates a composite score (0.0 to 1.0) indicating an employee's readiness
for promotion based on technical competencies, learning velocity, and operational impact.
"""

import logging

logger = logging.getLogger(__name__)


class PromotionReadinessScorer:
    def __init__(self, weights: dict[str, float] = None):
        """
        Initialize with weights for different scoring components.
        Default weights prioritize technical competency but value growth.
        """
        self.weights = weights or {"technical_competency": 0.50, "learning_velocity": 0.25, "operational_impact": 0.25}

    def calculate_score(self, employee_profile: dict) -> float:
        """
        Calculates the overall promotion readiness score.

        Args:
            employee_profile: Dictionary containing:
                - 'avg_proficiency': Average skill level (0-1)
                - 'velocity_trend': Average daily proficiency change
                - 'impact_metrics': Dict of operational KPIs (e.g., 'churn_reduction', 'efficiency_gain')

        Returns:
            A float between 0.0 and 1.0.
        """
        # 1. Technical Competency Score
        tech_score = min(max(employee_profile.get("avg_proficiency", 0), 0), 1)

        # 2. Learning Velocity Score
        # Normalize velocity: 0.02/day is considered "high growth" (1.0)
        velocity = employee_profile.get("velocity_trend", 0)
        vel_score = min(max(velocity / 0.02, 0), 1)

        # 3. Operational Impact Score
        impact_metrics = employee_profile.get("impact_metrics", {})
        if impact_metrics:
            # Simple average of normalized impact KPIs
            impact_score = sum(impact_metrics.values()) / len(impact_metrics)
        else:
            impact_score = 0.5  # Neutral if no data

        # Weighted Composite
        final_score = (
            (tech_score * self.weights["technical_competency"])
            + (vel_score * self.weights["learning_velocity"])
            + (impact_score * self.weights["operational_impact"])
        )

        logger.info(f"Promotion Readiness Score calculated: {final_score:.4f}")
        return round(final_score, 4)

    def get_recommendation(self, score: float, threshold: float = 0.85) -> str:
        """
        Provides a textual recommendation based on the score.
        """
        if score >= threshold:
            return "READY_FOR_PROMOTION"
        elif score >= threshold - 0.15:
            return "NEARLY_READY"
        else:
            return "REQUIRES_DEVELOPMENT"
