"""Tests for state_core.leveling_engine."""

from state_core.leveling_engine import compute_level
from state_core.projections import TopicState


class TestComputeLevel:
    """Tests for the deterministic leveling rules."""

    def test_beginner_zero_passes(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=0,
            fail_count=0,
            attempts_total=0,
            recent_attempts=[],
        )
        assert compute_level(state) == "beginner"

    def test_beginner_one_pass_but_fails_exceed(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=1,
            fail_count=3,
            attempts_total=4,
            recent_attempts=[False, False, True],
        )
        assert compute_level(state) == "beginner"

    def test_intermediate_one_pass_no_fails(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=1,
            fail_count=0,
            attempts_total=1,
            recent_attempts=[True],
        )
        assert compute_level(state) == "intermediate"

    def test_intermediate_passes_equal_fails(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=2,
            fail_count=2,
            attempts_total=4,
            recent_attempts=[False, True, False, True],
        )
        assert compute_level(state) == "intermediate"

    def test_expert_three_passes_no_recent_fails(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=3,
            fail_count=0,
            attempts_total=3,
            recent_attempts=[True, True, True],
        )
        assert compute_level(state) == "expert"

    def test_expert_many_passes_no_recent_fails(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=10,
            fail_count=0,
            attempts_total=10,
            recent_attempts=[True, True, True],
        )
        assert compute_level(state) == "expert"

    def test_not_expert_recent_fail_in_last_three(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=3,
            fail_count=1,
            attempts_total=4,
            recent_attempts=[True, False, True],
        )
        assert compute_level(state) == "intermediate"

    def test_not_expert_not_enough_passes(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=2,
            fail_count=0,
            attempts_total=2,
            recent_attempts=[True, True],
        )
        assert compute_level(state) == "intermediate"

    def test_zero_attempts_is_beginner(self) -> None:
        state = TopicState(topic="algebra")
        assert compute_level(state) == "beginner"

    def test_expert_with_exactly_three_attempts_all_pass(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=3,
            fail_count=0,
            attempts_total=3,
            recent_attempts=[True, True, True],
        )
        assert compute_level(state) == "expert"

    def test_recent_attempts_empty_means_beginner(self) -> None:
        state = TopicState(
            topic="algebra",
            pass_count=0,
            fail_count=0,
            attempts_total=0,
            recent_attempts=[],
        )
        assert compute_level(state) == "beginner"
