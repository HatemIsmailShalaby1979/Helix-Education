"""
Adaptive Learning Path Generator.

Generates personalized training sequences based on predicted skill deficiencies
and dynamically adjusts the path based on learner performance (quiz scores).
"""

import logging

logger = logging.getLogger(__name__)


class AdaptivePathGenerator:
    def __init__(self, content_catalog: dict[str, list[dict]]):
        """
        Initialize with a catalog of available lessons mapped by skill.
        Example: {'Python': [{'id': 'L1', 'difficulty': 0.5}, ...]}
        """
        self.content_catalog = content_catalog

    def generate_initial_path(self, predicted_gaps: list[dict]) -> list[dict]:
        """
        Creates an initial learning path prioritized by deficiency severity.
        """
        path = []
        # Sort gaps by severity (future_deficiency_score) descending
        sorted_gaps = sorted(predicted_gaps, key=lambda x: x["future_deficiency_score"], reverse=True)

        for gap in sorted_gaps:
            skill = gap["skill_name"]
            if skill in self.content_catalog:
                # Select lessons that match the required proficiency uplift
                relevant_lessons = [
                    l for l in self.content_catalog[skill] if l["difficulty"] >= gap["current_proficiency"]
                ]
                path.extend(relevant_lessons[:3])  # Limit to top 3 most relevant per skill

        logger.info(f"Generated initial path with {len(path)} lessons.")
        return path

    def adapt_path(self, current_path: list[dict], last_quiz_score: float) -> list[dict]:
        """
        Adjusts the remaining path based on the most recent quiz performance.
        - Score < 0.6: Insert remedial/prerequisite lessons.
        - Score > 0.9: Skip ahead to more advanced modules.
        """
        if not current_path:
            return current_path

        adapted = []
        for lesson in current_path:
            if last_quiz_score < 0.6:
                # Find a simpler version or prerequisite
                remedial = self._find_prerequisite(lesson)
                if remedial:
                    adapted.append(remedial)
            elif last_quiz_score > 0.9:
                # Skip this lesson if it's too easy
                continue

            adapted.append(lesson)

        logger.info(f"Adapted path. New length: {len(adapted)}")
        return adapted

    def _find_prerequisite(self, lesson: dict) -> dict:
        """
        Helper to find a lower-difficulty lesson for the same skill.
        """
        skill = lesson.get("skill_name", "General")
        target_difficulty = max(0, lesson["difficulty"] - 0.2)

        candidates = [l for l in self.content_catalog.get(skill, []) if l["difficulty"] <= target_difficulty]
        return candidates[-1] if candidates else None
