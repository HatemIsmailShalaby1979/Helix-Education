"""
Adaptive Learning Path Service.

Orchestrates the generation and adaptation of learning paths by integrating
the Predictive Gap Model, Content Catalog, and Event Store.
"""

import logging

import pandas as pd

from cognitive_engine.ml_models.predictive_gap_model import PredictiveGapModel
from state_core.event_store import EventStore

from .path_generator import AdaptivePathGenerator

logger = logging.getLogger(__name__)


class LearningPathService:
    def __init__(self, event_store: EventStore, content_catalog: dict):
        self.event_store = event_store
        self.path_generator = AdaptivePathGenerator(content_catalog)
        self.prediction_model = PredictiveGapModel()

        # In a production environment, this would be loaded from disk or a registry
        try:
            self.prediction_model.load_model("data/predictive_gap_model.joblib")
        except Exception as e:
            logger.warning(f"Could not load pre-trained model: {e}. Using untrained instance.")

    def create_personalized_path(self, employee_id: str) -> list[dict]:
        """
        Generates a full adaptive learning path for an employee.
        1. Retrieves historical data.
        2. Predicts future gaps.
        3. Generates initial path.
        """
        # 1. Get history from EventStore (simulated for this spike)
        history_df = self._get_employee_history(employee_id)

        if history_df.empty:
            logger.info(f"No history found for {employee_id}. Generating baseline path.")
            return []

        # 2. Predict gaps
        predictions = self.prediction_model.predict(history_df)

        # Map predictions back to gap objects for the generator
        predicted_gaps = []
        for i, score in enumerate(predictions):
            predicted_gaps.append(
                {
                    "skill_name": history_df.iloc[i]["skill_name"],
                    "current_proficiency": history_df.iloc[i]["proficiency_level"],
                    "future_deficiency_score": float(score),
                }
            )

        # 3. Generate path
        return self.path_generator.generate_initial_path(predicted_gaps)

    def update_path_progress(self, employee_id: str, lesson_id: str, quiz_score: float):
        """
        Records a quiz result and adapts the remaining learning path.
        """
        # Record the event
        self.event_store.append_event(
            {"type": "QUIZ_COMPLETED", "employee_id": employee_id, "lesson_id": lesson_id, "score": quiz_score}
        )

        # Retrieve current active path (simulated retrieval)
        current_path = self._get_active_path(employee_id)

        # Adapt based on performance
        adapted_path = self.path_generator.adapt_path(current_path, quiz_score)

        logger.info(f"Path for {employee_id} adapted after lesson {lesson_id} (Score: {quiz_score})")
        return adapted_path

    def _get_employee_history(self, employee_id: str) -> pd.DataFrame:
        """
        Retrieves and formats historical assessment data for an employee.
        """
        # In a real implementation, this would query the EventStore
        # For this spike, we'll return a small synthetic sample if no real data exists
        return pd.DataFrame(
            [
                {
                    "skill_name": "Python",
                    "proficiency_level": 0.6,
                    "proficiency_change_per_day": 0.01,
                    "days_since_last_assessment": 5,
                    "gap_severity": 0.4,
                    "role_complexity": 0.7,
                }
            ]
        )

    def _get_active_path(self, employee_id: str) -> list[dict]:
        """
        Retrieves the currently active learning path for an employee.
        """
        # Placeholder for state retrieval logic
        return []
