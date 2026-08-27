"""Tests for content_engine module."""

import pytest

from content_engine import ContentService, Lesson, Section
from learning_service import LearningService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig


@pytest.fixture
def content_service(tmp_path) -> ContentService:
    """Provide a ContentService backed by temp EventStore."""
    es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
    ks = SealedAnswerKeyStore()
    ls = LearningService(es, ks)
    return ContentService(ls)


class TestContentModels:
    """Tests for content data models."""

    def test_section_creation(self) -> None:
        s = Section(
            section_id="sec_1",
            title="Introduction",
            body="Hello world",
            source_citations=["src1"],
        )
        assert s.section_id == "sec_1"
        assert s.title == "Introduction"
        assert s.body == "Hello world"
        assert s.source_citations == ["src1"]

    def test_lesson_creation(self) -> None:
        s = Section(section_id="s1", title="Intro", body="Body")
        lesson = Lesson(topic="algebra", title="Algebra 101", sections=[s])
        assert lesson.topic == "algebra"
        assert lesson.title == "Algebra 101"
        assert len(lesson.sections) == 1
        assert lesson.sections[0].section_id == "s1"

    def test_lesson_default_sections_empty(self) -> None:
        lesson = Lesson(topic="python", title="Python Basics")
        assert lesson.sections == []


