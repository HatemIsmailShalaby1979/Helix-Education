from dataclasses import dataclass, field


@dataclass
class CognitiveNode:
    concept: str
    topic: str
    understanding_level: float
    times_encountered: int
    times_correct: int
    last_practiced: str
    source_materials: list[str] = field(default_factory=list)
    related_concepts: list[str] = field(default_factory=list)
    depth_level_reached: int = 1


@dataclass
class Recommendation:
    recommendation_id: str
    concept: str
    topic: str
    reason: str
    suggested_action: str
    evidence: str
    priority: str
    timestamp: str
    approved: bool = False
    applied: bool = False


@dataclass
class LearningSession:
    session_id: str
    topic: str
    started_at: str
    sections_read: list[str] = field(default_factory=list)
    dig_deeper_requests: int = 0
    quiz_taken: bool = False
    quiz_score: float = 0.0
    quiz_passed: bool = False
    completed_at: str | None = None


@dataclass
class MetacognitiveInsight:
    category: str
    title: str
    description: str
    recommendation: str
    timestamp: str


@dataclass
class KnowledgeMap:
    topics: dict[str, list[CognitiveNode]] = field(default_factory=dict)
    overall_level: str = "beginner"
    topics_studied_count: int = 0
    total_quizzes_taken: int = 0
    average_quiz_score: float = 0.0
    weak_areas: list[str] = field(default_factory=list)
    strong_areas: list[str] = field(default_factory=list)
    topic_progress: dict[str, float] = field(default_factory=dict)
    quiz_mastery: dict[str, float] = field(default_factory=dict)


@dataclass
class JourneyEntry:
    timestamp: str
    entry_type: str
    topic: str
    detail: str
    score: float | None = None
