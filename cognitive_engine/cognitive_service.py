try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from uuid import uuid4

from learning_service import LearningService
from state_core.event_models import (
    AnswerScoredEvent,
    JourneyEntryRecordedEvent,
    LearningSessionStartedEvent,
    LessonSectionCommittedEvent,
    QuizItemCreatedEvent,
    RecommendationDecisionEvent,
    RecommendationProposedEvent,
    TopicPassedEvent,
    TopicStartedEvent,
)
from state_core.projections import project_cognitive_state

from .cognitive_models import (
    CognitiveNode,
    JourneyEntry,
    KnowledgeMap,
    LearningSession,
    MetacognitiveInsight,
    Recommendation,
)


class CognitiveService:
    def __init__(self, learning: LearningService) -> None:
        self._learning = learning

    # â”€â”€ Cognitive State Projection â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _project_cognitive_state(self):
        """Get the current cognitive state by replaying all events."""
        return project_cognitive_state(self._learning._event_store.read_all())

    # â”€â”€ Knowledge Map (unchanged - reads from event log directly) â”€â”€â”€

    def build_knowledge_map(self) -> KnowledgeMap:
        events = self._learning._event_store.read_all()

        # Pass 1: Build quiz_item_id -> topic mapping from QuizItemCreatedEvent
        quiz_item_to_topic: dict[str, str] = {}
        for e in events:
            if isinstance(e, QuizItemCreatedEvent):
                quiz_item_to_topic[e.quiz_item_id] = e.topic

        # Pass 2: Build nodes using the mapping
        nodes: dict[str, CognitiveNode] = {}
        topic_scores: dict[str, list[float]] = {}
        quiz_count = 0
        all_scores: list[float] = []
        topic_attempts: dict[str, int] = {}
        topic_passes: dict[str, int] = {}

        for e in events:
            if isinstance(e, TopicStartedEvent):
                if e.topic not in nodes:
                    nodes[e.topic] = CognitiveNode(
                        concept=e.topic,
                        topic=e.topic,
                        understanding_level=0.0,
                        times_encountered=1,
                        times_correct=0,
                        last_practiced=e.timestamp,
                    )
                else:
                    nodes[e.topic].times_encountered += 1
                    nodes[e.topic].last_practiced = e.timestamp

            elif isinstance(e, TopicPassedEvent):
                if e.topic in nodes:
                    nodes[e.topic].understanding_level = 1.0

            elif isinstance(e, AnswerScoredEvent):
                quiz_count += 1
                all_scores.append(e.raw_score)
                topic = quiz_item_to_topic.get(e.quiz_item_id, "unknown")
                # Track topic-level attempts and passes
                topic_attempts[topic] = topic_attempts.get(topic, 0) + 1
                if e.passed:
                    topic_passes[topic] = topic_passes.get(topic, 0) + 1
                if e.quiz_item_id not in nodes:
                    nodes[e.quiz_item_id] = CognitiveNode(
                        concept=e.quiz_item_id,
                        topic=topic,
                        understanding_level=e.raw_score if e.passed else 0.3,
                        times_encountered=1,
                        times_correct=1 if e.passed else 0,
                        last_practiced=e.timestamp,
                    )
                else:
                    nodes[e.quiz_item_id].times_encountered += 1
                    if e.passed:
                        nodes[e.quiz_item_id].times_correct += 1
                    nodes[e.quiz_item_id].understanding_level = (
                        nodes[e.quiz_item_id].times_correct / nodes[e.quiz_item_id].times_encountered
                    )
                    nodes[e.quiz_item_id].last_practiced = e.timestamp

            elif isinstance(e, LessonSectionCommittedEvent):
                if e.topic not in topic_scores:
                    topic_scores[e.topic] = []

        topics_map: dict[str, list[CognitiveNode]] = {}
        for node in nodes.values():
            t = node.topic
            if t not in topics_map:
                topics_map[t] = []
            topics_map[t].append(node)

        avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
        # weak_areas and strong_areas are computed ONLY from quiz-item-level nodes
        # (continuous scale), not from topic-level nodes (binary 0.0/1.0 scale)
        quiz_item_nodes = {k: v for k, v in nodes.items() if k in quiz_item_to_topic}
        weak = [k for k, v in quiz_item_nodes.items() if v.understanding_level < 0.5]
        strong = [k for k, v in quiz_item_nodes.items() if v.understanding_level >= 0.8]

        # topic_progress: fraction of attempts passed for topics with attempts > 0
        topic_progress = {
            topic: topic_passes.get(topic, 0) / topic_attempts[topic]
            for topic in topic_attempts
            if topic_attempts[topic] > 0
        }

        # quiz_mastery: times_correct / times_encountered for quiz items
        quiz_mastery = {
            k: v.times_correct / v.times_encountered for k, v in quiz_item_nodes.items() if v.times_encountered > 0
        }

        level = "expert" if avg >= 0.8 else "intermediate" if avg >= 0.5 else "beginner"

        return KnowledgeMap(
            topics=topics_map,
            overall_level=level,
            topics_studied_count=len(topics_map),
            total_quizzes_taken=quiz_count,
            average_quiz_score=round(avg, 2),
            weak_areas=weak,
            strong_areas=strong,
            topic_progress=topic_progress,
            quiz_mastery=quiz_mastery,
        )

    # â”€â”€ Recommendations (generated from knowledge map) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def get_recommendations(self) -> list[Recommendation]:
        km = self.build_knowledge_map()
        recs: list[Recommendation] = []

        # Get existing proposed recommendations to avoid duplicates
        state = self._project_cognitive_state()
        existing_keys = set()
        for rec in state.recommendations.values():
            existing_keys.add((rec.concept, rec.topic))

        for topic, nodes in km.topics.items():
            for node in nodes:
                if node.understanding_level < 0.5:
                    key = (node.concept, topic)
                    if key in existing_keys:
                        continue
                    rid = str(uuid4())
                    event = RecommendationProposedEvent.create(
                        recommendation_id=rid,
                        concept=node.concept,
                        topic=topic,
                        reason=f"Low understanding ({node.understanding_level:.0%})",
                        suggested_action=f"Review {topic} and retake quiz on {node.concept}",
                        evidence=f"Score: {node.understanding_level:.0%}, Attempts: {node.times_encountered}",
                        priority="high" if node.understanding_level < 0.3 else "medium",
                    )
                    self._learning._event_store.append(event)
                    recs.append(
                        Recommendation(
                            recommendation_id=rid,
                            concept=node.concept,
                            topic=topic,
                            reason=f"Low understanding ({node.understanding_level:.0%})",
                            suggested_action=f"Review {topic} and retake quiz on {node.concept}",
                            evidence=f"Score: {node.understanding_level:.0%}, Attempts: {node.times_encountered}",
                            priority="high" if node.understanding_level < 0.3 else "medium",
                            timestamp=event.timestamp,
                        )
                    )

        if km.weak_areas:
            key = ("general", "all")
            if key not in existing_keys:
                rid = str(uuid4())
                event = RecommendationProposedEvent.create(
                    recommendation_id=rid,
                    concept="general",
                    topic="all",
                    reason=f"{len(km.weak_areas)} weak area(s) identified",
                    suggested_action="Focus on weak concepts and retake relevant quizzes",
                    evidence=f"Weak areas: {', '.join(km.weak_areas[:3])}",
                    priority="medium",
                )
                self._learning._event_store.append(event)
                recs.append(
                    Recommendation(
                        recommendation_id=rid,
                        concept="general",
                        topic="all",
                        reason=f"{len(km.weak_areas)} weak area(s) identified",
                        suggested_action="Focus on weak concepts and retake relevant quizzes",
                        evidence=f"Weak areas: {', '.join(km.weak_areas[:3])}",
                        priority="medium",
                        timestamp=event.timestamp,
                    )
                )

        return recs

    # â”€â”€ Event-sourced Recommendation Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def propose_recommendation(
        self,
        concept: str,
        topic: str,
        reason: str,
        suggested_action: str,
        evidence: str,
        priority: str = "medium",
    ) -> str:
        rid = str(uuid4())
        event = RecommendationProposedEvent.create(
            recommendation_id=rid,
            concept=concept,
            topic=topic,
            reason=reason,
            suggested_action=suggested_action,
            evidence=evidence,
            priority=priority,
        )
        self._learning._event_store.append(event)
        return rid

    def approve_recommendation(self, recommendation_id: str) -> bool:
        # Check if recommendation exists and is not already approved
        state = self._project_cognitive_state()
        rec = state.recommendations.get(recommendation_id)
        if rec is not None and rec.approved:
            # Already approved
            return False

        # Check if it's a pending recommendation (exists in proposed but not decided)
        events = self._learning._event_store.read_all()
        has_proposal = False
        for e in events:
            if isinstance(e, RecommendationProposedEvent) and e.recommendation_id == recommendation_id:
                has_proposal = True
                # Check if already has a decision
                for d in events:
                    if isinstance(d, RecommendationDecisionEvent) and d.recommendation_id == recommendation_id:
                        return False
                break
        if not has_proposal:
            return False

        event = RecommendationDecisionEvent.create(
            recommendation_id=recommendation_id,
            decision="approved",
        )
        self._learning._event_store.append(event)

        # Keep existing behavior: also propose profile delta
        # We need to get the recommendation details for the profile delta
        for e in self._learning._event_store.read_all():
            if isinstance(e, RecommendationProposedEvent) and e.recommendation_id == recommendation_id:
                self._learning.propose_profile_delta(
                    evidence=[e.evidence],
                    proposed_changes={"recommendation_applied": e.suggested_action},
                )
                break

        return True

    def reject_recommendation(self, recommendation_id: str) -> bool:
        # Check if recommendation exists and is not already rejected
        state = self._project_cognitive_state()
        rec = state.recommendations.get(recommendation_id)
        if rec is not None and rec.approved:
            # Already approved, can't reject
            return False

        # Check if it's a pending recommendation (exists in proposed but not decided)
        events = self._learning._event_store.read_all()
        has_proposal = False
        for e in events:
            if isinstance(e, RecommendationProposedEvent) and e.recommendation_id == recommendation_id:
                has_proposal = True
                # Check if already has a decision
                for d in events:
                    if isinstance(d, RecommendationDecisionEvent) and d.recommendation_id == recommendation_id:
                        return False
                break
        if not has_proposal:
            return False

        event = RecommendationDecisionEvent.create(
            recommendation_id=recommendation_id,
            decision="reject",
        )
        self._learning._event_store.append(event)
        return True

    # â”€â”€ Event-sourced Session Management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def start_session(self, topic: str) -> str:
        sid = str(uuid4())
        event = LearningSessionStartedEvent.create(
            session_id=sid,
            topic=topic,
        )
        self._learning._event_store.append(event)

        # Also record journey entry
        journey_event = JourneyEntryRecordedEvent.create(
            session_id=sid,
            entry_type="session_started",
            topic=topic,
            detail="Started learning session",
        )
        self._learning._event_store.append(journey_event)
        return sid

    def record_section_read(self, session_id: str, section_id: str) -> None:
        # Verify session exists
        state = self._project_cognitive_state()
        session = state.sessions.get(session_id)
        if session and section_id not in session.sections_read:
            event = JourneyEntryRecordedEvent.create(
                session_id=session_id,
                entry_type="section_read",
                topic=session.topic,
                detail=f"Read section: {section_id}",
            )
            self._learning._event_store.append(event)

    def record_dig_deeper(self, session_id: str) -> None:
        state = self._project_cognitive_state()
        session = state.sessions.get(session_id)
        if session:
            event = JourneyEntryRecordedEvent.create(
                session_id=session_id,
                entry_type="dig_deeper",
                topic=session.topic,
                detail="Requested deeper dive",
            )
            self._learning._event_store.append(event)

    def record_quiz_result(self, session_id: str, score: float, passed: bool) -> None:
        state = self._project_cognitive_state()
        session = state.sessions.get(session_id)
        if session:
            event = JourneyEntryRecordedEvent.create(
                session_id=session_id,
                entry_type="quiz_completed",
                topic=session.topic,
                detail=f"Score: {score:.0%}, Passed: {passed}",
                score=score,
            )
            self._learning._event_store.append(event)

    def get_session(self, session_id: str) -> LearningSession | None:
        state = self._project_cognitive_state()
        return state.sessions.get(session_id)

    def get_journey(self) -> list[JourneyEntry]:
        state = self._project_cognitive_state()
        return state.journey

    def get_metacognitive_insights(self) -> list[MetacognitiveInsight]:
        insights: list[MetacognitiveInsight] = []
        km = self.build_knowledge_map()
        now = datetime.now(UTC)

        if km.weak_areas:
            insights.append(
                MetacognitiveInsight(
                    category="struggle_area",
                    title="Areas needing focus",
                    description=f"You have {len(km.weak_areas)} concept(s) below 50% understanding.",
                    recommendation="Focus your next study session on these topics and retake their quizzes.",
                    timestamp=now.isoformat(),
                )
            )

        if km.strong_areas:
            insights.append(
                MetacognitiveInsight(
                    category="strength",
                    title="Strong areas identified",
                    description=f"You have {len(km.strong_areas)} concept(s) mastered at 80%+.",
                    recommendation="These concepts can serve as foundation for advanced topics.",
                    timestamp=now.isoformat(),
                )
            )

        if km.total_quizzes_taken > 0:
            if km.average_quiz_score >= 0.7:
                insights.append(
                    MetacognitiveInsight(
                        category="learning_pattern",
                        title="Strong quiz performance",
                        description=f"Average quiz score: {km.average_quiz_score:.0%} across {km.total_quizzes_taken} quizzes.",
                        recommendation="You're ready to tackle more advanced topics.",
                        timestamp=now.isoformat(),
                    )
                )
            else:
                insights.append(
                    MetacognitiveInsight(
                        category="learning_pattern",
                        title="Room for improvement",
                        description=f"Average quiz score: {km.average_quiz_score:.0%} across {km.total_quizzes_taken} quizzes.",
                        recommendation="Review weak areas before moving to new topics.",
                        timestamp=now.isoformat(),
                    )
                )

        # Use projected recommendations for pending count
        state = self._project_cognitive_state()
        rec_count = len([r for r in state.recommendations.values() if not r.approved])
        if rec_count > 0:
            insights.append(
                MetacognitiveInsight(
                    category="recommendation",
                    title="Pending recommendations",
                    description=f"You have {rec_count} recommendation(s) waiting for your review.",
                    recommendation="Review and approve recommendations to update your cognitive profile.",
                    timestamp=now.isoformat(),
                )
            )

        topics_with_depth = sum(1 for s in state.sessions.values() if s.dig_deeper_requests > 0)
        if topics_with_depth > 0:
            insights.append(
                MetacognitiveInsight(
                    category="engagement",
                    title="Active exploration",
                    description=f"You requested deeper dives on {topics_with_depth} topic(s).",
                    recommendation="This shows good curiosity â€” keep exploring complex topics.",
                    timestamp=now.isoformat(),
                )
            )

        return insights

    # â”€â”€ Computed property for backward compatibility â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @property
    def _recommendations(self) -> dict[str, Recommendation]:
        """Thin computed property for backward compatibility with get_recommendations()."""
        return self._project_cognitive_state().recommendations

    def get_pending_recommendations(self) -> list[Recommendation]:
        state = self._project_cognitive_state()
        return [r for r in state.recommendations.values() if not r.approved]

    def get_approved_recommendations(self) -> list[Recommendation]:
        state = self._project_cognitive_state()
        return [r for r in state.recommendations.values() if r.approved]
