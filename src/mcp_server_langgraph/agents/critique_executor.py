"""CritiqueExecutor - Multi-pass executor+critic pattern.

Implements the executor+critic agentic loop where:
1. Executor generates an initial response
2. Critic reviews and provides feedback
3. Executor refines based on feedback
4. Repeat until approved or max_rounds reached

OTEL Instrumentation:
- Spans for each execution and critique phase
- Metrics for round counts and latencies
- Structured logging for debugging

Feature Flags:
- FF_ENABLE_CRITIQUE_LOOP: Master toggle
- FF_CRITIQUE_CROSS_VENDOR: Use different vendors for executor/critic
- FF_MAX_CRITIQUE_ROUNDS: Hard limit on rounds
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, cast

from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from langchain_core.messages import BaseMessage

from mcp_server_langgraph.llm.factory import LLMFactory
from mcp_server_langgraph.observability.telemetry import logger

# OTEL instrumentation
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Metrics
critique_rounds_counter = meter.create_counter(
    name="critique_rounds_total",
    description="Total number of critique rounds executed",
    unit="1",
)

critique_latency_histogram = meter.create_histogram(
    name="critique_latency_seconds",
    description="Latency of critique execution loop",
    unit="s",
)

critique_approval_counter = meter.create_counter(
    name="critique_approvals_total",
    description="Total number of critique approvals/rejections",
    unit="1",
)


@dataclass
class CritiqueResult:
    """Result of a critique pass.

    Attributes:
        approved: Whether the response passed critique
        feedback: Textual feedback from critic (None if approved)
        refinement_suggestions: List of specific improvements
        confidence: Critic's confidence in the assessment (0.0-1.0)
    """

    approved: bool
    feedback: str | None
    refinement_suggestions: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "approved": self.approved,
            "feedback": self.feedback,
            "refinement_suggestions": self.refinement_suggestions,
            "confidence": self.confidence,
        }


# Critique prompt template
CRITIQUE_SYSTEM_PROMPT = """You are a quality critic reviewing AI-generated responses.

Your task is to evaluate the response and provide structured feedback.

Evaluation criteria:
1. Accuracy: Is the information correct?
2. Completeness: Does it fully address the question?
3. Clarity: Is it well-organized and easy to understand?
4. Specificity: Does it include concrete examples where appropriate?

Respond with JSON only:
{
  "approved": true/false,
  "feedback": "Brief explanation if rejected, null if approved",
  "suggestions": ["List of specific improvements if rejected"],
  "confidence": 0.0-1.0
}
"""

REFINEMENT_PROMPT_TEMPLATE = """Your previous response was reviewed and needs refinement.

Original response:
{original_response}

Critique feedback:
{feedback}

Suggestions for improvement:
{suggestions}

