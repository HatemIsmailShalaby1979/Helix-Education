"""LLM-based Answer Evaluation Service.

This module replaces the deterministic keyword-based scoring engine with
a semantic LLM-based evaluation. The model evaluates learner answers
against the question, expected concepts, and source material — producing
structured feedback including score, reasoning, detected misconceptions,
and recommended next steps.

This is the foundation of the metacognitive system: the model reflects
on the learner's answer quality and its own evaluation reasoning.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from cognitive_agent.agent_client import CognitiveAgentClient, OllamaAgentClient
from state_core.event_store import SealedAnswerKeyStore
from state_core.scoring_engine import AnswerKey


@dataclass
class LLMEvaluationResult:
    """Structured result from LLM-based answer evaluation.

    Inputs:
        score: Float in [0.0, 1.0] representing answer quality.
        passed: True when score >= 0.6 (configurable threshold).
        reasoning: Natural language explanation of the evaluation.
        misconceptions: List of detected misconceptions or gaps.
        next_steps: Recommended learning actions for the learner.
        confidence: Model's confidence in its own evaluation [0.0, 1.0].
        evaluation_method: Always "llm_semantic" for this evaluator.
        attempt_number: The attempt number for this answer (1-based).
        matched_keywords: Keywords that were matched (for backward compat).
    """

    score: float
    passed: bool
    reasoning: str
    misconceptions: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    confidence: float = 0.8
    evaluation_method: str = "llm_semantic"
    attempt_number: int = 1
    matched_keywords: list[str] = field(default_factory=list)

    # Backward compatibility properties for existing tests and QuizService
    @property
    def raw_score(self) -> float:
        """Backward compatibility: alias for score."""
        return self.score

    @property
    def missing_keywords(self) -> list[str]:
        """Backward compatibility: alias for misconceptions."""
        return self.misconceptions


class LLMEvaluationService:
    """LLM-based semantic answer evaluation service.

    Uses a cognitive agent client (Ollama) to evaluate learner answers
    against the question, expected answer key, and optional source context.
    Produces structured LLMEvaluationResult with semantic understanding.

    This replaces the primitive keyword-match scoring_engine.py with
    genuine semantic evaluation — the model "understands" the answer.
    """

    # System prompt for the evaluator role
    EVALUATOR_SYSTEM_PROMPT = """You are an expert educational evaluator. Your task is to assess a learner's answer to a quiz question.

EVALUATION CRITERIA:
1. ACCURACY: Does the answer correctly address the question?
2. COMPLETENESS: Does it cover the key concepts expected?
3. DEPTH: Does it demonstrate understanding beyond surface-level keywords?
4. MISCONCEPTIONS: Are there any incorrect beliefs or gaps revealed?
5. CLARITY: Is the answer well-structured and coherent?

SCORING GUIDE:
- 1.0: Perfect — accurate, complete, demonstrates deep understanding
- 0.8-0.9: Strong — mostly correct, minor omissions or imprecision
- 0.6-0.7: Adequate — core concept correct, but incomplete or partially confused
- 0.4-0.5: Weak — significant gaps, major misconceptions, or largely incorrect
- 0.0-0.3: Insufficient — fundamentally wrong or non-responsive

OUTPUT FORMAT (JSON only):
{
  "score": 0.0-1.0,
  "passed": true/false,
  "reasoning": "2-3 sentence explanation of the evaluation",
  "misconceptions": ["specific misconception 1", "specific misconception 2"],
  "next_steps": ["actionable recommendation 1", "actionable recommendation 2"],
  "confidence": 0.0-1.0
}

