"""
GenUI Orchestrator

Orchestrator for generating dynamic UI components using LLM intelligence.
Follows BaseOrchestrator pattern for parallel task execution.

Task Types:
- generate_widget: Create chart/table/text widgets from prompts
- render_data: Transform raw data into widget format
- execute_form: Handle form submission with AI validation

Usage:
    from mcp_server_langgraph.agents.genui_orchestrator import (
        GenUIOrchestrator,
        GenUITask,
    )

    orchestrator = GenUIOrchestrator(llm_factory=llm)
    results = await orchestrator.execute([
        GenUITask(task_type="generate_widget", data={"prompt": "Show sales"})
    ])
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from mcp_server_langgraph.agents.base_orchestrator import (
    BaseOrchestrator,
    BaseResult,
    BaseTask,
)
from mcp_server_langgraph.core.feature_flags import feature_flags

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# =============================================================================
# System Prompts
# =============================================================================

GENUI_WIDGET_SYSTEM_PROMPT = """You are an AI assistant that generates dynamic UI widget configurations.

Based on the user's prompt and context data, generate an appropriate widget configuration.

Widget types:
- chart: For numerical data visualization (bar charts, line charts)
- table: For structured data display (rows and columns)
- text: For summaries, explanations, or single values

Respond with a JSON object containing:
{
    "widget_type": "chart" | "table" | "text",
    "title": "Widget Title",
    "data": {
        // For chart:
        "labels": ["Label1", "Label2", ...],
        "values": [num1, num2, ...]
        // For table:
        "columns": ["Col1", "Col2", ...],
        "rows": [["val1", "val2"], ...]
        // For text:
        "content": "The text content"
    },
    "confidence": 0.0-1.0
}"""

GENUI_RENDER_SYSTEM_PROMPT = """You are an AI assistant that transforms raw data into UI widget format.

Given raw data and a format hint, determine the best widget representation.

Respond with a JSON object containing:
{
    "widget_type": "chart" | "table" | "text",
    "title": "Appropriate Title",
    "data": { ... },
    "confidence": 0.0-1.0
}"""

GENUI_FORM_SYSTEM_PROMPT = """You are an AI assistant that processes form submissions.

Validate the form data and determine the next action.

