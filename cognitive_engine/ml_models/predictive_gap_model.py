"""
Predictive Gap Analysis Model.

Forecasts skill deficiencies 30 days out based on historical assessment data,
learning velocity, and operational gap patterns from the TMK Loop.
"""

import logging

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)


class PredictiveGapModel:
    def __init__(self):
        self.model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
        self.is_trained = False
        self.feature_columns = [
            "current_proficiency",
            "learning_velocity",
            "days_since_last_assessment",
            "operational_gap_severity",
            "role_complexity_score",
        ]

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extracts and engineers features from raw assessment history."""
        if df.empty:
            return pd.DataFrame(columns=self.feature_columns)

        # Simple feature engineering for the spike
        features = pd.DataFrame()
        features["current_proficiency"] = df["proficiency_level"]
        features["learning_velocity"] = df["proficiency_change_per_day"]
        features["days_since_last_assessment"] = df["days_since_last_assessment"]
        features["operational_gap_severity"] = df.get("gap_severity", 0.5)
        features["role_complexity_score"] = df.get("role_complexity", 0.5)

        return features.fillna(0)

    def train(self, training_data: pd.DataFrame, target_column: str = "future_deficiency_score"):
        """Trains the model on historical assessment data."""
        X = self.prepare_features(training_data)
        y = training_data[target_column]

        if X.empty or y.empty:
            logger.warning("Insufficient data for training.")
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        self.model.fit(X_train, y_train)
        self.is_trained = True

        # Evaluation during training
        y_pred = self.model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        logger.info(f"Model trained. RMSE: {rmse:.4f}, R2: {r2:.4f}")
        return {"rmse": rmse, "r2": r2}

    def predict(self, current_profiles: pd.DataFrame) -> pd.Series:
        """Predicts deficiency scores for the next 30 days."""
        if not self.is_trained:
            raise Exception("Model must be trained before prediction.")

        X = self.prepare_features(current_profiles)
        return self.model.predict(X)

    def save_model(self, path: str):
        """Persists the trained model to disk."""
        joblib.dump(self.model, path)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: str):
        """Loads a pre-trained model from disk."""
        self.model = joblib.load(path)
        self.is_trained = True
        logger.info(f"Model loaded from {path}")
