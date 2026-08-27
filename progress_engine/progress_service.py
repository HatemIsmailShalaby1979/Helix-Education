"""Progress Service — milestone and learning path computation.

Reads the event log through the Learning Service to compute progress,
milestones, and recommend learning paths. Pure computation — no side
effects.
"""

from learning_service import LearningService

from .progress_models import LearningPath, Milestone, MilestoneType


class ProgressService:
    """Computes learner progress, milestones, and recommends paths.

    Pure query service — does not mutate state or append events.

    Inputs:
        learning_service: A LearningService for state queries.
    """

    def __init__(self, learning_service: LearningService) -> None:
        self._learning = learning_service

    def get_milestones(self) -> list[Milestone]:
        """Compute all milestones achieved by the learner.

        Reads all events and derives milestones from the current state.

        Returns:
            A list of Milestone instances sorted by timestamp.
        """
        events = self._learning._event_store.read_all()
        milestones: list[Milestone] = []

        for e in events:
            from state_core.event_models import (
                TopicBranchedEvent,
                TopicPassedEvent,
                TopicStartedEvent,
            )

            if isinstance(e, TopicStartedEvent):
                milestones.append(
                    Milestone(
                        milestone_type=MilestoneType.TOPIC_STARTED,
                        topic=e.topic,
                        detail=e.requested_level or "beginner",
                        timestamp=e.timestamp,
                    )
                )

            elif isinstance(e, TopicPassedEvent):
                milestones.append(
                    Milestone(
                        milestone_type=MilestoneType.TOPIC_PASSED,
                        topic=e.topic,
                        detail=f"passed at {e.final_level}",
                        timestamp=e.timestamp,
                    )
                )

            elif isinstance(e, TopicBranchedEvent):
                milestones.append(
                    Milestone(
                        milestone_type=MilestoneType.BRANCH_EXPLORED,
                        topic=e.child_topic,
                        detail=f"branched from {e.parent_topic}: {e.reason}",
                        timestamp=e.timestamp,
                    )
                )

        return sorted(milestones, key=lambda m: m.timestamp)

    def get_learning_path(self, topics: list[str]) -> LearningPath:
        """Compute a learning path through the given topics.

        Analyzes which topics have been started or passed and recommends
        the next unstarted topic.

        Inputs:
            topics: Ordered list of topic names defining the curriculum.
        Returns:
            A LearningPath with current position and recommendations.
        """
        completed: list[str] = []
        started: list[str] = []

        for topic in topics:
            state = self._learning.get_topic_state(topic)
            if state.is_passed:
                completed.append(topic)
            elif state.attempts_total > 0:
                started.append(topic)

        current_index = len(completed) + len(started)
        if current_index >= len(topics):
            current_index = max(0, len(topics) - 1)

        recommended_next = None
        for topic in topics:
            if topic not in completed and topic not in started:
                recommended_next = topic
                break

        return LearningPath(
            topics=topics,
            current_index=current_index,
            completed_topics=completed,
            recommended_next=recommended_next,
        )

    def get_topic_summary(self, topic: str) -> dict:
        """Get a human-readable summary of a topic's progress.

        Inputs:
            topic: The topic name.
        Returns:
            A dict with level, attempts, pass_rate, is_passed,
            branch_children, and milestones.
        """
        state = self._learning.get_topic_state(topic)
        level = self._learning.compute_topic_level(topic)

        pass_rate = 0.0
        if state.attempts_total > 0:
            pass_rate = round(state.pass_count / state.attempts_total, 2)

        return {
            "topic": topic,
            "level": level,
            "attempts_total": state.attempts_total,
            "pass_count": state.pass_count,
            "fail_count": state.fail_count,
            "pass_rate": pass_rate,
            "is_passed": state.is_passed,
            "branch_children": state.branch_children,
        }
