"""
Automated Retraining Triggers.

Monitors content effectiveness and operational shifts to flag training
modules that require updates or re-generation.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RetrainingTriggerService:
    def __init__(self, freshness_threshold_days: int = 90):
        self.freshness_threshold = timedelta(days=freshness_threshold_days)

    def check_content_freshness(self, content_catalog: list[dict]) -> list[str]:
        """
        Identifies lessons that haven't been updated in over the threshold.
        """
        outdated_ids = []
        now = datetime.utcnow()

        for lesson in content_catalog:
            last_updated = datetime.fromisoformat(lesson.get("last_updated", "2020-01-01"))
            if (now - last_updated) > self.freshness_threshold:
                outdated_ids.append(lesson["id"])
                logger.warning(f"Content outdated: {lesson['id']} ({lesson.get('title')})")

        return outdated_ids

    def detect_performance_degradation(self, assessment_history: list[dict], threshold: float = 0.6) -> list[str]:
        """
        Flags lessons where recent pass rates have dropped below the threshold.
        """
        failing_lessons = []
        # Group by lesson_id and calculate average score for the last 30 days
        # Simplified for this spike:
        for record in assessment_history:
            if record.get("avg_score", 1.0) < threshold:
                failing_lessons.append(record["lesson_id"])

        return list(set(failing_lessons))
