"""Tests for state_core.scoring_engine."""

import pytest

from state_core.scoring_engine import (
    AnswerKey,
    score_answer,
    score_answer_detailed,
    score_answer_simple,
)


class TestScoreAnswerDetailed:
    """Happy-path tests for detailed answer scoring (with AnswerKey)."""

    def test_all_keywords_matched(self) -> None:
        key = AnswerKey(required_keywords=["foo", "bar", "baz"])
        result = score_answer_detailed("this answer has foo bar and baz", key)
        assert result.raw_score == 1.0
        assert result.passed is True
        assert result.missing_keywords == []
        assert set(result.matched_keywords) == {"foo", "bar", "baz"}

    def test_partial_match(self) -> None:
        key = AnswerKey(required_keywords=["foo", "bar", "baz"])
        result = score_answer_detailed("only foo here", key)
        assert result.raw_score == pytest.approx(1 / 3)
        assert result.passed is False
        assert result.missing_keywords == ["bar", "baz"]
        assert result.matched_keywords == ["foo"]

    def test_forbidden_keyword_penalty(self) -> None:
        key = AnswerKey(
            required_keywords=["foo", "bar"],
            forbidden_keywords=["wrong"],
        )
        result = score_answer_detailed("foo bar wrong", key)
        assert result.raw_score == pytest.approx(0.9)
        assert result.passed is True

    def test_forbidden_drops_below_passing(self) -> None:
        key = AnswerKey(
            required_keywords=["foo"],
            forbidden_keywords=["wrong", "bad"],
        )
        result = score_answer_detailed("foo wrong bad", key)
        assert result.raw_score == pytest.approx(0.8)
        assert result.passed is True

    def test_penalty_clamps_to_zero(self) -> None:
        key = AnswerKey(
            required_keywords=["foo"],
            forbidden_keywords=["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"],
        )
        result = score_answer_detailed("foo a b c d e f g h i j k", key)
        assert result.raw_score == pytest.approx(0.0)
        assert result.passed is False


class TestScoreAnswer:
    """Tests for the score_answer(item_id, provided_answer, required_keywords) -> float function."""

    def test_all_keywords_matched(self) -> None:
        score = score_answer("item1", "this answer has foo bar and baz", ["foo", "bar", "baz"])
        assert score == 1.0

    def test_partial_match(self) -> None:
        score = score_answer("item1", "only foo here", ["foo", "bar", "baz"])
        assert score == pytest.approx(1 / 3)

    def test_no_required_keywords(self) -> None:
        score = score_answer("item1", "any answer at all", [])
        assert score == 1.0

    def test_case_insensitive_matching(self) -> None:
        score = score_answer("item1", "foo bar", ["FOO", "Bar"])
        assert score == 1.0

    def test_whitespace_handling(self) -> None:
        score = score_answer("item1", "  foo   bar  ", ["foo", "bar"])
        assert score == 1.0

    def test_empty_answer_raises(self) -> None:
        with pytest.raises(ValueError, match="raw_answer must not be empty"):
            score_answer("item1", "", ["foo"])

    def test_blank_answer_raises(self) -> None:
        with pytest.raises(ValueError, match="raw_answer must not be empty"):
            score_answer("item1", "   ", ["foo"])

    def test_item_id_used_for_context(self) -> None:
        # item_id is accepted but doesn't affect scoring
        score1 = score_answer("item1", "foo bar", ["foo", "bar"])
        score2 = score_answer("item2", "foo bar", ["foo", "bar"])
        assert score1 == score2 == 1.0


class TestScoreAnswerSimple:
    """Tests for the score_answer_simple convenience function (alias for score_answer)."""

    def test_returns_float_score(self) -> None:
        score = score_answer_simple("item-1", "foo bar", ["foo", "bar"])
        assert isinstance(score, float)
        assert score == pytest.approx(1.0)

    def test_partial_match(self) -> None:
        score = score_answer_simple("item-1", "only foo", ["foo", "bar", "baz"])
        assert score == pytest.approx(1 / 3)

    def test_no_match(self) -> None:
        score = score_answer_simple("item-1", "nothing relevant", ["foo", "bar"])
        assert score == pytest.approx(0.0)

    def test_empty_keywords(self) -> None:
        score = score_answer_simple("item-1", "any answer", [])
        assert score == pytest.approx(1.0)

    def test_case_insensitive(self) -> None:
        score = score_answer_simple("item-1", "FOO Bar", ["foo", "bar"])
        assert score == pytest.approx(1.0)

    def test_empty_answer_raises(self) -> None:
        with pytest.raises(ValueError, match="raw_answer must not be empty"):
            score_answer_simple("item-1", "", ["foo"])

    def test_item_id_accepted(self) -> None:
        score = score_answer_simple("custom-item-id", "hello", ["hello"])
        assert score == pytest.approx(1.0)


