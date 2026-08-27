"""Content Service — CRUD operations for lessons and sections.

Uses an in-memory store (dict-backed) with optional file persistence.
The service coordinates with the Learning Service by also emitting
LessonSectionCommittedEvent through the EventStore, ensuring the event
log stays in sync with the content store.
"""

from dataclasses import dataclass

from learning_service import LearningService

from .content_models import Lesson, Section


@dataclass
class ContentStoreConfig:
    """Configuration for the Content Engine storage.

    Inputs:
        persist_path: Optional path to a JSON file for persistence.
            If None, content is stored in memory only.
    """

    persist_path: str | None = None


class ContentService:
    """Manages lesson content with in-memory or file-backed storage.

    Coordinates with the Learning Service to emit events when content
    is committed.

    Inputs:
        learning_service: A LearningService instance for event coordination.
        config: ContentStoreConfig for storage settings.
    """

    def __init__(
        self,
        learning_service: LearningService,
        config: ContentStoreConfig | None = None,
    ) -> None:
        self._learning = learning_service
        self._config = config or ContentStoreConfig()
        self._lessons: dict[str, Lesson] = {}
        self._rebuild_from_events()

    def _rebuild_from_events(self) -> None:
        from state_core.event_models import (
            LessonDeletedEvent,
            LessonSectionCommittedEvent,
            TopicStartedEvent,
        )

        # Topic deletion is reversible: a topic is considered deleted only if
        # its most recent lifecycle event (by timestamp) is a LessonDeletedEvent.
        # A later TopicStartedEvent reactivates the topic. See README_STATE_CORE.md.
        last_deletion_timestamp: dict[str, str] = {}
        events = self._learning._event_store.read_all()
        for e in events:
            if isinstance(e, LessonDeletedEvent):
                last_deletion_timestamp[e.topic] = e.timestamp
                self._lessons.pop(e.topic, None)
                continue
            if isinstance(e, TopicStartedEvent):
                if e.topic in last_deletion_timestamp and last_deletion_timestamp[e.topic] > e.timestamp:
                    continue
                if e.topic not in self._lessons:
                    lesson_title = e.lesson_title if e.lesson_title else e.topic
                    self._lessons[e.topic] = Lesson(topic=e.topic, title=lesson_title, difficulty=e.difficulty)
                elif e.lesson_title:
                    self._lessons[e.topic].title = e.lesson_title
                    if e.difficulty:
                        self._lessons[e.topic].difficulty = e.difficulty
                continue
            if isinstance(e, LessonSectionCommittedEvent):
                if e.topic in last_deletion_timestamp and last_deletion_timestamp[e.topic] > e.timestamp:
                    continue
                if e.topic not in self._lessons:
                    lesson_title = e.lesson_title if e.lesson_title else e.topic
                    self._lessons[e.topic] = Lesson(topic=e.topic, title=lesson_title)
                lesson = self._lessons[e.topic]
                # Update-in-place if section_id already exists (consistent with
                # commit_section's update-in-place behavior). This ensures live
                # and replay behavior match: repeated commits for the same
                # section_id overwrite the prior content rather than being skipped.
                for idx, existing in enumerate(lesson.sections):
                    if existing.section_id == e.section_id:
                        lesson.sections[idx] = Section(
                            section_id=e.section_id,
                            title=e.title,
                            body=e.body,
                            source_citations=list(e.source_citations),
                        )
                        break
                else:
                    lesson.sections.append(
                        Section(
                            section_id=e.section_id,
                            title=e.title,
                            body=e.body,
                            source_citations=list(e.source_citations),
                        )
                    )

    def create_lesson(
        self,
        topic: str,
        title: str,
        difficulty: str | None = None,
    ) -> Lesson:
        """Create a new empty lesson for a topic.

        Inputs:
            topic: The topic name.
            title: Human-readable lesson title.
            difficulty: Optional difficulty classification.
        Returns:
            The created Lesson instance.
        Raises:
            ValueError: If a lesson for this topic already exists.
        """
        if topic in self._lessons:
            raise ValueError(f"Lesson already exists for topic: {topic}")
        # Emit TopicStartedEvent before mutating in-memory state so the
        # lesson survives a process restart even if commit_section() is
        # never called.
        self._learning.start_topic(topic=topic, lesson_title=title, difficulty=difficulty)
        lesson = Lesson(topic=topic, title=title, difficulty=difficulty)
        self._lessons[topic] = lesson
        return lesson

    def get_lesson(self, topic: str) -> Lesson | None:
        """Retrieve a lesson by topic.

        Inputs:
            topic: The topic name.
        Returns:
            The Lesson if found, None otherwise.
        """
        return self._lessons.get(topic)

    def commit_section(
        self,
        topic: str,
        section_id: str,
        title: str,
        body: str,
        source_citations: list[str] | None = None,
    ) -> Section:
        """Add or update a section in a lesson and emit a LessonSectionCommittedEvent.

        If a section with the given section_id already exists in the lesson,
        it is UPDATED in place (title, body, and source_citations replaced)
        and a new LessonSectionCommittedEvent is emitted. This update-in-place
        behavior (Option A) is chosen because:
        1. Re-running generation for the same section_id during iteration is
           the normal workflow, not an error.
        2. It matches the _rebuild_from_events() replay logic which also
           updates-in-place, ensuring live and post-restart state are identical.
        3. The alternative (reject duplicate) would require callers to manually
           delete before re-generating, adding friction to the common case.

        Inputs:
            topic: The topic this section belongs to.
            section_id: Unique identifier for the section.
            title: Section title.
            body: Section body text.
            source_citations: Optional list of source references.
        Returns:
            The created or updated Section instance.
        Raises:
            ValueError: If no lesson exists for this topic and auto-create fails.
        """
        lesson = self._lessons.get(topic)
        if lesson is None:
            # Auto-create lesson if it doesn't exist (preserves original behavior)
            lesson = Lesson(topic=topic, title=topic)
            self._lessons[topic] = lesson

        citations = source_citations or []
        section = Section(
            section_id=section_id,
            title=title,
            body=body,
            source_citations=citations,
        )

        # Write event FIRST; only mutate in-memory state on success.
        self._learning.commit_lesson_section(
            topic,
            section_id,
            title,
            body,
            citations,
            lesson_title=lesson.title,
        )

        # Update-in-place if section_id already exists; otherwise append.
        # This ensures live behavior matches _rebuild_from_events() replay.
        for idx, existing in enumerate(lesson.sections):
            if existing.section_id == section_id:
                lesson.sections[idx] = section
                return section
        lesson.sections.append(section)
        return section

    def list_topics(self) -> list[str]:
        """List all topics that have lessons.

        Returns:
            Sorted list of topic names with lessons.
        """
        return sorted(self._lessons.keys())

    def remove_lesson(self, topic: str) -> None:
        """Remove a lesson by topic.

        Emits a LessonDeletedEvent to the event log so replays reflect
        the deletion. Past LessonSectionCommittedEvents are preserved.

        Inputs:
            topic: The topic name.
        Raises:
            ValueError: If no lesson exists for this topic.
        """
        if topic not in self._lessons:
            raise ValueError(f"No lesson found for topic: {topic}")
        from state_core.event_models import LessonDeletedEvent

        event = LessonDeletedEvent.create(topic=topic)
        self._learning._event_store.append(event)
        del self._lessons[topic]
