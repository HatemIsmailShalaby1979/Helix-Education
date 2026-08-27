"""Feedback Service — generates human-readable feedback from scoring results.

Pure transformation functions — no side effects, no I/O.
"""

from datetime import UTC, datetime

from learning_service import LearningService
from state_core.scoring_engine import ScoreResult

from .delivery_models import FeedbackLevel, FeedbackMessage, SessionLog


class FeedbackService:
    """Generates learner-facing feedback from scoring and state data.

    Inputs:
        learning_service: A LearningService for state queries.
    """

    def __init__(self, learning_service: LearningService) -> None:
        self._learning = learning_service

    def score_feedback(self, result: ScoreResult) -> FeedbackMessage:
        """Generate human-readable feedback from a ScoreResult.

        Inputs:
            result: The ScoreResult from an answer submission.
        Returns:
            A FeedbackMessage with level-appropriate messaging.
        """
        if result.passed:
            return FeedbackMessage(
                level=FeedbackLevel.SUCCESS,
                title="Correct!",
                body=(
                    f"Score: {result.raw_score:.0%}. "
                    f"You matched {len(result.matched_keywords)} of "
                    f"{len(result.matched_keywords) + len(result.missing_keywords)} "
                    f"required keywords."
                ),
            )
        else:
            details = []
            if result.missing_keywords:
                details.append(f"Missing keywords: {', '.join(result.missing_keywords)}")
            return FeedbackMessage(
                level=FeedbackLevel.WARNING,
                title="Needs Improvement",
                body=(f"Score: {result.raw_score:.0%}. Passing threshold is 60%."),
                details=details,
            )

    def topic_progress_feedback(self, topic: str) -> FeedbackMessage:
        """Generate feedback on a learner's progress in a topic.

        Inputs:
            topic: The topic name.
        Returns:
            A FeedbackMessage summarizing progress.
        """
        state = self._learning.get_topic_state(topic)
        level = self._learning.compute_topic_level(topic)

        # Check if the topic has been started (TopicStartedEvent exists)
        from state_core.event_models import TopicStartedEvent

        events = self._learning._event_store.read_all()
        topic_started = any(isinstance(e, TopicStartedEvent) and e.topic == topic for e in events)

        if state.is_passed:
            return FeedbackMessage(
                level=FeedbackLevel.SUCCESS,
                title=f"Topic Passed: {topic}",
                body=(
                    f"You passed {topic} at {state.current_level} level "
                    f"with {state.attempts_total} attempt(s). "
                    f"Pass rate: {self._pass_rate(state.pass_count, state.attempts_total):.0%}."
                ),
            )
        elif state.attempts_total > 0 or topic_started:
            return FeedbackMessage(
                level=FeedbackLevel.INFO,
                title=f"In Progress: {topic}",
                body=(
                    f"Current level: {level}. "
                    f"Attempts: {state.attempts_total} "
                    f"(passed: {state.pass_count}, failed: {state.fail_count}). "
                    f"Pass rate: {self._pass_rate(state.pass_count, state.attempts_total):.0%}."
                ),
            )
        else:
            return FeedbackMessage(
                level=FeedbackLevel.INFO,
                title=f"Not Started: {topic}",
                body=f"You have not started studying {topic} yet.",
            )

    def session_started(self, session_id: str) -> SessionLog:
        """Create a new session log entry.

        Inputs:
            session_id: Unique session identifier.
        Returns:
            A new SessionLog with the start timestamp.
        """
        return SessionLog(
            session_id=session_id,
            started_at=datetime.now(UTC).isoformat(),
        )

    def session_log_entry(
        self,
        log: SessionLog,
        message: str,
    ) -> SessionLog:
        """Append an entry to a session log (returns new instance).

        Inputs:
            log: The existing SessionLog.
            message: The message to append.
        Returns:
            A new SessionLog with the entry appended.
        """
        new_entries = list(log.entries) + [f"[{datetime.now(UTC).isoformat()}] {message}"]
        return SessionLog(
            session_id=log.session_id,
            entries=new_entries,
            started_at=log.started_at,
        )

    @staticmethod
    def _pass_rate(pass_count: int, attempts_total: int) -> float:
        if attempts_total == 0:
            return 0.0
        return pass_count / attempts_total