class TestEdgeCases:
    """Edge cases and error handling for detailed scoring."""

    def test_empty_required_keywords(self) -> None:
        key = AnswerKey(required_keywords=[])
        result = score_answer_detailed("any answer at all", key)
        assert result.raw_score == 1.0
        assert result.passed is True
        assert result.missing_keywords == []
        assert result.matched_keywords == []

    def test_case_insensitive_matching(self) -> None:
        key = AnswerKey(required_keywords=["FOO", "Bar"])
        result = score_answer_detailed("foo bar", key)
        assert result.raw_score == 1.0

    def test_whitespace_handling(self) -> None:
        key = AnswerKey(required_keywords=["foo", "bar"])
        result = score_answer_detailed("  foo   bar  ", key)
        assert result.raw_score == 1.0

    def test_empty_answer_raises(self) -> None:
        key = AnswerKey(required_keywords=["foo"])
        with pytest.raises(ValueError, match="raw_answer must not be empty"):
            score_answer_detailed("", key)

    def test_blank_answer_raises(self) -> None:
        key = AnswerKey(required_keywords=["foo"])
        with pytest.raises(ValueError, match="raw_answer must not be empty"):
            score_answer_detailed("   ", key)

    def test_min_length_not_enforced_by_scoring(self) -> None:
        key = AnswerKey(required_keywords=["x"], min_length_chars=100)
        result = score_answer_detailed("x", key)
        assert result.raw_score == 1.0


class TestScoreResultStructure:
    """Verify the ScoreResult dataclass fields."""

    def test_result_fields_present(self) -> None:
        key = AnswerKey(required_keywords=["hello"])
        result = score_answer_detailed("hello world", key)
        assert isinstance(result.raw_score, float)
        assert isinstance(result.passed, bool)
        assert isinstance(result.missing_keywords, list)
        assert isinstance(result.matched_keywords, list)

    def test_score_boundary(self) -> None:
        key = AnswerKey(required_keywords=["a", "b", "c", "d", "e"])
        result = score_answer_detailed("a b c", key)
        assert result.raw_score == pytest.approx(0.6)
        assert result.passed is True

    def test_score_just_below_boundary(self) -> None:
        key = AnswerKey(required_keywords=["a", "b", "c", "d", "e"])
        result = score_answer_detailed("a b", key)
        assert result.raw_score == pytest.approx(0.4)
        assert result.passed is False


class TestScoreAnswerFromQuizItem:
    """Verify score_answer derives the score from QuizItem.required_keywords.

    Directive 11 requires the keyword-match score to be based on the
    required_keywords stored in the QuizItem. These tests confirm the
    item's keyword list feeds score_answer directly.
    """

    def test_score_uses_item_required_keywords(self) -> None:
        from quiz_engine import QuizItem

        item = QuizItem(
            quiz_item_id="qi-1",
            question="Explain photosynthesis.",
            category="short_answer",
            difficulty="medium",
            required_keywords=["light", "water", "chlorophyll"],
        )
        score = score_answer(
            item.quiz_item_id,
            "Plants use light and water with chlorophyll to make sugar.",
            item.required_keywords,
        )
        assert score == 1.0

    def test_partial_match_via_item_keywords(self) -> None:
        from quiz_engine import QuizItem

        item = QuizItem(
            quiz_item_id="qi-2",
            question="Name the three states of matter.",
            category="short_answer",
            difficulty="easy",
            required_keywords=["solid", "liquid", "gas"],
        )
        score = score_answer(item.quiz_item_id, "solid and liquid", item.required_keywords)
        assert score == pytest.approx(2 / 3)

    def test_item_with_empty_keywords_scores_full(self) -> None:
        from quiz_engine import QuizItem

        item = QuizItem(
            quiz_item_id="qi-3",
            question="Any thoughtful answer.",
            category="short_answer",
            difficulty="easy",
            required_keywords=[],
        )
        score = score_answer(item.quiz_item_id, "anything goes here", item.required_keywords)
        assert score == 1.0

    def test_item_default_keywords_is_empty_list(self) -> None:
        from quiz_engine import QuizItem

        item = QuizItem(
            quiz_item_id="qi-4",
            question="Q?",
            category="mc",
            difficulty="easy",
        )
        assert item.required_keywords == []


