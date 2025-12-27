#!/usr/bin/env python3
"""
Feature Flag Catalog Generator

Extracts feature flags from the FeatureFlags class and generates a
Markdown catalog for documentation.

Usage:
    python scripts/validation/generate_feature_flag_catalog.py [--output PATH]

The script:
1. Introspects the FeatureFlags Pydantic settings class
2. Extracts field metadata (name, type, default, description, constraints)
3. Categorizes flags by domain (Pydantic AI, LLM, Authorization, etc.)
4. Generates a comprehensive Markdown catalog
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from pydantic.fields import FieldInfo


@dataclass
class FeatureFlagInfo:
    """Information about a single feature flag."""

    name: str
    type: str
    default: Any
    description: str
    env_var: str
    min_value: float | int | None = None
    max_value: float | int | None = None
    category: str = "Uncategorized"

    @property
    def default_str(self) -> str:
        """Get default value as string for display."""
        if isinstance(self.default, bool):
            return str(self.default)
        if isinstance(self.default, (list, tuple)):
            return str(list(self.default))
        return str(self.default)

    @property
    def type_str(self) -> str:
        """Get type as string for display."""
        return self.type

    @property
    def constraints_str(self) -> str:
        """Get constraints as string for display."""
        constraints = []
        if self.min_value is not None:
            constraints.append(f"min: {self.min_value}")
        if self.max_value is not None:
            constraints.append(f"max: {self.max_value}")
        return ", ".join(constraints) if constraints else "-"


# Category mapping based on flag name prefixes and patterns
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "Pydantic AI": ["pydantic_ai"],
    "LLM": [
        "llm_",
        "enable_llm_",
        "enable_streaming_responses",
        "enable_llm_fallback",
        "enable_streaming_suggestions",
        "enable_llm_suggestions",
        "enable_llm_hooks",
    ],
    "Authorization": ["openfga", "keycloak", "enable_keycloak", "enable_openfga"],
    "Observability": [
        "langsmith",
        "trace_",
        "enable_detailed_logging",
        "enable_langsmith",
        "enable_trace_",
    ],
    "Performance": [
        "cache_",
        "enable_response_caching",
        "enable_request_batching",
        "max_batch_size",
    ],
    "Agent Behavior": [
        "max_agent_",
        "enable_agent_memory",
        "memory_max_",
        "enable_multi_agent_",
        "enable_tool_reflection",
        "max_subagents",
    ],
    "Security": [
        "rate_limit",
        "enable_rate_limiting",
        "enable_input_validation",
        "max_input_length",
        "enable_pii_",
        "enable_encrypted_",
    ],
    "UI Features": [
        "enable_workflows_feature",
        "enable_sessions_feature",
        "enable_cost_dashboard",
        "enable_observability_ui",
        "enable_code_export",
        "enable_ai_suggestions",
        "enable_notification_",
        "enable_interactive_",
        "enable_url_content_",
        "enable_slash_commands",
        "enable_style_presets",
        "enable_user_preferences_",
        "enable_session_export",
        "enable_project_context",
        "enable_onboarding_",
        "enable_guided_tour",
        "enable_sus_survey",
        "enable_command_palette",
        "enable_keyboard_shortcuts",
        "enable_theme_customization",
        "enable_confirmation_dialogs",
        "enable_personalized_suggestions",
        "suggestion_",
        "enable_suggestion_",
        "max_conversation_history_",
        "enable_conversation_history_",
        "enable_mcp_websocket",
        "enable_distributed_rate_limiting",
    ],
    "Canvas": [
        "studio_canvas_shell",
        "canvas_editable",
        "canvas_agents",
        "canvas_ai_palette",
        "canvas_compliance",
        "canvas_help",
    ],
    "DevTools": ["devtools_"],
    "Claude Agent SDK": ["enable_sdk_", "sdk_"],
    "Multi-Framework Parity": [
        "enable_handoff_pattern",
        "enable_mcp_client",
        "enable_session_hooks",
        "enable_loop_agent",
        "enable_session_fork",
    ],
    "MCP Extensions": [
        "enable_orchestration_mcp_",
        "enable_hooks_mcp_",
        "enable_bash_tool",
        "enable_computer_use",
    ],
    "Anthropic Best Practices": [
        "enable_tool_examples",
        "enable_think_tool",
        "enable_defer_loading",
        "enable_skills_",
        "enable_programmatic_tools",
    ],
    "Cost Tracking": [
        "enable_cost_tracking",
        "orchestration_cost_",
        "session_cost_",
        "cost_alert_",
    ],
    "Thinking Budget": ["enable_thinking_budget", "default_thinking_level"],
    "Context Engineering": [
        "enable_dynamic_context_",
        "context_split_",
        "enable_short_tool_",
        "enable_lost_in_middle_",
        "enable_context_ranking",
        "enable_semantic_deduplication",
        "context_deduplication_",
        "enable_agentic_memory",
        "enable_model_aware_",
        "context_compaction_",
        "enable_model_capabilities_",
    ],
    "Orchestrator": [
        "enable_orchestrator_",
        "orchestrator_timeout_",
        "orchestrator_max_concurrent",
        "orchestrator_circuit_",
        "enable_multi_agent_orchestration",
        "enable_orchestrated_",
    ],
    "Studio AI": [
        "enable_studio_ai",
        "enable_session_intelligence",
        "enable_conversation_intelligence",
        "enable_canvas_intelligence",
        "enable_diagram_intelligence",
        "enable_trace_intelligence",
        "enable_hitl_ai",
        "enable_genui",
    ],
    "AI UX": [
        "enable_ai_disclosure",
        "enable_ai_empty_states",
        "enable_ai_nudges",
        "enable_ai_error_recovery",
        "enable_ai_onboarding",
        "enable_ai_metrics_insights",
        "enable_ai_persona_analysis",
        "enable_ai_ux",
        "enable_batch_composite_",
        "ai_ux_",
    ],
    "Frontend Cache": ["enable_frontend_redis_l2_", "frontend_redis_l2_"],
    "Agent HITL": [
        "enable_agent_hitl",
        "agent_hitl_",
        "enable_ai_explanations",
    ],
    "WebSocket": [
        "enable_websocket_",
        "websocket_heartbeat_",
        "websocket_idle_",
        "websocket_rate_",
    ],
    "Experimental": [
        "enable_experimental_features",
    ],
}


def extract_feature_flags() -> list[FeatureFlagInfo]:
    """
    Extract all feature flags from the FeatureFlags class.

    Returns:
        List of FeatureFlagInfo objects with metadata for each flag.
    """
    from mcp_server_langgraph.core.feature_flags import FeatureFlags

    flags: list[FeatureFlagInfo] = []

    # Get model fields from Pydantic model
    for field_name, field_info in FeatureFlags.model_fields.items():
        # Skip internal/private fields
        if field_name.startswith("_"):
            continue

        # Skip model_config which is not a feature flag
        if field_name == "model_config":
            continue

        # Extract field metadata
        field_type = _get_field_type(field_info)
        default_value = _get_default_value(field_info)
        description = field_info.description or ""
        min_value, max_value = _get_constraints(field_info)

        # Generate environment variable name (FF_ prefix, uppercase)
        env_var = f"FF_{field_name.upper()}"

        flag = FeatureFlagInfo(
            name=field_name,
            type=field_type,
            default=default_value,
            description=description,
            env_var=env_var,
            min_value=min_value,
            max_value=max_value,
        )

        flags.append(flag)

    return flags


def _get_field_type(field_info: FieldInfo) -> str:
    """Extract type string from field info."""
    annotation = field_info.annotation
    if annotation is None:
        return "Any"

    # Handle common types
    if annotation is bool:
        return "bool"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is str:
        return "str"

    # Handle generic types
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        args = getattr(annotation, "__args__", ())
        if args:
            return f"list[{args[0].__name__}]"
        return "list"

    # Fallback to string representation
    return str(annotation).replace("typing.", "")


def _get_default_value(field_info: FieldInfo) -> Any:
    """Extract default value from field info."""
    if field_info.default is not None:
        return field_info.default
    if field_info.default_factory is not None:
        try:
            return field_info.default_factory()
        except Exception:
            return None
    return None


def _get_constraints(field_info: FieldInfo) -> tuple[float | int | None, float | int | None]:
    """Extract ge/le constraints from field metadata."""
    min_value = None
    max_value = None

    # Check metadata for constraints
    if field_info.metadata:
        for meta in field_info.metadata:
            if hasattr(meta, "ge"):
                min_value = meta.ge
            if hasattr(meta, "le"):
                max_value = meta.le
            if hasattr(meta, "gt"):
                min_value = meta.gt
            if hasattr(meta, "lt"):
                max_value = meta.lt

    return min_value, max_value


def categorize_flags(flags: list[FeatureFlagInfo]) -> dict[str, list[FeatureFlagInfo]]:
    """
    Categorize feature flags by domain.

    Args:
        flags: List of feature flags to categorize.

    Returns:
        Dictionary mapping category names to lists of flags.
    """
    categories: dict[str, list[FeatureFlagInfo]] = {}

    for flag in flags:
        category = _determine_category(flag.name)
        flag.category = category

        if category not in categories:
            categories[category] = []
        categories[category].append(flag)

    # Sort categories by name
    return dict(sorted(categories.items()))


def _determine_category(flag_name: str) -> str:
    """Determine the category for a flag based on its name."""
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in flag_name or flag_name.startswith(pattern):
                return category

    return "Uncategorized"


def generate_markdown_catalog(flags: list[FeatureFlagInfo]) -> str:
    """
    Generate a Markdown catalog of feature flags.

    Args:
        flags: List of feature flags to document.

    Returns:
        Markdown string containing the catalog.
    """
    categories = categorize_flags(flags)

    lines: list[str] = []

    # Header
    lines.append("# Feature Flag Catalog")
    lines.append("")
    lines.append(f"**Total Flags**: {len(flags)}")
    lines.append(f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")
    lines.append("This catalog is auto-generated from `src/mcp_server_langgraph/core/feature_flags.py`.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("")
    for i, category in enumerate(categories.keys(), 1):
        anchor = category.lower().replace(" ", "-").replace("/", "")
        lines.append(f"{i}. [{category}](#{anchor}) ({len(categories[category])} flags)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Category sections
    for category, cat_flags in categories.items():
        lines.append(f"## {category}")
        lines.append("")
        lines.append(f"*{len(cat_flags)} flags in this category*")
        lines.append("")

        # Table header
        lines.append("| Flag | Type | Default | Environment Variable | Description |")
        lines.append("|------|------|---------|---------------------|-------------|")

        # Table rows
        for flag in sorted(cat_flags, key=lambda f: f.name):
            default_display = _format_default(flag.default)
            desc_short = _truncate(flag.description, 80)
            env_var = f"`{flag.env_var}`"

            lines.append(f"| `{flag.name}` | {flag.type_str} | {default_display} | {env_var} | {desc_short} |")

        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("## Usage")
    lines.append("")
    lines.append("Feature flags can be configured via environment variables with the `FF_` prefix:")
    lines.append("")
    lines.append("```bash")
    lines.append("# Enable a feature")
    lines.append("export FF_ENABLE_LANGSMITH=true")
    lines.append("")
    lines.append("# Set a numeric value")
    lines.append("export FF_LLM_TIMEOUT_SECONDS=120")
    lines.append("")
    lines.append("# Configure in .env file")
    lines.append("FF_ENABLE_OPENFGA=true")
    lines.append("FF_OPENFGA_STRICT_MODE=true")
    lines.append("```")
    lines.append("")
    lines.append("## Programmatic Access")
    lines.append("")
    lines.append("```python")
    lines.append("from mcp_server_langgraph.core.feature_flags import get_feature_flags")
    lines.append("")
    lines.append("flags = get_feature_flags()")
    lines.append("")
    lines.append("# Check if feature is enabled")
    lines.append("if flags.enable_langsmith:")
    lines.append('    print("LangSmith tracing enabled")')
    lines.append("")
    lines.append("# Require feature (raises FeatureDisabledError if disabled)")
    lines.append('flags.require_feature("enable_langsmith", "LangSmith Tracing")')
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def _format_default(value: Any) -> str:
    """Format a default value for display in table."""
    if isinstance(value, bool):
        return f"`{value}`"
    if isinstance(value, str):
        return f'`"{value}"`'
    if isinstance(value, (list, tuple)):
        return f"`{list(value)}`"
    return f"`{value}`"


def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Generate feature flag catalog from FeatureFlags class")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("docs-internal/FEATURE_FLAG_CATALOG.md"),
        help="Output path for the markdown catalog",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Print to stdout instead of writing to file",
    )

    args = parser.parse_args()

    # Extract flags
    flags = extract_feature_flags()
    print(f"Extracted {len(flags)} feature flags")

    # Generate catalog
    catalog = generate_markdown_catalog(flags)

    if args.dry_run:
        print(catalog)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(catalog)
        print(f"Wrote catalog to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
