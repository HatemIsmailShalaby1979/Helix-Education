"""State Mutator — event-sourced persistent learning state.

Listens for QuizResultEvent and updates a UserLearningState with
aggregate statistics and topic-level mastery flags. Every mutation
emits a LearningStateUpdatedEvent to the EventStore, ensuring full
event-sourced traceability.
"""

from state_core.event_models import (
    LearningStateUpdatedEvent,
    QuizItemCreatedEvent,
    QuizResultEvent,
)
from state_core.event_store import EventStore

from .progress_models import UserLearningState


class StateMutatorService:
    """Mutates persistent learning state in response to quiz results.

    Rebuilds UserLearningState from the event log on init and after
    every mutation. State is never stored outside the event log —
    all mutations emit a LearningStateUpdatedEvent.

    Inputs:
        event_store: An EventStore instance for persistence.
    """

    def __init__(self, event_store: EventStore) -> None:
        self._event_store = event_store
        self._state = self._rebuild_from_events()

    def _rebuild_from_events(self) -> UserLearningState:
        """Replay all events to reconstruct the current learning state.

        Returns:
            A UserLearningState rebuilt from the full event log.
        """
        events = self._event_store.read_all()
        state = UserLearningState()

        total_score_sum = 0.0
        answered_items: dict[str, list[float]] = {}
        topic_items: dict[str, set[str]] = {}

        for e in events:
            if isinstance(e, QuizItemCreatedEvent):
                topic_items.setdefault(e.topic, set()).add(e.quiz_item_id)

            elif isinstance(e, QuizResultEvent):
                state.total_questions_studied += 1
                total_score_sum += e.raw_score
                answered_items.setdefault(e.quiz_item_id, []).append(e.raw_score)

        if state.total_questions_studied > 0:
            state.running_average_score = round(total_score_sum / state.total_questions_studied, 4)

        mastered: set[str] = set()
        in_progress: set[str] = set()

        for topic, item_ids in topic_items.items():
            if not item_ids:
                continue
            all_mastered = True
            any_attempted = False
            for item_id in item_ids:
                scores = answered_items.get(item_id, [])
                if scores:
                    any_attempted = True
                    best = max(scores)
                    if best < 0.6:
                        all_mastered = False
                else:
                    all_mastered = False
            if all_mastered and any_attempted:
                mastered.add(topic)
            elif any_attempted:
                in_progress.add(topic)

        state.topics_mastered = sorted(mastered)
        state.topics_in_progress = sorted(in_progress - mastered)

        return state

    def get_state(self) -> UserLearningState:
        """Return the current learning state.

        Returns:
            The current UserLearningState snapshot.
        """
        return self._state

    def process_quiz_result(
        self,
        quiz_id: str,
        quiz_item_id: str,
        raw_score: float,
        passed: bool,
    ) -> None:
        """Process a quiz result by updating state and appending events.

        1. Appends a QuizResultEvent to the event log.
        2. Replays all events to rebuild UserLearningState.
        3. Appends a LearningStateUpdatedEvent with the new state snapshot.

        Inputs:
            quiz_id: The quiz this result belongs to.
            quiz_item_id: The quiz item that was answered.
            raw_score: The computed score (0.0 to 1.0).
            passed: Whether the answer passed the threshold.
        """
        result_event = QuizResultEvent.create(
            quiz_id=quiz_id,
            quiz_item_id=quiz_item_id,
            raw_score=raw_score,
            passed=passed,
        )
        self._event_store.append(result_event)

        self._state = self._rebuild_from_events()

        update_event = LearningStateUpdatedEvent.create(
            total_questions_studied=self._state.total_questions_studied,
            running_average_score=self._state.running_average_score,
            topics_mastered=list(self._state.topics_mastered),
            topics_in_progress=list(self._state.topics_in_progress),
        )
        self._event_store.append(update_event)

    def get_topic_mastery(self, topic: str) -> dict:
        """Get mastery information for a specific topic.

        Inputs:
            topic: The topic to query.
        Returns:
            A dict with is_mastered, is_in_progress, and item_count.
        """
        events = self._event_store.read_all()
        item_ids: set[str] = set()
        answered: dict[str, list[float]] = {}

        for e in events:
            if isinstance(e, QuizItemCreatedEvent) and e.topic == topic:
                item_ids.add(e.quiz_item_id)
            elif isinstance(e, QuizResultEvent):
                if e.quiz_item_id in item_ids:
                    answered.setdefault(e.quiz_item_id, []).append(e.raw_score)

        if not item_ids:
            return {
                "is_mastered": False,
                "is_in_progress": False,
                "item_count": 0,
                "answered_count": 0,
            }

        all_mastered = True
        any_attempted = False
        for item_id in item_ids:
            scores = answered.get(item_id, [])
            if scores:
                any_attempted = True
                if max(scores) < 0.6:
                    all_mastered = False
            else:
                all_mastered = False

        return {
            "is_mastered": all_mastered and any_attempted,
            "is_in_progress": any_attempted and not (all_mastered and any_attempted),
            "item_count": len(item_ids),
            "answered_count": len([i for i in item_ids if i in answered]),
        }
