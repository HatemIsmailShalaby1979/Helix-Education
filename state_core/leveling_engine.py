"""Deterministic level promotion/demotion rules for topic mastery.

Leveling rule set (auditable):

- beginner:
    pass_count == 0

- intermediate:
    pass_count >= 1 and fail_count <= pass_count

- expert:
    pass_count >= 3 and fail_count == 0 in the last 3 attempts

No heuristics, ML, or external data are consulted. These rules are
applied exactly as specified and are auditable against the project spec.
"""

from .projections import TopicState


def compute_level(topic_state: TopicState) -> str:
    """Determine the mastery level for a topic based on its computed state.

    Inputs:
        topic_state: A TopicState dataclass with computed attempt statistics.
    Returns:
        One of 'beginner', 'intermediate', or 'expert'.
    """
    ts = topic_state

    # expert: pass_count >= 3 and no failures in the last 3 attempts
    if ts.pass_count >= 3 and len(ts.recent_attempts) >= 3 and all(ts.recent_attempts):
        return "expert"

    # intermediate: pass_count >= 1 and fail_count <= pass_count
    if ts.pass_count >= 1 and ts.fail_count <= ts.pass_count:
        return "intermediate"

    return "beginner"
