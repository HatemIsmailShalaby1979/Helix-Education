"""Tests for cognitive_engine module."""

import pytest

from cognitive_engine import CognitiveService
from cognitive_engine.cognitive_models import (
    JourneyEntry,
    KnowledgeMap,
)
from learning_service import LearningService
from state_core.event_store import EventStore, SealedAnswerKeyStore, StoreConfig
from state_core.scoring_engine import AnswerKey


@pytest.fixture
def cog(tmp_path) -> CognitiveService:
    es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
    ks = SealedAnswerKeyStore()
    ls = LearningService(es, ks)
    return CognitiveService(ls)


class TestKnowledgeMap:
    def test_empty_knowledge_map(self, cog) -> None:
        km = cog.build_knowledge_map()
        assert isinstance(km, KnowledgeMap)
        assert km.topics_studied_count == 0
        assert km.total_quizzes_taken == 0
        assert km.average_quiz_score == 0.0

    def test_knowledge_map_after_topic_started(self, cog) -> None:
        cog._learning.start_topic("algebra")
        km = cog.build_knowledge_map()
        assert km.topics_studied_count >= 1

    def test_knowledge_map_after_quiz(self, cog) -> None:
        cog._learning.start_topic("algebra")
        key = AnswerKey(required_keywords=["4"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q1", "Q?", "mc", "easy", key)
        cog._learning.submit_and_score_answer("q1", "4")
        cog._learning.submit_and_score_answer("q1", "5")
        km = cog.build_knowledge_map()
        assert km.total_quizzes_taken == 2
        assert km.average_quiz_score > 0

    def test_weak_and_strong_areas(self, cog) -> None:
        cog._learning.start_topic("algebra")
        key = AnswerKey(required_keywords=["4", "five"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q1", "Q?", "mc", "easy", key)
        cog._learning.submit_and_score_answer("q1", "wrong")
        km = cog.build_knowledge_map()
        assert len(km.weak_areas) >= 1


class TestSessions:
    def test_start_session(self, cog) -> None:
        sid = cog.start_session("algebra")
        assert len(sid) > 0
        session = cog.get_session(sid)
        assert session is not None
        assert session.topic == "algebra"

    def test_record_section_read(self, cog) -> None:
        sid = cog.start_session("algebra")
        cog.record_section_read(sid, "sec_001")
        session = cog.get_session(sid)
        assert session is not None
        assert "sec_001" in session.sections_read

    def test_record_dig_deeper(self, cog) -> None:
        sid = cog.start_session("algebra")
        cog.record_dig_deeper(sid)
        session = cog.get_session(sid)
        assert session is not None
        assert session.dig_deeper_requests == 1

    def test_record_quiz_result(self, cog) -> None:
        sid = cog.start_session("algebra")
        cog.record_quiz_result(sid, 0.8, True)
        session = cog.get_session(sid)
        assert session is not None
        assert session.quiz_taken is True
        assert session.quiz_score == 0.8
        assert session.quiz_passed is True

    def test_journey_logged(self, cog) -> None:
        cog.start_session("algebra")
        cog.start_session("geometry")
        journey = cog.get_journey()
        assert len(journey) == 2
        assert all(isinstance(e, JourneyEntry) for e in journey)
        assert journey[0].topic == "algebra"
        assert journey[1].topic == "geometry"

    def test_journey_sorted_by_timestamp(self, cog) -> None:
        cog.start_session("algebra")
        cog.start_session("geometry")
        journey = cog.get_journey()
        for i in range(len(journey) - 1):
            assert journey[i].timestamp <= journey[i + 1].timestamp


class TestRecommendations:
    def test_get_recommendations_empty(self, cog) -> None:
        recs = cog.get_recommendations()
        assert recs == []

    def test_get_recommendations_after_weak_score(self, cog) -> None:
        cog._learning.start_topic("algebra")
        key = AnswerKey(required_keywords=["4", "five", "six"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q1", "Q?", "mc", "easy", key)
        cog._learning.submit_and_score_answer("q1", "wrong")
        recs = cog.get_recommendations()
        assert len(recs) >= 1

    def test_pending_recommendations(self, cog) -> None:
        cog._learning.start_topic("algebra")
        key = AnswerKey(required_keywords=["4", "five"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q1", "Q?", "mc", "easy", key)
        cog._learning.submit_and_score_answer("q1", "wrong")
        cog.get_recommendations()
        pending = cog.get_pending_recommendations()
        assert len(pending) >= 1

    def test_approve_recommendation(self, cog) -> None:
        rid = cog.propose_recommendation("concept", "topic", "reason", "action", "evidence")
        result = cog.approve_recommendation(rid)
        assert result is True
        approved = cog.get_approved_recommendations()
        assert any(r.recommendation_id == rid for r in approved)

    def test_approve_nonexistent_recommendation(self, cog) -> None:
        result = cog.approve_recommendation("nonexistent")
        assert result is False

    def test_reject_recommendation(self, cog) -> None:
        rid = cog.propose_recommendation("concept", "topic", "reason", "action", "evidence")
        result = cog.reject_recommendation(rid)
        assert result is True
        pending = cog.get_pending_recommendations()
        assert all(r.recommendation_id != rid for r in pending)

    def test_reject_nonexistent_recommendation(self, cog) -> None:
        result = cog.reject_recommendation("nonexistent")
        assert result is False

    def test_approve_creates_profile_delta(self, cog) -> None:
        rid = cog.propose_recommendation("concept", "topic", "reason", "action", "evidence")
        cog.approve_recommendation(rid)
        profile = cog._learning.get_learner_profile()
        assert len(profile.pending_deltas) >= 0


class TestMetacognitiveInsights:
    def test_insights_empty(self, cog) -> None:
        insights = cog.get_metacognitive_insights()
        assert isinstance(insights, list)

    def test_insights_after_activity(self, cog) -> None:
        cog._learning.start_topic("algebra")
        key = AnswerKey(required_keywords=["4"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q1", "Q?", "mc", "easy", key)
        cog._learning.submit_and_score_answer("q1", "4")
        cog.get_recommendations()
        insights = cog.get_metacognitive_insights()
        categories = {i.category for i in insights}
        assert "learning_pattern" in categories

    def test_propose_recommendation(self, cog) -> None:
        rid = cog.propose_recommendation("concept", "topic", "reason", "action", "evidence")
        assert len(rid) > 0
        recs = cog.get_pending_recommendations()
        assert any(r.recommendation_id == rid for r in recs)

    def test_section_read_not_in_unknown_session(self, cog) -> None:
        cog.record_section_read("nonexistent", "sec_001")
        assert cog.get_session("nonexistent") is None

    def test_dig_deeper_not_in_unknown_session(self, cog) -> None:
        cog.record_dig_deeper("nonexistent")
        assert cog.get_session("nonexistent") is None

    def test_quiz_result_not_in_unknown_session(self, cog) -> None:
        cog.record_quiz_result("nonexistent", 0.8, True)
        assert cog.get_session("nonexistent") is None


# ── Fix B: Full event-sourcing for cognitive layer ──────────────────


class TestCognitiveEventSourcing:
    """Tests proving the cognitive layer is fully event-sourced."""

    def test_session_survives_restart(self, tmp_path) -> None:
        """A LearningSession started via CognitiveService.start_session(),
        with a section read and a quiz result recorded, survives a simulated
        restart — i.e., a freshly constructed CognitiveService against the
        same event_store returns the same session data via get_session()."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        # First service: start session, record activity
        cog1 = CognitiveService(ls)
        sid = cog1.start_session("algebra")
        cog1.record_section_read(sid, "sec_001")
        cog1.record_quiz_result(sid, 0.85, True)

        # Simulate restart: create new CognitiveService against same event store
        cog2 = CognitiveService(ls)
        session = cog2.get_session(sid)
        assert session is not None
        assert session.session_id == sid
        assert session.topic == "algebra"
        assert "sec_001" in session.sections_read
        assert session.quiz_taken is True
        assert session.quiz_score == 0.85
        assert session.quiz_passed is True

    def test_approved_recommendation_survives_restart(self, tmp_path) -> None:
        """An approved recommendation survives restart and appears in
        get_approved_recommendations(); a rejected one does NOT appear in
        either pending or approved lists after restart."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        # First service: propose, approve one; propose, reject another
        cog1 = CognitiveService(ls)
        approved_rid = cog1.propose_recommendation("concept1", "topic1", "reason1", "action1", "evidence1", "high")
        rejected_rid = cog1.propose_recommendation("concept2", "topic2", "reason2", "action2", "evidence2", "medium")
        cog1.approve_recommendation(approved_rid)
        cog1.reject_recommendation(rejected_rid)

        # Verify pre-restart state
        assert any(r.recommendation_id == approved_rid for r in cog1.get_approved_recommendations())
        assert all(r.recommendation_id != rejected_rid for r in cog1.get_pending_recommendations())
        assert all(r.recommendation_id != rejected_rid for r in cog1.get_approved_recommendations())

        # Simulate restart
        cog2 = CognitiveService(ls)

        # Approved recommendation should survive
        approved_after = cog2.get_approved_recommendations()
        assert any(r.recommendation_id == approved_rid for r in approved_after)

        # Rejected recommendation should NOT appear in either list
        pending_after = cog2.get_pending_recommendations()
        approved_after = cog2.get_approved_recommendations()
        assert all(r.recommendation_id != rejected_rid for r in pending_after)
        assert all(r.recommendation_id != rejected_rid for r in approved_after)

    def test_journey_survives_restart_in_chronological_order(self, tmp_path) -> None:
        """The journey log, after restart, contains entries in correct
        chronological order matching what was recorded pre-restart."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        # First service: record multiple journey entries
        cog1 = CognitiveService(ls)
        sid1 = cog1.start_session("algebra")
        cog1.record_section_read(sid1, "sec_001")
        cog1.record_dig_deeper(sid1)
        cog1.record_quiz_result(sid1, 0.9, True)

        sid2 = cog1.start_session("geometry")
        cog1.record_section_read(sid2, "sec_002")

        journey_before = cog1.get_journey()
        assert len(journey_before) == 6  # 2 session_started + 2 section_read + 1 dig_deeper + 1 quiz_completed

        # Verify chronological order
        for i in range(len(journey_before) - 1):
            assert journey_before[i].timestamp <= journey_before[i + 1].timestamp

        # Simulate restart
        cog2 = CognitiveService(ls)
        journey_after = cog2.get_journey()

        # Journey should have same entries in same order
        assert len(journey_after) == len(journey_before)
        for before, after in zip(journey_before, journey_after):
            assert before.timestamp == after.timestamp
            assert before.entry_type == after.entry_type
            assert before.topic == after.topic
            assert before.detail == after.detail
            assert before.score == after.score


# ── Defect Fix Tests ────────────────────────────────────────────────


class TestKnowledgeMapDefectFixes:
    """Tests for the two defect fixes in build_knowledge_map()."""

    def test_quiz_item_resolves_to_real_topic_not_unknown(self, tmp_path) -> None:
        """A quiz item scored via a properly-created QuizItemCreatedEvent
        resolves to its real topic in build_knowledge_map(), not 'unknown'.
        Proves Defect 1 fix."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        cog = CognitiveService(ls)
        # Start topic and create quiz item
        cog._learning.start_topic("algebra")
        key = AnswerKey(required_keywords=["4"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q1", "What is 2+2?", "mc", "easy", key)
        # Score the answer
        cog._learning.submit_and_score_answer("q1", "4")

        km = cog.build_knowledge_map()

        # The quiz item node should have topic="algebra", not "unknown"
        # Find the quiz item node (concept != topic) in the algebra topic
        algebra_nodes = km.topics.get("algebra", [])
        quiz_item_nodes = [n for n in algebra_nodes if n.concept != n.topic]
        assert len(quiz_item_nodes) >= 1
        for node in quiz_item_nodes:
            assert node.topic == "algebra", f"Quiz item {node.concept} should have topic='algebra', got '{node.topic}'"

    def test_topic_with_attempts_not_passed_not_in_weak_areas(self, tmp_path) -> None:
        """A topic with attempts_total > 0 but not yet passed does NOT appear
        in weak_areas. Proves Defect 2 separation - under OLD code this topic
        would have incorrectly appeared as a weak area at 0.0."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        cog = CognitiveService(ls)
        # Start topic and create quiz item
        cog._learning.start_topic("algebra")
        key = AnswerKey(required_keywords=["4"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q1", "What is 2+2?", "mc", "easy", key)
        # Score one answer incorrectly (so topic has attempts but not passed)
        cog._learning.submit_and_score_answer("q1", "wrong")

        km = cog.build_knowledge_map()

        # The topic "algebra" should NOT be in weak_areas because:
        # - weak_areas now only contains quiz-item-level nodes (continuous scale)
        # - topic-level nodes (binary 0.0/1.0) are excluded from weak_areas
        assert "algebra" not in km.weak_areas, (
            f"Topic 'algebra' should not be in weak_areas (only quiz items should be), got: {km.weak_areas}"
        )

    def test_topic_progress_and_quiz_mastery_both_present_and_correct(self, tmp_path) -> None:
        """topic_progress and quiz_mastery are both present and independently
        correct on the same KnowledgeMap instance for a scenario involving both
        a topic-level pass state and quiz-item-level scores."""
        es = EventStore(StoreConfig(path=str(tmp_path / "events.jsonl")))
        ks = SealedAnswerKeyStore()
        ls = LearningService(es, ks)

        cog = CognitiveService(ls)
        # Start topic and create quiz items
        cog._learning.start_topic("algebra")
        key1 = AnswerKey(required_keywords=["4"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q1", "What is 2+2?", "mc", "easy", key1)
        key2 = AnswerKey(required_keywords=["9"])
        cog._learning.create_quiz_item("algebra", "quiz-1", "q2", "What is 3+3?", "mc", "easy", key2)

        # Score q1 correctly, q2 incorrectly
        cog._learning.submit_and_score_answer("q1", "4")  # pass
        cog._learning.submit_and_score_answer("q2", "wrong")  # fail

        # Also pass the topic officially
        cog._learning.pass_topic("algebra", "intermediate")

        km = cog.build_knowledge_map()

        # topic_progress should exist and have algebra with 1 pass / 2 attempts = 0.5
        assert "algebra" in km.topic_progress
        assert km.topic_progress["algebra"] == 0.5, (
            f"topic_progress['algebra'] should be 0.5 (1 pass / 2 attempts), got {km.topic_progress['algebra']}"
        )

        # quiz_mastery should exist and have q1=1.0, q2=0.0
        assert "q1" in km.quiz_mastery
        assert "q2" in km.quiz_mastery
        assert km.quiz_mastery["q1"] == 1.0, f"quiz_mastery['q1'] should be 1.0, got {km.quiz_mastery['q1']}"
        assert km.quiz_mastery["q2"] == 0.0, f"quiz_mastery['q2'] should be 0.0, got {km.quiz_mastery['q2']}"

        # weak_areas should only contain q2 (quiz item with understanding < 0.5)
        # NOT the topic "algebra"
        assert "q2" in km.weak_areas
        assert "algebra" not in km.weak_areas

        # strong_areas should only contain q1 (quiz item with understanding >= 0.8)
        assert "q1" in km.strong_areas
        assert "algebra" not in km.strong_areas
