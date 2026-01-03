"""
Centralized Prompt Management with XML Structure

Implements Anthropic's prompt engineering best practices:
- XML tags for structural clarity
- Right altitude principle (balanced specificity/flexibility)
- Minimalism with sufficiency
- Clear sectioning (<role>, <task>, <instructions>, <output_format>)

References:
- ADR-0089: Prompt Architecture Centralization
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
"""

from mcp_server_langgraph.core.prompts.ai_ux_prompts import (
    CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT,
    CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT,
    CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT,
    DIAGRAM_ANALYZE_SYSTEM_PROMPT,
    DIAGRAM_TO_CODE_SYSTEM_PROMPT,
    DISCLOSURE_ANALYSIS_SYSTEM_PROMPT,
    EMPTY_STATE_SYSTEM_PROMPT,
    ERROR_ANALYSIS_SYSTEM_PROMPT,
    METRICS_INSIGHTS_SYSTEM_PROMPT,
    NUDGE_RECOMMENDATION_SYSTEM_PROMPT,
    ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT,
    PERSONA_ANALYSIS_SYSTEM_PROMPT,
    SESSION_GROUP_SYSTEM_PROMPT,
    SESSION_SIMILARITY_SYSTEM_PROMPT,
    SESSION_SUMMARIZE_SYSTEM_PROMPT,
    TRACE_ANOMALIES_SYSTEM_PROMPT,
    TRACE_SUMMARIZE_SYSTEM_PROMPT,
)
from mcp_server_langgraph.core.prompts.genui_prompts import (
    GENUI_FORM_SYSTEM_PROMPT,
    GENUI_RENDER_SYSTEM_PROMPT,
    GENUI_WIDGET_SYSTEM_PROMPT,
)
from mcp_server_langgraph.core.prompts.orchestration_router_prompt import (
    ORCHESTRATION_ROUTER_SYSTEM_PROMPT,
    get_orchestration_router_prompt,
)
from mcp_server_langgraph.core.prompts.plan_editor_prompts import (
    PLAN_VALIDATION_SYSTEM_PROMPT,
    TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
    get_plan_validation_prompt,
)
from mcp_server_langgraph.core.prompts.response_prompt import RESPONSE_SYSTEM_PROMPT
from mcp_server_langgraph.core.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from mcp_server_langgraph.core.prompts.schemas import (
    ErrorAnalysisOutput,
    RecoverySuggestion,
    ResponseOutput,
    VerificationOutput,
    WidgetConfigOutput,
    WorkflowEdge,
    WorkflowNode,
    WorkflowOutput,
)
from mcp_server_langgraph.core.prompts.studio_prompt import STUDIO_SYSTEM_PROMPT
from mcp_server_langgraph.core.prompts.telemetry import (
    async_prompt_telemetry_context,
    attach_prompt_to_span,
    get_prompt_metadata,
    prompt_telemetry_context,
    record_prompt_usage,
)
from mcp_server_langgraph.core.prompts.search import (
    PromptIndex,
    PromptSearchResult,
    search_prompts,
)
from mcp_server_langgraph.core.prompts.validation import (
    ValidationResult,
    validate_output,
)
from mcp_server_langgraph.core.prompts.verification_prompt import VERIFICATION_SYSTEM_PROMPT
from mcp_server_langgraph.core.prompts.workflow_prompts import WORKFLOW_GENERATOR_SYSTEM_PROMPT

__all__ = [
    # Core prompts
    "ROUTER_SYSTEM_PROMPT",
    "RESPONSE_SYSTEM_PROMPT",
    "VERIFICATION_SYSTEM_PROMPT",
    "ORCHESTRATION_ROUTER_SYSTEM_PROMPT",
    "STUDIO_SYSTEM_PROMPT",
    # GenUI prompts
    "GENUI_FORM_SYSTEM_PROMPT",
    "GENUI_RENDER_SYSTEM_PROMPT",
    "GENUI_WIDGET_SYSTEM_PROMPT",
    # Workflow prompts
    "WORKFLOW_GENERATOR_SYSTEM_PROMPT",
    # Plan editor prompts
    "PLAN_VALIDATION_SYSTEM_PROMPT",
    "TEMPLATE_SUGGESTION_SYSTEM_PROMPT",
    # AI UX prompts - Error Handling
    "ERROR_ANALYSIS_SYSTEM_PROMPT",
    # AI UX prompts - Core UX
    "EMPTY_STATE_SYSTEM_PROMPT",
    "PERSONA_ANALYSIS_SYSTEM_PROMPT",
    "DISCLOSURE_ANALYSIS_SYSTEM_PROMPT",
    "NUDGE_RECOMMENDATION_SYSTEM_PROMPT",
    "ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT",
    # AI UX prompts - Analytics
    "METRICS_INSIGHTS_SYSTEM_PROMPT",
    # AI UX prompts - Session Intelligence
    "SESSION_SUMMARIZE_SYSTEM_PROMPT",
    "SESSION_GROUP_SYSTEM_PROMPT",
    "SESSION_SIMILARITY_SYSTEM_PROMPT",
    # AI UX prompts - Traces
    "TRACE_SUMMARIZE_SYSTEM_PROMPT",
    "TRACE_ANOMALIES_SYSTEM_PROMPT",
    # AI UX prompts - Canvas/Diagrams
    "CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT",
    "CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT",
    "CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT",
    "DIAGRAM_ANALYZE_SYSTEM_PROMPT",
    "DIAGRAM_TO_CODE_SYSTEM_PROMPT",
    # Pydantic schemas
    "ResponseOutput",
    "VerificationOutput",
    "ErrorAnalysisOutput",
    "RecoverySuggestion",
    "WidgetConfigOutput",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowOutput",
    # Validation
    "ValidationResult",
    "validate_output",
    # Search
    "PromptIndex",
    "PromptSearchResult",
    "search_prompts",
    # Functions
    "get_orchestration_router_prompt",
    "get_plan_validation_prompt",
    "get_prompt",
    "get_prompt_version",
    "list_prompt_versions",
    # Telemetry
    "record_prompt_usage",
    "get_prompt_metadata",
    "attach_prompt_to_span",
    "prompt_telemetry_context",
    "async_prompt_telemetry_context",
]

