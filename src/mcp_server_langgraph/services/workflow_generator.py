"""
Workflow Generator Service

LLM-powered service for generating workflow definitions from:
- Text prompts describing desired functionality
- Session message history capturing user interactions

Uses structured output parsing to ensure valid workflow graphs.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

# Import centralized prompts and telemetry (ADR-0089)
from mcp_server_langgraph.core.prompts import (
    WORKFLOW_GENERATOR_SYSTEM_PROMPT as SYSTEM_PROMPT,
    # Telemetry (Phase 7 - ADR-0089)
    record_prompt_usage,
)

if TYPE_CHECKING:
    from mcp_server_langgraph.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


# ==============================================================================
# Exceptions
# ==============================================================================


class WorkflowGenerationError(Exception):
    """Raised when workflow generation fails."""

    pass


# ==============================================================================
# Pydantic Models for Structured LLM Output
# ==============================================================================


class GeneratedNode(BaseModel):
    """A node in a generated workflow."""

    id: str = Field(description="Unique identifier for the node")
    type: str = Field(description="Node type: start, end, llm, tool, router, condition")
    label: str = Field(description="Human-readable label for the node")
    config: dict[str, Any] = Field(default_factory=dict, description="Node configuration")


class GeneratedEdge(BaseModel):
    """An edge connecting nodes in a generated workflow."""

    source: str = Field(description="Source node ID")
    target: str = Field(description="Target node ID")
    condition: str | None = Field(default=None, description="Edge condition (for routers)")


class GeneratedWorkflowOutput(BaseModel):
    """Structured output from LLM for workflow generation."""

    name: str = Field(description="Workflow name")
    description: str = Field(description="Workflow description")
    nodes: list[GeneratedNode] = Field(description="List of workflow nodes")
    edges: list[GeneratedEdge] = Field(description="List of edges connecting nodes")
    reasoning: str = Field(description="Explanation of the workflow design")


class WorkflowGenerationResult(BaseModel):
    """Result of workflow generation including metadata."""

    workflow: GeneratedWorkflowOutput = Field(description="Generated workflow")
    confidence: float = Field(ge=0.0, le=1.0, description="Generation confidence")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")


# ==============================================================================
# System Prompt (Migrated to core/prompts/ per ADR-0089)
# ==============================================================================
# Prompt is now centralized in:
#   src/mcp_server_langgraph/core/prompts/workflow_prompts.py
#
# Imported as:
#   WORKFLOW_GENERATOR_SYSTEM_PROMPT -> SYSTEM_PROMPT (alias for backward compatibility)
# ==============================================================================


# ==============================================================================
# Workflow Generator
# ==============================================================================


class WorkflowGenerator:
    """
    LLM-powered workflow generator.

    Generates workflow definitions from text prompts or session message history.
    Uses structured output parsing to ensure valid workflow graphs.
    """

    def __init__(self, llm: LLMFactory) -> None:
        """
        Initialize the workflow generator.

        Args:
            llm: LLM factory instance for making API calls.
        """
        self._llm = llm

    def get_system_prompt(self) -> str:
        """Get the system prompt for workflow generation."""
        return SYSTEM_PROMPT

    async def generate_from_prompt(self, prompt: str) -> WorkflowGenerationResult:
        """
        Generate a workflow from a text prompt.

        Args:
            prompt: User's description of the desired workflow.

        Returns:
            WorkflowGenerationResult with the generated workflow.

        Raises:
            WorkflowGenerationError: If generation or parsing fails.
        """
        user_message = f"Create a workflow for the following requirement:\n\n{prompt}"

        return await self._generate(user_message)

    async def generate_from_session(self, messages: list[dict[str, Any]]) -> WorkflowGenerationResult:
        """
        Generate a workflow from session message history.

        Analyzes the conversation to understand user intent and creates
        a workflow that captures the discussed functionality.

        SECURITY: Session content is sanitized before LLM exposure to prevent
        prompt injection attacks. See ADR-0089 and Plan Review Consensus.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.

        Returns:
            WorkflowGenerationResult with the generated workflow.

        Raises:
            WorkflowGenerationError: If generation or parsing fails.
        """
        # Import sanitization (Review consensus: sanitize before LLM calls)
        from mcp_server_langgraph.security.prompt_injection import sanitize_content

        # Sanitize each message before processing (prevents injection attacks)
        sanitized_messages = []
        for m in messages:
            content = m.get("content", "")
            role = m.get("role", "user")
            # Sanitize content - replaces detected injection patterns
            sanitized, detection_result = sanitize_content(str(content))
            if detection_result.risk_score > 0.5:
                logger.warning(
                    "High-risk content detected in session message",
                    extra={
                        "role": role,
                        "risk_score": detection_result.risk_score,
                        "patterns": [d["pattern"] for d in detection_result.detections],
                    },
                )
            sanitized_messages.append({"role": role, "content": sanitized})

        # Format sanitized session messages into a summary
        conversation = "\n".join(f"[{m.get('role', 'user').upper()}]: {m.get('content', '')}" for m in sanitized_messages)

        user_message = f"""Analyze this conversation and create a workflow that captures the discussed functionality:

<conversation>
{conversation}
</conversation>