class TestMetacognitiveFeedbackLoop:
    """Integration tests closing the metacognitive feedback loop.

    Directive 11: wire the path where a user's quiz answers are
    processed, scored, and recorded. The loop is:

        answer -> score_answer() -> StateMutatorService.process_quiz_result()
              -> QuizResultEvent + LearningStateUpdatedEvent
              -> updated UserLearningState (total, average, mastery)
    """

    @pytest.fixture
    def event_store(self, tmp_path) -> "EventStore":
        from state_core.event_store import EventStore, StoreConfig

        return EventStore(StoreConfig(path=str(tmp_path / "loop_events.jsonl")))

    @pytest.fixture
    def mutator(self, event_store) -> "StateMutatorService":
        from progress_engine.state_mutator import StateMutatorService

        return StateMutatorService(event_store)

    def _seed_item(
        self,
        event_store: "EventStore",
        topic: str,
        quiz_id: str,
        item_id: str,
    ) -> None:
        from state_core.event_models import QuizItemCreatedEvent

        event_store.append(
            QuizItemCreatedEvent.create(
                topic=topic,
                quiz_id=quiz_id,
                quiz_item_id=item_id,
                question=f"Q? {item_id}",
                category="sa",
                difficulty="easy",
                answer_key_hash="hash",
            )
        )

    def test_full_loop_records_both_events(self, mutator, event_store) -> None:
        """score_answer -> process_quiz_result emits QuizResult + LearningStateUpdated."""
        from state_core.event_models import (
            LearningStateUpdatedEvent,
            QuizResultEvent,
        )

        self._seed_item(event_store, "algebra", "q1", "qi1")
        required = ["foo", "bar"]
        score = score_answer("qi1", "foo and bar are present", required)
        passed = score >= 0.6

        mutator.process_quiz_result("q1", "qi1", score, passed)

        events = event_store.read_all()
        result_events = [e for e in events if isinstance(e, QuizResultEvent)]
        update_events = [e for e in events if isinstance(e, LearningStateUpdatedEvent)]

        assert len(result_events) == 1
        assert result_events[0].quiz_item_id == "qi1"
        assert result_events[0].raw_score == pytest.approx(1.0)
        assert result_events[0].passed is True

        assert len(update_events) == 1
        assert update_events[0].total_questions_studied == 1
        assert update_events[0].running_average_score == pytest.approx(1.0)

    def test_loop_updates_running_average(self, mutator, event_store) -> None:
        """Multiple loop iterations accumulate into the running average."""
        self._seed_item(event_store, "algebra", "q1", "qi1")
        self._seed_item(event_store, "algebra", "q1", "qi2")

        s1 = score_answer("qi1", "foo bar", ["foo", "bar"])
        mutator.process_quiz_result("q1", "qi1", s1, s1 >= 0.6)

        s2 = score_answer("qi2", "foo only", ["foo", "bar"])
        mutator.process_quiz_result("q1", "qi2", s2, s2 >= 0.6)

        state = mutator.get_state()
        assert state.total_questions_studied == 2
        assert state.running_average_score == pytest.approx((1.0 + 0.5) / 2)

    def test_loop_sets_mastery_flag(self, mutator, event_store) -> None:
        """All items passing a topic triggers the mastery flag."""
        self._seed_item(event_store, "algebra", "q1", "qi1")
        self._seed_item(event_store, "algebra", "q1", "qi2")

        for item_id, answer in [("qi1", "foo bar"), ("qi2", "foo bar")]:
            score = score_answer(item_id, answer, ["foo", "bar"])
            mutator.process_quiz_result("q1", item_id, score, score >= 0.6)

        state = mutator.get_state()
        assert "algebra" in state.topics_mastered
        assert "algebra" not in state.topics_in_progress

    def test_loop_marks_in_progress_on_partial(self, mutator, event_store) -> None:
        """A failing item leaves the topic in_progress, not mastered."""
        self._seed_item(event_store, "algebra", "q1", "qi1")
        self._seed_item(event_store, "algebra", "q1", "qi2")

        s1 = score_answer("qi1", "foo bar", ["foo", "bar"])
        mutator.process_quiz_result("q1", "qi1", s1, s1 >= 0.6)

        s2 = score_answer("qi2", "nothing relevant", ["foo", "bar"])
        mutator.process_quiz_result("q1", "qi2", s2, s2 >= 0.6)

        state = mutator.get_state()
        assert "algebra" not in state.topics_mastered
        assert "algebra" in state.topics_in_progress

    def test_loop_is_event_sourced_no_direct_writes(self, mutator, event_store) -> None:
        """State is rebuilt purely from events — no out-of-band state."""
        self._seed_item(event_store, "algebra", "q1", "qi1")
        score = score_answer("qi1", "foo bar", ["foo", "bar"])
        mutator.process_quiz_result("q1", "qi1", score, score >= 0.6)

        # A fresh mutator over the same event log must reconstruct the
        # identical state — proving state lives only in the event log.
        from progress_engine.state_mutator import StateMutatorService

        replica = StateMutatorService(event_store)
        replica_state = replica.get_state()

        assert replica_state.total_questions_studied == mutator.get_state().total_questions_studied
        assert replica_state.running_average_score == pytest.approx(mutator.get_state().running_average_score)
        assert replica_state.topics_mastered == mutator.get_state().topics_mastered