# Prompt version registry
# Format: {prompt_name: {version: prompt_string}}
_PROMPT_VERSIONS: dict[str, dict[str, str]] = {
    # Core prompts
    "router": {
        "v1": ROUTER_SYSTEM_PROMPT,
        "latest": ROUTER_SYSTEM_PROMPT,
    },
    "response": {
        "v1": RESPONSE_SYSTEM_PROMPT,
        "latest": RESPONSE_SYSTEM_PROMPT,
    },
    "verification": {
        "v1": VERIFICATION_SYSTEM_PROMPT,
        "latest": VERIFICATION_SYSTEM_PROMPT,
    },
    "orchestration_router": {
        "v1": ORCHESTRATION_ROUTER_SYSTEM_PROMPT,
        "latest": ORCHESTRATION_ROUTER_SYSTEM_PROMPT,
    },
    "studio": {
        "v1": STUDIO_SYSTEM_PROMPT,
        "latest": STUDIO_SYSTEM_PROMPT,
    },
    # GenUI prompts
    "genui_widget": {
        "v1": GENUI_WIDGET_SYSTEM_PROMPT,
        "latest": GENUI_WIDGET_SYSTEM_PROMPT,
    },
    "genui_render": {
        "v1": GENUI_RENDER_SYSTEM_PROMPT,
        "latest": GENUI_RENDER_SYSTEM_PROMPT,
    },
    "genui_form": {
        "v1": GENUI_FORM_SYSTEM_PROMPT,
        "latest": GENUI_FORM_SYSTEM_PROMPT,
    },
    # Workflow prompts
    "workflow_generator": {
        "v1": WORKFLOW_GENERATOR_SYSTEM_PROMPT,
        "latest": WORKFLOW_GENERATOR_SYSTEM_PROMPT,
    },
    # Plan editor prompts
    "plan_validation": {
        "v1": PLAN_VALIDATION_SYSTEM_PROMPT,
        "latest": PLAN_VALIDATION_SYSTEM_PROMPT,
    },
    "template_suggestion": {
        "v1": TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
        "latest": TEMPLATE_SUGGESTION_SYSTEM_PROMPT,
    },
    # AI UX prompts
    "error_analysis": {
        "v1": ERROR_ANALYSIS_SYSTEM_PROMPT,
        "latest": ERROR_ANALYSIS_SYSTEM_PROMPT,
    },
    "empty_state": {
        "v1": EMPTY_STATE_SYSTEM_PROMPT,
        "latest": EMPTY_STATE_SYSTEM_PROMPT,
    },
    "persona_analysis": {
        "v1": PERSONA_ANALYSIS_SYSTEM_PROMPT,
        "latest": PERSONA_ANALYSIS_SYSTEM_PROMPT,
    },
    "disclosure_analysis": {
        "v1": DISCLOSURE_ANALYSIS_SYSTEM_PROMPT,
        "latest": DISCLOSURE_ANALYSIS_SYSTEM_PROMPT,
    },
    "nudge_recommendation": {
        "v1": NUDGE_RECOMMENDATION_SYSTEM_PROMPT,
        "latest": NUDGE_RECOMMENDATION_SYSTEM_PROMPT,
    },
    "onboarding_personalization": {
        "v1": ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT,
        "latest": ONBOARDING_PERSONALIZATION_SYSTEM_PROMPT,
    },
    "metrics_insights": {
        "v1": METRICS_INSIGHTS_SYSTEM_PROMPT,
        "latest": METRICS_INSIGHTS_SYSTEM_PROMPT,
    },
    "session_summarize": {
        "v1": SESSION_SUMMARIZE_SYSTEM_PROMPT,
        "latest": SESSION_SUMMARIZE_SYSTEM_PROMPT,
    },
    "session_group": {
        "v1": SESSION_GROUP_SYSTEM_PROMPT,
        "latest": SESSION_GROUP_SYSTEM_PROMPT,
    },
    "session_similarity": {
        "v1": SESSION_SIMILARITY_SYSTEM_PROMPT,
        "latest": SESSION_SIMILARITY_SYSTEM_PROMPT,
    },
    "trace_summarize": {
        "v1": TRACE_SUMMARIZE_SYSTEM_PROMPT,
        "latest": TRACE_SUMMARIZE_SYSTEM_PROMPT,
    },
    "trace_anomalies": {
        "v1": TRACE_ANOMALIES_SYSTEM_PROMPT,
        "latest": TRACE_ANOMALIES_SYSTEM_PROMPT,
    },
    "canvas_artifact_type": {
        "v1": CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT,
        "latest": CANVAS_ARTIFACT_TYPE_SYSTEM_PROMPT,
    },
    "canvas_code_analysis": {
        "v1": CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT,
        "latest": CANVAS_CODE_ANALYSIS_SYSTEM_PROMPT,
    },
    "canvas_diff_explain": {
        "v1": CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT,
        "latest": CANVAS_DIFF_EXPLAIN_SYSTEM_PROMPT,
    },
    "diagram_analyze": {
        "v1": DIAGRAM_ANALYZE_SYSTEM_PROMPT,
        "latest": DIAGRAM_ANALYZE_SYSTEM_PROMPT,
    },
    "diagram_to_code": {
        "v1": DIAGRAM_TO_CODE_SYSTEM_PROMPT,
        "latest": DIAGRAM_TO_CODE_SYSTEM_PROMPT,
    },
}