Based on this conversation, design a workflow that implements what the user is trying to accomplish."""

        return await self._generate(user_message)

    async def _generate(self, user_message: str) -> WorkflowGenerationResult:
        """
        Internal method to generate workflow from any user message.

        Args:
            user_message: Formatted user message for the LLM.

        Returns:
            WorkflowGenerationResult with the generated workflow.

        Raises:
            WorkflowGenerationError: If generation or parsing fails.
        """
        messages = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=user_message),
        ]

        # Record prompt usage for telemetry (Phase 7 - ADR-0089)
        record_prompt_usage("workflow_generator", "v1")

        try:
            response = await self._llm.ainvoke(messages)  # type: ignore[arg-type]
            content = response.content

            # Ensure content is a string (handle multimodal response edge case)
            content_str = content if isinstance(content, str) else str(content)

            # Parse JSON response
            workflow_output = self._parse_response(content_str)

            # Calculate confidence based on workflow completeness
            confidence = self._calculate_confidence(workflow_output)

            # Generate improvement suggestions
            suggestions = self._generate_suggestions(workflow_output)

            return WorkflowGenerationResult(
                workflow=workflow_output,
                confidence=confidence,
                suggestions=suggestions,
            )

        except json.JSONDecodeError as e:
            logger.exception("Failed to parse LLM response as JSON")
            raise WorkflowGenerationError(f"LLM returned invalid JSON: {e}") from e
        except Exception as e:
            logger.exception("Workflow generation failed")
            raise WorkflowGenerationError(f"Generation failed: {e}") from e

    def _parse_response(self, content: str) -> GeneratedWorkflowOutput:
        """
        Parse LLM response content into structured output.

        Args:
            content: Raw LLM response content.

        Returns:
            Parsed GeneratedWorkflowOutput.

        Raises:
            json.JSONDecodeError: If content is not valid JSON.
            ValueError: If JSON doesn't match expected structure.
        """
        # Strip any markdown code blocks if present
        content = content.strip()
        if content.startswith("```"):
            # Find the JSON content between code blocks
            lines = content.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block or not content.startswith("```"):
                    json_lines.append(line)
            content = "\n".join(json_lines)

        data = json.loads(content)
        return GeneratedWorkflowOutput(**data)

    def _calculate_confidence(self, workflow: GeneratedWorkflowOutput) -> float:
        """
        Calculate confidence score based on workflow completeness.

        Factors:
        - Has start node
        - Has end node
        - All nodes are connected
        - No orphan nodes
        - Has meaningful description

        Args:
            workflow: The generated workflow.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        score = 0.0
        factors = 0

        # Check for start node
        factors += 1
        if any(n.type == "start" for n in workflow.nodes):
            score += 1.0

        # Check for end node
        factors += 1
        if any(n.type == "end" for n in workflow.nodes):
            score += 1.0

        # Check minimum node count (at least 3 for a useful workflow)
        factors += 1
        if len(workflow.nodes) >= 3:
            score += 1.0

        # Check edges connect nodes
        factors += 1
        node_ids = {n.id for n in workflow.nodes}
        valid_edges = all(e.source in node_ids and e.target in node_ids for e in workflow.edges)
        if valid_edges and len(workflow.edges) > 0:
            score += 1.0

        # Check description exists
        factors += 1
        if len(workflow.description) > 10:
            score += 1.0

        return score / factors if factors > 0 else 0.0

    def _generate_suggestions(self, workflow: GeneratedWorkflowOutput) -> list[str]:
        """
        Generate improvement suggestions for the workflow.

        Args:
            workflow: The generated workflow.

        Returns:
            List of improvement suggestions.
        """
        suggestions = []

        # Check for error handling
        has_error_node = any("error" in n.label.lower() for n in workflow.nodes)
        if not has_error_node:
            suggestions.append("Consider adding error handling nodes")

        # Check for memory/context
        has_memory = any(n.type == "memory" for n in workflow.nodes)
        if not has_memory:
            suggestions.append("Consider adding memory nodes for context persistence")

        # Check for validation
        has_validation = any("validat" in n.label.lower() for n in workflow.nodes)
        if not has_validation:
            suggestions.append("Consider adding input validation")

        # Suggest logging for complex workflows
        if len(workflow.nodes) > 5:
            suggestions.append("Consider adding logging nodes for observability")

        return suggestions


# ==============================================================================
# Factory Function
# ==============================================================================


async def create_workflow_generator() -> WorkflowGenerator:
    """
    Factory function to create a WorkflowGenerator with configured LLM.

    Uses the application's LLM configuration to create the generator.

    Returns:
        Configured WorkflowGenerator instance.
    """
    from mcp_server_langgraph.core.config import settings
    from mcp_server_langgraph.llm.factory import create_llm_from_config

    llm = create_llm_from_config(settings)

    return WorkflowGenerator(llm=llm)


# ==============================================================================
# Conversion Helpers
# ==============================================================================


def workflow_to_api_format(
    result: WorkflowGenerationResult,
) -> dict[str, Any]:
    """
    Convert WorkflowGenerationResult to API response format.

    Args:
        result: The workflow generation result.

    Returns:
        Dict matching the API's GenerateWorkflowResponse format.
    """
    workflow = result.workflow
    now = datetime.now().isoformat()
    workflow_id = str(uuid.uuid4())

    return {
        "workflow": {
            "id": workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "position": {"x": i * 200, "y": 100},  # Simple layout
                    "data": {
                        "label": node.label,
                        **node.config,
                    },
                }
                for i, node in enumerate(workflow.nodes)
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.condition,
                }
                for edge in workflow.edges
            ],
            "created_at": now,
            "updated_at": now,
        },
        "confidence": result.confidence,
        "suggestions": result.suggestions,
    }