Be precise. Do not inflate scores. Detect genuine understanding vs. keyword stuffing."""

    def __init__(
        self,
        agent_client: CognitiveAgentClient | None = None,
        key_store: SealedAnswerKeyStore | None = None,
        pass_threshold: float = 0.6,
        model_name: str = "lfm2.5:8b",
    ) -> None:
        """Initialize the LLM evaluation service.

        Args:
            agent_client: Cognitive agent client for LLM calls. If None,
                creates OllamaAgentClient with model_name.
            key_store: SealedAnswerKeyStore for retrieving answer keys.
                If None, creates a new instance.
            pass_threshold: Minimum score to pass (default 0.6).
            model_name: Ollama model name (default "lfm2.5:8b").
        """
        self._agent_client = agent_client or OllamaAgentClient(model_name=model_name)
        self._key_store = key_store or SealedAnswerKeyStore()
        self._pass_threshold = pass_threshold

    def evaluate_answer(
        self,
        quiz_item_id: str,
        raw_answer: str,
        question: str = "",
        source_context: str = "",
        attempt_number: int = 1,
    ) -> LLMEvaluationResult:
        """Evaluate a learner's answer using LLM semantic understanding.

        Args:
            quiz_item_id: The quiz item identifier.
            raw_answer: The learner's submitted answer text.
            question: The quiz question text (optional but recommended).
            source_context: Source material context for grounding (optional).
            attempt_number: The attempt number (1-based).

        Returns:
            LLMEvaluationResult with score, reasoning, misconceptions, next_steps.

        Raises:
            ValueError: If raw_answer is empty or answer key not found.
        """
        if not raw_answer or not raw_answer.strip():
            raise ValueError("raw_answer must not be empty")

        # Retrieve the answer key from the sealed store
        answer_key = self._key_store.retrieve(quiz_item_id)
        if answer_key is None:
            raise ValueError(f"No answer key found for quiz item: {quiz_item_id}")

        # Build the evaluation prompt
        prompt = self._build_evaluation_prompt(
            question=question,
            raw_answer=raw_answer,
            answer_key=answer_key,
            source_context=source_context,
            attempt_number=attempt_number,
        )

        # Call the LLM
        try:
            response = self._agent_client.generate_raw(prompt)
            result = self._parse_llm_response(response, attempt_number)
        except Exception as e:
            # Fallback to keyword scoring on LLM failure
            result = self._fallback_keyword_scoring(raw_answer, answer_key, attempt_number)
            result.reasoning = f"LLM evaluation failed ({e}); fell back to keyword scoring: {result.reasoning}"
            result.evaluation_method = "llm_fallback_keyword"
            result.confidence = 0.3

        return result

    def _build_evaluation_prompt(
        self,
        question: str,
        raw_answer: str,
        answer_key: AnswerKey,
        source_context: str,
        attempt_number: int,
    ) -> str:
        """Construct the evaluation prompt for the LLM."""
        required_kw = ", ".join(answer_key.required_keywords) if answer_key.required_keywords else "none specified"
        forbidden_kw = ", ".join(answer_key.forbidden_keywords) if answer_key.forbidden_keywords else "none specified"

        prompt_parts = [
            f"QUESTION: {question}" if question else "QUESTION: (not provided)",
            f"LEARNER'S ANSWER (attempt {attempt_number}): {raw_answer}",
            f"EXPECTED KEY CONCEPTS: {required_kw}",
            f"CONCEPTS THAT INDICATE MISCONCEPTION: {forbidden_kw}",
        ]

        if source_context:
            prompt_parts.append(f"SOURCE CONTEXT:\n{source_context[:3000]}")

        prompt_parts.append(
            "Evaluate the learner's answer against the question and expected concepts. "
            "Output ONLY the JSON object as specified in the system prompt."
        )

        return "\n\n".join(prompt_parts)

    def _parse_llm_response(self, response: str, attempt_number: int) -> LLMEvaluationResult:
        """Parse the LLM's JSON response into LLMEvaluationResult."""
        # Try to extract JSON from the response
        response = response.strip()

        # Find JSON object in response (handles markdown code blocks)
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = response[start : end + 1]
        else:
            json_str = response

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

        # Validate and clamp fields
        score = max(0.0, min(1.0, float(data.get("score", 0.0))))
        passed = bool(data.get("passed", score >= self._pass_threshold))
        reasoning = str(data.get("reasoning", "")).strip()
        misconceptions = [str(m).strip() for m in data.get("misconceptions", []) if str(m).strip()]
        next_steps = [str(n).strip() for n in data.get("next_steps", []) if str(n).strip()]
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.8))))

        # Ensure passed aligns with score
        if passed and score < self._pass_threshold:
            passed = False
        elif not passed and score >= self._pass_threshold:
            passed = True

        return LLMEvaluationResult(
            score=score,
            passed=passed,
            reasoning=reasoning or "No reasoning provided by evaluator.",
            misconceptions=misconceptions,
            next_steps=next_steps,
            confidence=confidence,
            evaluation_method="llm_semantic",
            attempt_number=attempt_number,
        )

    def _fallback_keyword_scoring(
        self,
        raw_answer: str,
        answer_key: AnswerKey,
        attempt_number: int,
    ) -> LLMEvaluationResult:
        """Fallback to keyword-based scoring when LLM fails."""
        from state_core.scoring_engine import ScoreResult, score_answer_detailed

        keyword_result: ScoreResult = score_answer_detailed(raw_answer, answer_key, attempt_number=attempt_number)

        # Convert to LLM result format
        matched = keyword_result.matched_keywords
        missing = keyword_result.missing_keywords

        reasoning_parts = []
        if matched:
            reasoning_parts.append(f"Matched keywords: {', '.join(matched)}.")
        if missing:
            reasoning_parts.append(f"Missing keywords: {', '.join(missing)}.")
        if keyword_result.raw_score < 0.6:
            reasoning_parts.append("Score below passing threshold.")

        return LLMEvaluationResult(
            score=keyword_result.raw_score,
            passed=keyword_result.passed,
            reasoning=" ".join(reasoning_parts) or "Keyword-based fallback evaluation.",
            misconceptions=missing,  # For backward compatibility
            next_steps=["Review the missing key concepts."] if missing else [],
            confidence=0.4,
            evaluation_method="keyword_fallback",
            attempt_number=attempt_number,
            matched_keywords=matched,
        )


def create_llm_evaluation_service(
    model_name: str = "lfm2.5:8b",
    pass_threshold: float = 0.6,
) -> LLMEvaluationService:
    """Factory function to create a configured LLMEvaluationService.

    Args:
        model_name: Ollama model to use for evaluation.
        pass_threshold: Minimum score to pass.

    Returns:
        Configured LLMEvaluationService instance.
    """
    return LLMEvaluationService(
        agent_client=OllamaAgentClient(model_name=model_name),
        pass_threshold=pass_threshold,
    )