Please provide an improved response that addresses the feedback.
"""


class CritiqueExecutor:
    """Orchestrates executor+critic multi-pass loop.

    This implements the executor+critic pattern where:
    - A fast executor model generates responses
    - A critic model reviews and provides feedback
    - The executor refines based on feedback
    - Loop continues until approved or max_rounds

    Attributes:
        executor_model: Model name for execution
        critic_model: Model name for critique (None to skip)
        max_rounds: Maximum critique iterations
    """

    def __init__(
        self,
        executor_model: str,
        critic_model: str | None = None,
        max_rounds: int = 3,
    ) -> None:
        """Initialize the CritiqueExecutor.

        Args:
            executor_model: Model identifier for executor
            critic_model: Model identifier for critic (None to skip critique)
            max_rounds: Maximum number of critique rounds (1-3)
        """
        self._executor_model = executor_model
        self._critic_model = critic_model
        self._max_rounds = min(max_rounds, 3)  # Hard cap at 3

        # Lazy-loaded LLM instances
        self._executor: LLMFactory | None = None
        self._critic: LLMFactory | None = None

        logger.debug(
            f"CritiqueExecutor initialized: executor={executor_model}, critic={critic_model}, max_rounds={max_rounds}"
        )

    def _get_executor(self) -> LLMFactory:
        """Get or create executor LLM instance."""
        if self._executor is None:
            self._executor = LLMFactory(model_name=self._executor_model)
        return self._executor

    def _get_critic(self) -> LLMFactory | None:
        """Get or create critic LLM instance."""
        if self._critic_model is None:
            return None
        if self._critic is None:
            self._critic = LLMFactory(model_name=self._critic_model)
        return self._critic

    async def _execute(
        self,
        messages: list[dict[str, Any]],
        refinement_context: str | None = None,
    ) -> str:
        """Execute the primary model.

        Args:
            messages: Conversation messages
            refinement_context: Optional context from previous critique

        Returns:
            Model response content
        """
        with tracer.start_as_current_span("critique_executor.execute") as span:
            span.set_attribute("model", self._executor_model)
            span.set_attribute("is_refinement", refinement_context is not None)

            executor = self._get_executor()

            # Build messages for LLM
            llm_messages: list[dict[str, Any]] = []
            for msg in messages:
                llm_messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

            # Add refinement context if this is a refinement pass
            if refinement_context:
                llm_messages.append({"role": "system", "content": refinement_context})

            try:
                response = await executor.ainvoke(cast(list[BaseMessage | dict[str, Any]], llm_messages))
                raw_content = response.content if hasattr(response, "content") else str(response)
                # Ensure content is always a string
                content: str = str(raw_content) if not isinstance(raw_content, str) else raw_content
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("response_length", len(content))
                return content
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(f"Executor failed: {e}")
                raise

    async def _critique(
        self,
        messages: list[dict[str, Any]],
        response: str,
    ) -> CritiqueResult:
        """Run critique on the response.

        Args:
            messages: Original conversation messages
            response: Response to critique

        Returns:
            CritiqueResult with approval status and feedback
        """
        with tracer.start_as_current_span("critique_executor.critique") as span:
            span.set_attribute("model", self._critic_model or "none")
            span.set_attribute("response_length", len(response))

            critic = self._get_critic()
            if critic is None:
                # No critic - auto-approve
                return CritiqueResult(approved=True, feedback=None, confidence=1.0)

            # Build critique prompt
            original_query = messages[-1].get("content", "") if messages else ""
            critique_messages: list[dict[str, Any]] = [
                {"role": "system", "content": CRITIQUE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Original query: {original_query}\n\nResponse to evaluate:\n{response}",
                },
            ]

            try:
                critique_response = await critic.ainvoke(cast(list[BaseMessage | dict[str, Any]], critique_messages))
                raw_content = critique_response.content if hasattr(critique_response, "content") else str(critique_response)
                # Ensure content is always a string
                content: str = str(raw_content) if not isinstance(raw_content, str) else raw_content

                # Parse JSON response
                result = self._parse_critique_response(content)
                span.set_attribute("approved", result.approved)
                span.set_attribute("confidence", result.confidence)
                span.set_status(Status(StatusCode.OK))

                # Record metric
                critique_approval_counter.add(
                    1,
                    {"approved": str(result.approved), "model": self._critic_model or "none"},
                )

                return result

            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.warning(f"Critique failed, auto-approving: {e}")
                # Graceful fallback: approve on error
                return CritiqueResult(approved=True, feedback=None, confidence=0.5)

    def _parse_critique_response(self, content: str) -> CritiqueResult:
        """Parse critic's JSON response into CritiqueResult.

        Args:
            content: Raw response from critic

        Returns:
            Parsed CritiqueResult
        """
        try:
            # Try to extract JSON from response
            # Handle case where LLM wraps JSON in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            return CritiqueResult(
                approved=data.get("approved", True),
                feedback=data.get("feedback"),
                refinement_suggestions=data.get("suggestions", []),
                confidence=float(data.get("confidence", 0.8)),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse critique response: {e}")
            # Default to approved on parse error
            return CritiqueResult(approved=True, feedback=None, confidence=0.5)

    async def execute_with_critique(
        self,
        messages: list[dict[str, Any]],
        critique_rounds: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Execute with optional critique passes.

        This is the main entry point for the critique loop.
        Yields events as the loop progresses for streaming to clients.

        Args:
            messages: Conversation messages
            critique_rounds: Number of critique rounds (0 = no critique)

        Yields:
            Events describing execution progress:
            - {"type": "executor_response", "round": N, "content": "..."}
            - {"type": "critique", "round": N, "result": CritiqueResult}
            - {"type": "refined_response", "round": N, "content": "..."}
        """
        start_time = time.time()
        effective_rounds = min(critique_rounds, self._max_rounds)

        with tracer.start_as_current_span("critique_executor.execute_with_critique") as span:
            span.set_attribute("executor_model", self._executor_model)
            span.set_attribute("critic_model", self._critic_model or "none")
            span.set_attribute("requested_rounds", critique_rounds)
            span.set_attribute("effective_rounds", effective_rounds)

            logger.info(
                f"Starting critique loop: executor={self._executor_model}, "
                f"critic={self._critic_model}, rounds={effective_rounds}"
            )

            # Round 0: Initial execution
            response = await self._execute(messages)
            yield {
                "type": "executor_response",
                "round": 0,
                "content": response,
                "model": self._executor_model,
            }

            # Skip critique if no critic or 0 rounds
            if self._critic_model is None or effective_rounds == 0:
                span.set_attribute("final_round", 0)
                critique_latency_histogram.record(
                    time.time() - start_time,
                    {"model": self._executor_model, "had_critique": "false"},
                )
                return

            # Rounds 1-N: Critique and refine
            final_round = 0
            for round_num in range(1, effective_rounds + 1):
                # Critique current response
                critique = await self._critique(messages, response)

                yield {
                    "type": "critique",
                    "round": round_num,
                    "result": critique,
                    "model": self._critic_model,
                }

                critique_rounds_counter.add(
                    1,
                    {
                        "executor_model": self._executor_model,
                        "critic_model": self._critic_model or "none",
                        "round": str(round_num),
                    },
                )

                final_round = round_num

                if critique.approved:
                    logger.info(f"Critique approved at round {round_num}")
                    break

                # Refine based on feedback
                refinement_context = REFINEMENT_PROMPT_TEMPLATE.format(
                    original_response=response,
                    feedback=critique.feedback or "No specific feedback",
                    suggestions="\n".join(f"- {s}" for s in critique.refinement_suggestions),
                )

                response = await self._execute(messages, refinement_context)
                yield {
                    "type": "refined_response",
                    "round": round_num,
                    "content": response,
                    "model": self._executor_model,
                }

            span.set_attribute("final_round", final_round)
            span.set_status(Status(StatusCode.OK))

            critique_latency_histogram.record(
                time.time() - start_time,
                {
                    "executor_model": self._executor_model,
                    "critic_model": self._critic_model or "none",
                    "had_critique": "true",
                    "final_round": str(final_round),
                },
            )

            logger.info(f"Critique loop completed: {final_round} rounds, elapsed={time.time() - start_time:.2f}s")