class TestContentService:
    """Tests for the Content Service."""

    def test_create_lesson(self, content_service) -> None:
        lesson = content_service.create_lesson("algebra", "Algebra 101")
        assert lesson.topic == "algebra"
        assert lesson.title == "Algebra 101"

    def test_create_duplicate_lesson_raises(self, content_service) -> None:
        content_service.create_lesson("algebra", "Algebra 101")
        with pytest.raises(ValueError, match="already exists"):
            content_service.create_lesson("algebra", "Duplicate")

    def test_get_lesson_found(self, content_service) -> None:
        content_service.create_lesson("algebra", "Algebra 101")
        lesson = content_service.get_lesson("algebra")
        assert lesson is not None
        assert lesson.title == "Algebra 101"

    def test_get_lesson_not_found(self, content_service) -> None:
        assert content_service.get_lesson("nonexistent") is None

    def test_commit_section(self, content_service) -> None:
        content_service.create_lesson("algebra", "Algebra 101")
        section = content_service.commit_section(
            topic="algebra",
            section_id="sec_001",
            title="Introduction",
            body="This is the intro section.",
            source_citations=["wiki/algebra"],
        )
        assert section.section_id == "sec_001"
        assert section.title == "Introduction"
        assert section.body == "This is the intro section."
        assert section.source_citations == ["wiki/algebra"]

        # Verify the section is stored in the lesson
        lesson = content_service.get_lesson("algebra")
        assert lesson is not None
        assert len(lesson.sections) == 1
        assert lesson.sections[0].section_id == "sec_001"

    def test_commit_section_no_citations(self, content_service) -> None:
        content_service.create_lesson("algebra", "Algebra 101")
        section = content_service.commit_section(
            topic="algebra",
            section_id="s1",
            title="Intro",
            body="Body",
        )
        assert section.source_citations == []

    def test_commit_section_no_lesson_auto_creates(self, content_service) -> None:
        section = content_service.commit_section(
            topic="algebra",
            section_id="s1",
            title="T",
            body="B",
        )
        assert section.section_id == "s1"
        lesson = content_service.get_lesson("algebra")
        assert lesson is not None
        assert lesson.topic == "algebra"

    def test_commit_section_emits_event(self, content_service) -> None:
        content_service.create_lesson("algebra", "Algebra 101")
        content_service.commit_section(
            topic="algebra",
            section_id="sec_001",
            title="Intro",
            body="Body",
            source_citations=["src"],
        )
        # Verify the event was appended to the store
        events = content_service._learning._event_store.read_all()
        committed = [e for e in events if hasattr(e, "section_id")]
        assert len(committed) == 1
        assert committed[0].section_id == "sec_001"
        assert committed[0].source_citations == ["src"]

    def test_list_topics(self, content_service) -> None:
        assert content_service.list_topics() == []
        content_service.create_lesson("algebra", "Algebra 101")
        content_service.create_lesson("geometry", "Geometry Basics")
        assert content_service.list_topics() == ["algebra", "geometry"]

    def test_remove_lesson(self, content_service) -> None:
        content_service.create_lesson("algebra", "Algebra 101")
        content_service.remove_lesson("algebra")
        assert content_service.get_lesson("algebra") is None

    def test_remove_nonexistent_lesson_raises(self, content_service) -> None:
        with pytest.raises(ValueError, match="No lesson found"):
            content_service.remove_lesson("nonexistent")

    def test_multiple_sections_in_order(self, content_service) -> None:
        content_service.create_lesson("algebra", "Algebra 101")
        content_service.commit_section("algebra", "s1", "Intro", "Intro text")
        content_service.commit_section("algebra", "s2", "Basics", "Basics text")
        content_service.commit_section("algebra", "s3", "Advanced", "Advanced text")
        lesson = content_service.get_lesson("algebra")
        assert lesson is not None
        assert [s.section_id for s in lesson.sections] == ["s1", "s2", "s3"]

    # ── Fix 3: create_lesson() emits TopicStartedEvent ──────────────

    def test_create_lesson_survives_restart_without_commit_section(self, tmp_path) -> None:
        """A lesson created via create_lesson() alone (no commit_section() call)
        survives a simulated restart — i.e., appears in _lessons after a fresh
        ContentService is constructed against the same event_store (Fix 3)."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        # First service: create lesson but don't commit any sections
        cs1 = ContentService(ls)
        cs1.create_lesson("algebra", "Algebra 101", difficulty="easy")

        # Simulate restart: create new ContentService against same event store
        cs2 = ContentService(ls)
        lesson = cs2.get_lesson("algebra")
        assert lesson is not None
        assert lesson.topic == "algebra"
        assert lesson.title == "Algebra 101"
        assert lesson.difficulty == "easy"

    # ── Fix 4: commit_section() write ordering ──────────────────────

    def test_commit_section_raises_and_leaves_state_unchanged_on_event_failure(
        self, content_service, monkeypatch
    ) -> None:
        """commit_section() raises and leaves lesson.sections unchanged when
        the event store append is mocked to throw (Fix 4)."""
        content_service.create_lesson("algebra", "Algebra 101")
        lesson = content_service.get_lesson("algebra")
        assert lesson is not None
        initial_section_count = len(lesson.sections)

        # Mock commit_lesson_section to raise an exception
        def failing_commit(*args, **kwargs):
            raise RuntimeError("Simulated event store failure")

        monkeypatch.setattr(content_service._learning, "commit_lesson_section", failing_commit)

        with pytest.raises(RuntimeError, match="Simulated event store failure"):
            content_service.commit_section(
                topic="algebra",
                section_id="sec_001",
                title="Intro",
                body="Body",
                source_citations=["src"],
            )

        # In-memory state must NOT have the section appended
        lesson = content_service.get_lesson("algebra")
        assert lesson is not None
        assert len(lesson.sections) == initial_section_count

    # ── Fix A: Reversible topic deletion ────────────────────────────

    def test_deleted_topic_reactivated_by_later_topic_started(self, tmp_path) -> None:
        """A deleted topic reactivated by a later TopicStartedEvent appears
        again in ContentService._lessons after a fresh instantiation (Fix A)."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        # First service: create lesson, then delete it
        cs1 = ContentService(ls)
        cs1.create_lesson("algebra", "Algebra 101")
        cs1.remove_lesson("algebra")
        assert cs1.get_lesson("algebra") is None

        # Now create a new lesson with the same topic (simulates reactivation)
        cs1.create_lesson("algebra", "Algebra 101 Reactivated")

        # Simulate restart: create new ContentService against same event store
        cs2 = ContentService(ls)
        lesson = cs2.get_lesson("algebra")
        assert lesson is not None
        assert lesson.topic == "algebra"
        assert lesson.title == "Algebra 101 Reactivated"

    # ── Fix 1: commit_section() update-in-place for duplicate section_id ──

    def test_commit_section_update_in_place_same_section_id(self, content_service) -> None:
        """Calling commit_section() twice with the same section_id for the same
        topic updates the section in place (Option A). Exactly one section exists
        afterward with the content from the second call."""
        content_service.create_lesson("algebra", "Algebra 101")

        # First commit
        section1 = content_service.commit_section(
            topic="algebra",
            section_id="sec_001",
            title="Introduction",
            body="First version of the intro.",
            source_citations=["src1"],
        )
        assert section1.title == "Introduction"
        assert section1.body == "First version of the intro."
        assert section1.source_citations == ["src1"]

        lesson = content_service.get_lesson("algebra")
        assert lesson is not None
        assert len(lesson.sections) == 1

        # Second commit with same section_id — should UPDATE in place
        section2 = content_service.commit_section(
            topic="algebra",
            section_id="sec_001",
            title="Updated Introduction",
            body="Second version of the intro, expanded.",
            source_citations=["src1", "src2"],
        )
        assert section2.title == "Updated Introduction"
        assert section2.body == "Second version of the intro, expanded."
        assert section2.source_citations == ["src1", "src2"]

        # Only one section should exist, with the UPDATED content
        lesson = content_service.get_lesson("algebra")
        assert lesson is not None
        assert len(lesson.sections) == 1
        assert lesson.sections[0].section_id == "sec_001"
        assert lesson.sections[0].title == "Updated Introduction"
        assert lesson.sections[0].body == "Second version of the intro, expanded."
        assert lesson.sections[0].source_citations == ["src1", "src2"]

    def test_commit_section_update_in_place_survives_restart(self, tmp_path) -> None:
        """After a simulated restart (fresh ContentService against same
        event_store), the updated section content from the second commit
        is what appears — not the first version, and not a duplicate."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        # First service: create lesson and commit section twice (update)
        cs1 = ContentService(ls)
        cs1.create_lesson("algebra", "Algebra 101")
        cs1.commit_section(
            topic="algebra",
            section_id="sec_001",
            title="Introduction",
            body="First version of the intro.",
            source_citations=["src1"],
        )
        cs1.commit_section(
            topic="algebra",
            section_id="sec_001",
            title="Updated Introduction",
            body="Second version of the intro, expanded.",
            source_citations=["src1", "src2"],
        )

        # Verify live state after second commit
        lesson1 = cs1.get_lesson("algebra")
        assert lesson1 is not None
        assert len(lesson1.sections) == 1
        assert lesson1.sections[0].title == "Updated Introduction"
        assert lesson1.sections[0].body == "Second version of the intro, expanded."

        # Simulate restart: create new ContentService against same event store
        cs2 = ContentService(ls)
        lesson2 = cs2.get_lesson("algebra")
        assert lesson2 is not None
        assert len(lesson2.sections) == 1
        # Post-restart state must match live state: updated content, not original
        assert lesson2.sections[0].section_id == "sec_001"
        assert lesson2.sections[0].title == "Updated Introduction"
        assert lesson2.sections[0].body == "Second version of the intro, expanded."
        assert lesson2.sections[0].source_citations == ["src1", "src2"]