# Current version metadata
_PROMPT_METADATA: dict[str, dict[str, str]] = {
    "router": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "response": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "verification": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "orchestration_router": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "studio": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "genui_widget": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "genui_render": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "genui_form": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "workflow_generator": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "plan_validation": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "template_suggestion": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "error_analysis": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "empty_state": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "persona_analysis": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "disclosure_analysis": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "nudge_recommendation": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "onboarding_personalization": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "metrics_insights": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "session_summarize": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "session_group": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "session_similarity": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "trace_summarize": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "trace_anomalies": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "canvas_artifact_type": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "canvas_code_analysis": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "canvas_diff_explain": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "diagram_analyze": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
    "diagram_to_code": {"current_version": "v1", "created": "2025-01-15", "last_updated": "2025-01-15"},
}


def get_prompt(prompt_name: str, version: str | None = None) -> str:
    """
    Get a prompt by name with optional versioning.

    Args:
        prompt_name: Name of the prompt (e.g., "router", "response", "error_analysis")
        version: Optional version string (default: "latest")

    Returns:
        Prompt string

    Raises:
        ValueError: If prompt name or version is unknown

    Examples:
        >>> get_prompt("router")  # Gets latest version
        >>> get_prompt("router", "v1")  # Gets specific version
        >>> get_prompt("error_analysis", "latest")  # Explicitly latest
    """
    if prompt_name not in _PROMPT_VERSIONS:
        available = list(_PROMPT_VERSIONS.keys())
        msg = f"Unknown prompt: {prompt_name}. Available: {available}"
        raise ValueError(msg)

    version = version or "latest"
    prompt_versions = _PROMPT_VERSIONS[prompt_name]

    if version not in prompt_versions:
        available_versions = list(prompt_versions.keys())
        msg = f"Unknown version '{version}' for prompt '{prompt_name}'. Available: {available_versions}"
        raise ValueError(msg)

    return prompt_versions[version]


def get_prompt_version(prompt_name: str) -> str:
    """
    Get current version number for a prompt.

    Args:
        prompt_name: Name of the prompt

    Returns:
        Version string (e.g., "v1")

    Raises:
        ValueError: If prompt name is unknown
    """
    if prompt_name not in _PROMPT_METADATA:
        msg = f"Unknown prompt: {prompt_name}"
        raise ValueError(msg)

    return _PROMPT_METADATA[prompt_name]["current_version"]


def list_prompt_versions(prompt_name: str) -> list[str]:
    """
    List all available versions for a prompt.

    Args:
        prompt_name: Name of the prompt

    Returns:
        List of version strings

    Raises:
        ValueError: If prompt name is unknown
    """
    if prompt_name not in _PROMPT_VERSIONS:
        msg = f"Unknown prompt: {prompt_name}"
        raise ValueError(msg)

    return list(_PROMPT_VERSIONS[prompt_name].keys())