Respond with a JSON object containing:
{
    "action": "submit" | "validate" | "error",
    "validated_data": { ... },
    "next_step": "confirmation" | "review" | "error_display",
    "errors": [...] (if any),
    "confidence": 0.0-1.0
}"""


# =============================================================================
# Task and Result Types
# =============================================================================


@dataclass
class GenUITask(BaseTask):
    """Task for GenUI orchestrator.

    Attributes:
        task_type: One of "generate_widget", "render_data", "execute_form"
        data: Task-specific data payload
    """

    task_type: str = "generate_widget"
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenUIResult(BaseResult):
    """Result from GenUI orchestrator.

    Attributes:
        task_type: Type of task that produced this result
        success: Whether the task succeeded
        result: Widget/action configuration if successful
        error: Error message if failed
    """

    task_type: str = "generate_widget"
    success: bool = True
    result: dict[str, Any] | None = None
    error: str | None = None


# =============================================================================
# Orchestrator Implementation
# =============================================================================


class GenUIOrchestrator(BaseOrchestrator[GenUITask, GenUIResult]):
    """Orchestrator for generating dynamic UI components.

    Uses LLM to intelligently generate widget configurations based on
    user prompts and context data.
    """

    def __init__(
        self,
        llm_factory: Any | None = None,
        enable_metrics: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize GenUI orchestrator.

        Args:
            llm_factory: LLM factory for AI-powered generation
            enable_metrics: Whether to record metrics
            **kwargs: Additional arguments for BaseOrchestrator
        """
        super().__init__(enable_metrics=enable_metrics, **kwargs)
        self.llm_factory = llm_factory

    @property
    def feature_flag_name(self) -> str:
        """Feature flag controlling this orchestrator."""
        return "enable_genui"

    @property
    def is_enabled(self) -> bool:
        """Check if GenUI is enabled."""
        return getattr(feature_flags, "enable_genui", False)

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response.

        Args:
            content: Raw LLM response content

        Returns:
            Parsed JSON dictionary or empty dict on error
        """
        try:
            # Handle markdown code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            return json.loads(content)  # type: ignore[no-any-return]
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {}

    def _get_fallback_widget(self, task_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Generate fallback widget when LLM is unavailable.

        Args:
            task_type: Type of task
            data: Task data

        Returns:
            Fallback widget configuration
        """
        if task_type == "generate_widget":
            return {
                "widget_type": "text",
                "title": "Generated Content",
                "data": {"content": f"Widget based on: {data.get('prompt', 'No prompt')}"},
                "confidence": 0.5,
            }
        elif task_type == "render_data":
            return {
                "widget_type": "text",
                "title": "Data Summary",
                "data": {"content": f"Data: {json.dumps(data.get('raw_data', {}))[:200]}"},
                "confidence": 0.5,
            }
        elif task_type == "execute_form":
            return {
                "action": "submit",
                "validated_data": data.get("form_data", {}),
                "next_step": "confirmation",
                "confidence": 0.5,
            }
        else:
            return {
                "widget_type": "text",
                "title": "Unknown Task",
                "data": {"content": f"Unknown task type: {task_type}"},
                "confidence": 0.3,
            }

    async def _execute_task(self, task: GenUITask) -> GenUIResult:
        """Execute a single GenUI task.

        Args:
            task: The task to execute

        Returns:
            GenUIResult with widget configuration
        """
        fallback = self._get_fallback_widget(task.task_type, task.data)

        # Check if GenUI is enabled and LLM is available
        if not self.is_enabled or self.llm_factory is None:
            return GenUIResult(
                task_type=task.task_type,
                success=True,
                result=fallback,
            )

        try:
            # Select system prompt based on task type
            if task.task_type == "generate_widget":
                system_prompt = GENUI_WIDGET_SYSTEM_PROMPT
                user_prompt = f"""Generate a widget for this request:

Prompt: {task.data.get("prompt", "")}
Context: {json.dumps(task.data.get("context", {}), indent=2)}"""

            elif task.task_type == "render_data":
                system_prompt = GENUI_RENDER_SYSTEM_PROMPT
                user_prompt = f"""Transform this data into a widget:

Raw Data: {json.dumps(task.data.get("raw_data", {}), indent=2)}
Format Hint: {task.data.get("format_hint", "auto")}"""

            elif task.task_type == "execute_form":
                system_prompt = GENUI_FORM_SYSTEM_PROMPT
                user_prompt = f"""Process this form submission:

Form ID: {task.data.get("form_id", "unknown")}
Form Data: {json.dumps(task.data.get("form_data", {}), indent=2)}"""

            else:
                return GenUIResult(
                    task_type=task.task_type,
                    success=True,
                    result=fallback,
                )

            # Call LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = await self.llm_factory.ainvoke(messages)
            result_content = response.content if hasattr(response, "content") else str(response)
            parsed = self._parse_json_response(result_content)

            if not parsed:
                return GenUIResult(
                    task_type=task.task_type,
                    success=True,
                    result=fallback,
                )

            return GenUIResult(
                task_type=task.task_type,
                success=True,
                result=parsed,
            )

        except Exception as e:
            logger.warning(f"GenUI task failed: {e}, using fallback")
            return GenUIResult(
                task_type=task.task_type,
                success=True,  # Graceful degradation
                result=fallback,
                error=str(e),
            )

    def synthesize(self, results: list[GenUIResult]) -> dict[str, Any]:
        """Synthesize multiple GenUI results into a layout.

        Args:
            results: List of GenUI results

        Returns:
            Combined layout with all widgets
        """
        widgets = []
        errors = []

        for i, result in enumerate(results):
            if result.success and result.result:
                widget = result.result.copy()
                widget["id"] = f"widget-{i}"
                widgets.append(widget)
            elif result.error:
                errors.append(result.error)

        # Determine layout based on widget count
        if len(widgets) == 1:
            layout = "single"
        elif len(widgets) == 2:
            layout = "side-by-side"
        elif len(widgets) <= 4:
            layout = "grid-2x2"
        else:
            layout = "scrollable"

        return {
            "widgets": widgets,
            "layout": layout,
            "total_count": len(widgets),
            "errors": errors if errors else None,
        }
