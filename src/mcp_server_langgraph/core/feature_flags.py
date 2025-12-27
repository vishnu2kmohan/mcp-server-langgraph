"""
Feature Flag Management System

Enables gradual rollouts, A/B testing, and safe feature deployment.
All flags are configurable via environment variables for different environments.
"""

import functools
import os
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

P = ParamSpec("P")
R = TypeVar("R")


class FeatureFlags(BaseSettings):
    """
    Feature flags for controlling system behavior.

    All flags can be overridden via environment variables with FF_ prefix.
    Example: FF_ENABLE_PYDANTIC_AI_ROUTING=false

    Category Structure (12 logical groups):
    ========================================

    1. AUTHENTICATION & AUTHORIZATION
       - enable_keycloak, enable_openfga, openfga_strict_mode, etc.

    2. AGENT ORCHESTRATION
       - enable_multi_agent_orchestration, multi_agent_strategy, max_subagents
       - enable_sdk_*, enable_handoff_pattern, enable_loop_agent

    3. AI FEATURES
       - Studio AI: enable_studio_ai + granular intelligence flags (deep analysis)
       - AI UX: enable_ai_ux + disclosure/nudges/error recovery (UX polish)
       - AI Suggestions: enable_ai_suggestions, suggestion_strategy

    4. CACHE & PERFORMANCE
       - default_cache_ttl_seconds + feature-specific TTLs
       - default_rate_limit_per_minute + feature-specific limits
       - enable_response_caching, enable_request_batching

    5. CONTEXT ENGINEERING
       - enable_context_ranking, enable_semantic_deduplication
       - enable_model_aware_compaction, context_split_threshold

    6. DEVELOPER TOOLS
       - devtools_panel, devtools_ai_insights, devtools_network_tab

    7. OBSERVABILITY
       - enable_langsmith, enable_detailed_logging, enable_trace_sampling

    8. SAFETY & SECURITY
       - enable_rate_limiting, enable_input_validation, enable_pii_tokenization
       - enable_agent_hitl, agent_hitl_confidence_threshold

    9. SKILLS ECOSYSTEM
       - enable_skills_system, enable_skills_marketplace

    10. UI COMPONENTS
        - Canvas: studio_canvas_shell, canvas_editable, canvas_ai_palette
        - Chat UX: enable_slash_commands, enable_style_presets
        - Sessions: enable_sessions_feature, enable_session_export

    11. WEBSOCKET INFRASTRUCTURE
        - enable_websocket_new_base, enable_mcp_websocket
        - websocket_heartbeat_interval_seconds, websocket_idle_timeout_seconds

    12. EXPERIMENTAL (default=False, requires opt-in)
        - enable_experimental_features (master switch)
        - enable_agentic_memory, enable_computer_use, enable_bash_tool

    Helper Methods:
    ===============
    - get_rate_limit(feature) - Get effective rate limit for a feature
    - get_cache_ttl(feature) - Get effective cache TTL for a feature
    - effective_suggestion_strategy - Get suggestion strategy (llm/heuristic/hybrid)
    - get_ui_features_for_role(role) - Get UI features available for a user role
    """

    # =========================================================================
    # CATEGORY 2: AI FEATURES - Pydantic AI Integration
    # =========================================================================
    # Pydantic AI Features
    enable_pydantic_ai_routing: bool = Field(
        default=True,
        description="Use Pydantic AI for type-safe routing decisions with confidence scoring",
    )

    enable_pydantic_ai_responses: bool = Field(
        default=True,
        description="Use Pydantic AI for structured response generation with validation",
    )

    pydantic_ai_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to trust Pydantic AI routing (0.0-1.0)",
    )

    # LLM Features
    enable_llm_fallback: bool = Field(
        default=True,
        description="Enable automatic fallback to alternative models on failure",
    )

    enable_streaming_responses: bool = Field(
        default=True,
        description="Enable streaming responses for real-time output",
    )

    llm_timeout_seconds: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Maximum time to wait for LLM responses (10-300 seconds)",
    )

    # Authorization Features
    enable_openfga: bool = Field(
        default=True,
        description="Enable OpenFGA for fine-grained authorization checks",
    )

    openfga_strict_mode: bool = Field(
        default=False,
        description="Fail-closed on OpenFGA errors (strict) vs fail-open (permissive)",
    )

    openfga_cache_ttl_seconds: int = Field(
        default=60,
        ge=0,
        le=3600,
        description="Cache authorization check results for N seconds (0=disabled)",
    )

    # Keycloak Features
    enable_keycloak: bool = Field(
        default=True,
        description="Enable Keycloak integration for authentication",
    )

    enable_token_refresh: bool = Field(
        default=True,
        description="Enable automatic token refresh for Keycloak tokens",
    )

    keycloak_role_sync: bool = Field(
        default=True,
        description="Sync Keycloak roles/groups to OpenFGA on authentication",
    )

    openfga_sync_on_login: bool = Field(
        default=True,
        description="Synchronize user roles to OpenFGA on every login",
    )

    # Observability Features
    enable_langsmith: bool = Field(
        default=False,
        description="Enable LangSmith tracing for LLM-specific observability",
    )

    enable_detailed_logging: bool = Field(
        default=True,
        description="Include detailed context in logs (may increase log volume)",
    )

    enable_trace_sampling: bool = Field(
        default=False,
        description="Sample traces rather than capturing all (reduces overhead)",
    )

    trace_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Percentage of traces to sample when sampling enabled (0.0-1.0)",
    )

    # Performance Optimizations
    enable_response_caching: bool = Field(
        default=False,
        description="Cache LLM responses for identical inputs (experimental)",
    )

    # =========================================================================
    # Cache TTL Configuration (Unified)
    # =========================================================================
    # Default cache TTL inherited by all feature-specific caches unless overridden.
    # Feature-specific overrides: suggestion_cache_ttl_seconds,
    # ai_ux_redis_cache_ttl_seconds, frontend_redis_l2_cache_ttl_seconds, openfga_cache_ttl_seconds
    default_cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=86400,
        description="Default cache TTL for all features (60s-24h). Feature-specific TTLs override this value when set.",
    )

    cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=86400,
        description="How long to cache LLM responses (60s-24h)",
    )

    enable_request_batching: bool = Field(
        default=True,
        description="Batch multiple requests to reduce LLM API calls",
    )

    max_batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of requests to batch together",
    )

    # Agent Behavior
    max_agent_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum iterations for agent loops before stopping",
    )

    enable_agent_memory: bool = Field(
        default=True,
        description="Enable conversation memory/checkpointing for stateful agents",
    )

    memory_max_messages: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Maximum messages to retain in conversation history",
    )

    # Security Features
    enable_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting to prevent abuse",
    )

    # =========================================================================
    # Rate Limiting Configuration (Unified)
    # =========================================================================
    # Default rate limit inherited by all feature-specific limits unless overridden.
    # Feature-specific overrides: suggestion_rate_limit_per_minute,
    # frontend_redis_l2_rate_limit_per_minute, websocket_rate_limit_per_minute
    default_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Default rate limit for all features (requests per minute per user). "
        "Feature-specific limits override this value when set.",
    )

    rate_limit_requests_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum requests per minute per user (API global rate limit)",
    )

    enable_input_validation: bool = Field(
        default=True,
        description="Validate and sanitize all user inputs",
    )

    max_input_length: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum input length in characters",
    )

    # UI Features (Unified Studio/BFF)
    # =========================================================================
    # Canvas Feature Flags (StudioShell is now default at /studio)
    # =========================================================================
    studio_canvas_shell: bool = Field(
        default=True,
        description="Phase 1: Enable Studio Canvas shell at /studio (StudioShellLayout)",
    )

    canvas_editable: bool = Field(
        default=False,
        description="Phase 2: Enable editable artifacts in Canvas panel",
    )

    canvas_agents: bool = Field(
        default=False,
        description="Phase 4: Enable background agent panel",
    )

    canvas_ai_palette: bool = Field(
        default=False,
        description="Phase 4: Enable AI fallback in command palette",
    )

    canvas_compliance: bool = Field(
        default=False,
        description="Phase 5: Enable compliance dashboards (GDPR, HIPAA, SOC2, FedRAMP)",
    )

    canvas_help: bool = Field(
        default=False,
        description="Phase 6: Enable in-app help pane with contextual assistance",
    )

    # =========================================================================
    # DevTools Feature Flags (Chrome DevTools-like debugging panel)
    # =========================================================================
    devtools_panel: bool = Field(
        default=True,
        description="Enable DevTools panel for debugging (master toggle)",
    )

    devtools_ai_insights: bool = Field(
        default=False,
        description="Enable AI Insights tab in DevTools for anomaly detection and suggestions",
    )

    devtools_ai_layout: bool = Field(
        default=False,
        description="Enable AI-powered layout suggestions in DevTools based on context",
    )

    devtools_network_tab: bool = Field(
        default=True,
        description="Enable Network tab in DevTools for API/WebSocket monitoring",
    )

    # =========================================================================
    # Core UI Features
    # =========================================================================
    enable_workflows_feature: bool = Field(
        default=True,
        description="Enable workflow builder UI feature",
    )

    enable_sessions_feature: bool = Field(
        default=True,
        description="Enable chat sessions UI feature",
    )

    enable_cost_dashboard: bool = Field(
        default=True,
        description="Enable cost dashboard for admins",
    )

    enable_cost_dashboard_users: bool = Field(
        default=False,
        description="Enable cost dashboard for regular users (not just admins)",
    )

    enable_observability_ui: bool = Field(
        default=True,
        description="Enable observability/trace UI feature",
    )

    enable_code_export: bool = Field(
        default=True,
        description="Enable code export feature in workflow builder",
    )

    enable_ai_suggestions: bool = Field(
        default=True,
        description="Enable AI-powered suggestions in UI (master toggle for all suggestion features)",
    )

    suggestion_strategy: str = Field(
        default="llm",
        description="Suggestion generation strategy: 'llm' (AI-powered, best quality), "
        "'heuristic' (rule-based, lower cost), or 'hybrid' (adaptive based on complexity). "
        "Replaces deprecated enable_llm_suggestions flag.",
    )

    # DEPRECATED: Use suggestion_strategy instead
    # Kept for backward compatibility - will be removed in future version
    enable_llm_suggestions: bool = Field(
        default=True,
        description="[DEPRECATED] Use suggestion_strategy='llm' instead. "
        "When False, uses heuristics only. Reduces cost but may lower suggestion quality.",
    )

    enable_streaming_suggestions: bool = Field(
        default=True,
        description="Enable streaming suggestions via SSE for real-time response",
    )

    enable_ai_suggestions_websocket: bool = Field(
        default=True,
        description="Enable AI suggestions WebSocket endpoint (/api/v1/ws/ai/suggestions). Requires enable_ai_suggestions=true.",
    )

    enable_personalized_suggestions: bool = Field(
        default=True,
        description="Enable personalized suggestions based on conversation history",
    )

    suggestion_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum suggestion requests per minute per user (1-1000)",
    )

    enable_distributed_rate_limiting: bool = Field(
        default=False,
        description="Use Redis for distributed rate limiting (required for multi-instance deployments)",
    )

    suggestion_cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Time-to-live for suggestion cache entries (60s-1h)",
    )

    enable_suggestion_quality_tracking: bool = Field(
        default=True,
        description="Track suggestion click rates and quality metrics for improvement",
    )

    enable_suggestion_prewarm: bool = Field(
        default=False,
        description="Pre-compute suggestions for common topics (experimental, increases startup time)",
    )

    max_conversation_history_messages: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum conversation history messages to include for personalization (1-20)",
    )

    enable_conversation_history_validation: bool = Field(
        default=True,
        description="Validate and sanitize conversation history to prevent prompt injection",
    )

    enable_notification_preferences: bool = Field(
        default=True,
        description="Enable notification preferences UI for users to customize notification types",
    )

    enable_mcp_websocket: bool = Field(
        default=True,
        description="Enable MCP 2025-11-25 WebSocket protocol for real-time bidirectional communication",
    )

    enable_interactive_artifacts: bool = Field(
        default=True,
        description="Enable interactive artifact rendering in chat (Sandpack for JSX/TSX/MDX, Mermaid diagrams, charts)",
    )

    enable_url_content_fetch: bool = Field(
        default=True,
        description="Enable #URL content fetch feature for including web content in chat context (OpenWebUI-style)",
    )

    enable_slash_commands: bool = Field(
        default=True,
        description="Enable slash commands (/) for quick actions and workflow templates in chat input",
    )

    enable_style_presets: bool = Field(
        default=True,
        description="Enable response style presets selector in chat (concise, detailed, etc.)",
    )

    # UX Enhancement Features (Priority 1-3 from competitive analysis)
    enable_user_preferences_sync: bool = Field(
        default=True,
        description="Enable syncing user preferences (theme, accessibility, model defaults) to backend",
    )

    enable_session_export: bool = Field(
        default=True,
        description="Enable exporting chat sessions to Markdown, JSON, or HTML formats",
    )

    enable_project_context: bool = Field(
        default=True,
        description="Enable .studio/context.md project context files (AGENTS.md equivalent)",
    )

    enable_onboarding_wizard: bool = Field(
        default=True,
        description="Enable onboarding wizard for first-time users",
    )

    enable_guided_tour: bool = Field(
        default=True,
        description="Enable guided tour after onboarding for feature discovery",
    )

    enable_sus_survey: bool = Field(
        default=True,
        description="Enable System Usability Scale (SUS) survey after 3 sessions or 7 days",
    )

    enable_command_palette: bool = Field(
        default=True,
        description="Enable command palette (Cmd+K) for quick actions",
    )

    enable_keyboard_shortcuts: bool = Field(
        default=True,
        description="Enable customizable keyboard shortcuts",
    )

    enable_theme_customization: bool = Field(
        default=True,
        description="Enable theme customization (light/dark/system)",
    )

    enable_confirmation_dialogs: bool = Field(
        default=True,
        description="Enable confirmation dialogs for destructive actions",
    )

    # Experimental Features
    enable_experimental_features: bool = Field(
        default=False,
        description="Master switch for all experimental features",
    )

    # NOTE: enable_multi_agent_collaboration was removed (Sprint Block 5 consolidation).
    # Use enable_multi_agent_orchestration + multi_agent_strategy instead.
    # Migration: All code referencing collaboration should use orchestration flag.

    enable_tool_reflection: bool = Field(
        default=True,
        description="Enable agents to reflect on tool usage effectiveness",
    )

    # =========================================================================
    # Claude Agent SDK Patterns (SDK-Inspired Features)
    # See ADR-0077 for architecture decisions and implementation details.
    #
    # Production-Ready (default=True):
    #   - sdk_hooks: Tool lifecycle interception for audit, validation, security
    #   - sdk_interrupt: Graceful cancellation of long-running operations
    #   - sdk_structured_output: JSON Schema validation for type-safe responses
    #
    # Experimental (default=False, requires explicit opt-in):
    #   - sdk_file_checkpointing: File change rollback (adds I/O overhead)
    #   - sdk_can_use_tool: Dynamic permission checks (supplements OpenFGA)
    #   - sdk_agent_definition: Declarative subagent creation pattern
    # =========================================================================
    enable_sdk_hooks: bool = Field(
        default=True,
        description="Enable Claude Agent SDK hook system (PreToolUse, PostToolUse, UserPromptSubmit, Stop). Production-ready.",
    )

    enable_sdk_interrupt: bool = Field(
        default=True,
        description="Enable Claude Agent SDK interrupt capability for graceful operation cancellation. Production-ready.",
    )

    enable_sdk_file_checkpointing: bool = Field(
        default=False,
        description="Enable Claude Agent SDK file checkpointing for rollback capability. Adds I/O overhead - enable for file-heavy operations.",
    )

    enable_sdk_structured_output: bool = Field(
        default=True,
        description="Enable Claude Agent SDK structured output validation via JSON Schema. Production-ready.",
    )

    enable_sdk_can_use_tool: bool = Field(
        default=False,
        description="Enable Claude Agent SDK can_use_tool callback for dynamic tool permission checks. Supplements OpenFGA for real-time decisions.",
    )

    enable_sdk_agent_definition: bool = Field(
        default=True,
        description="Enable Claude Agent SDK AgentDefinition pattern for declarative subagent creation. Simplifies multi-agent orchestration.",
    )

    # =========================================================================
    # Multi-Framework Parity Features (ADR-0079 to ADR-0082)
    # =========================================================================
    # These features implement capabilities from Claude Agent SDK, Google ADK,
    # and OpenAI Agents SDK while maintaining LLM-agnostic design.
    # =========================================================================
    enable_llm_hooks: bool = Field(
        default=True,
        description="Enable LLM-level hooks (BEFORE_MODEL, AFTER_MODEL) for request/response interception. Enables caching, filtering, and prompt modification.",
    )

    enable_session_hooks: bool = Field(
        default=True,
        description="Enable session lifecycle hooks (SESSION_START, SESSION_END) for initialization and cleanup.",
    )

    enable_handoff_pattern: bool = Field(
        default=True,
        description="Enable Handoff pattern (ADR-0081) for explicit agent-to-agent control transfer with context filtering. Production-ready.",
    )

    enable_mcp_client: bool = Field(
        default=True,
        description="Enable MCP client capabilities (ADR-0082) to consume tools from external MCP servers. Production-ready.",
    )

    enable_litellm_otel: bool = Field(
        default=True,
        description="Enable LiteLLM native OTEL callback for enhanced LLM tracing. Provides gen_ai.client.token.cost histogram and automatic span creation for all LLM calls.",
    )

    # =========================================================================
    # MCP Extensions (Plan Section 10.4-10.5)
    # =========================================================================
    enable_orchestration_mcp_resources: bool = Field(
        default=False,
        description="Expose multi-agent orchestration as MCP resources (orchestrator://tasks, artifacts, subagents). Experimental.",
    )

    enable_orchestration_mcp_tools: bool = Field(
        default=False,
        description="Expose orchestration operations as MCP tools (decompose, execute, status, cancel). Experimental.",
    )

    enable_hooks_mcp_extension: bool = Field(
        default=False,
        description="Enable hooks MCP tool for listing registered hooks and available events. Experimental.",
    )

    enable_bash_tool: bool = Field(
        default=False,
        description="Enable enhanced bash tool for sandboxed command execution beyond Python.",
    )

    enable_computer_use: bool = Field(
        default=False,
        description="Enable computer use tools for screen capture, input simulation, and browser automation.",
    )

    enable_loop_agent: bool = Field(
        default=False,
        description="Enable LoopAgent pattern (Google ADK parity) for iterative task execution with termination conditions.",
    )

    enable_session_fork: bool = Field(
        default=False,
        description="Enable session fork capability (Claude Agent SDK parity) for branching conversation history.",
    )

    enable_encrypted_sessions: bool = Field(
        default=False,
        description="Enable at-rest encryption for session data. Provides GDPR/HIPAA compliance for sensitive session storage.",
    )

    # =========================================================================
    # Anthropic Best Practices Features (ADR-0072)
    # =========================================================================
    enable_tool_examples: bool = Field(
        default=True,
        description="Enable input_examples for tools to improve accuracy (72% -> 90% improvement)",
    )

    enable_think_tool: bool = Field(
        default=True,
        description="Enable think tool for structured reasoning during tool chains (54% improvement)",
    )

    enable_defer_loading: bool = Field(
        default=False,
        description="Enable defer_loading for tools to reduce initial token usage (experimental)",
    )

    enable_skills_system: bool = Field(
        default=True,
        description="Enable SKILL.md-based skills system for agent capabilities. "
        "Provides structured skill definitions with YAML frontmatter, sandboxed execution, "
        "and progressive discovery. Set FF_ENABLE_SKILLS_SYSTEM=false to disable.",
    )

    enable_skills_marketplace: bool = Field(
        default=True,
        description="Enable skills marketplace integration with Anthropic skills repo. "
        "Fetches skills from https://github.com/anthropics/skills and custom marketplaces. "
        "Set FF_ENABLE_SKILLS_MARKETPLACE=false to disable.",
    )

    enable_pii_tokenization: bool = Field(
        default=True,
        description="Enable PII tokenization layer for GDPR/HIPAA compliance. "
        "Automatically detects and tokenizes PII (email, phone, SSN, credit card, names, addresses) "
        "before LLM exposure. REQUIRED for healthcare and EU deployments. "
        "Set FF_ENABLE_PII_TOKENIZATION=false only for non-compliant environments.",
    )

    enable_programmatic_tools: bool = Field(
        default=False,
        description="Enable programmatic tool calling from sandbox code (experimental). "
        "Allows sandboxed Python code to invoke MCP tools via call_tool() API. "
        "Set FF_ENABLE_PROGRAMMATIC_TOOLS=true to enable.",
    )

    enable_multi_agent_orchestration: bool = Field(
        default=True,
        description="Enable orchestrator-worker pattern for parallel task execution. "
        "Supports up to max_subagents parallel workers with artifact-based synthesis. "
        "Includes three-tier model selection and cross-vendor verification. "
        "Set FF_ENABLE_MULTI_AGENT_ORCHESTRATION=false to disable.",
    )

    multi_agent_strategy: str = Field(
        default="orchestrator",
        description="Multi-agent coordination strategy: 'orchestrator' (hierarchical with coordinator), "
        "'peer' (decentralized collaboration), or 'hybrid' (adaptive based on task complexity). "
        "Replaces deprecated enable_multi_agent_collaboration flag.",
    )

    max_subagents: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of parallel subagents in orchestrator (1-50)",
    )

    # Cost Tracking Flags (Phase 5)
    enable_cost_tracking: bool = Field(
        default=True,
        description="Enable token and cost budget tracking for orchestrations",
    )

    orchestration_cost_limit: float = Field(
        default=0.50,
        ge=0.01,
        le=100.0,
        description="Maximum cost in dollars per single orchestration (0.01-100.0)",
    )

    session_cost_limit: float = Field(
        default=5.00,
        ge=0.10,
        le=1000.0,
        description="Maximum cost in dollars per session (0.10-1000.0)",
    )

    cost_alert_thresholds: list[float] = Field(
        default=[0.5, 0.75, 0.9],
        description="Percentage thresholds for cost alerts (e.g., [0.5, 0.75, 0.9])",
    )

    # Thinking Budget Flags (Phase 6)
    enable_thinking_budget: bool = Field(
        default=True,
        description="Enable thinking budget management for extended reasoning",
    )

    default_thinking_level: str = Field(
        default="medium",
        description="Default thinking level (low, medium, high, ultra)",
    )

    # Dynamic Context Splitting Flags (Phase 7)
    enable_dynamic_context_splitting: bool = Field(
        default=True,
        description="Enable dynamic context splitting for large tasks",
    )

    context_split_threshold: float = Field(
        default=0.8,
        ge=0.5,
        le=0.95,
        description="Percentage of effective limit that triggers splitting (0.5-0.95)",
    )

    # Context Engineering Optimizations (Phase 3)
    enable_short_tool_descriptions: bool = Field(
        default=True,
        description="Use short-form tool descriptions to reduce token usage (~40% savings)",
    )

    enable_lost_in_middle_mitigation: bool = Field(
        default=True,
        description="Reorder context to place key info at start/end for better attention",
    )

    enable_context_ranking: bool = Field(
        default=True,
        description="Rank contexts by relevance before loading into context window",
    )

    enable_semantic_deduplication: bool = Field(
        default=True,
        description="Deduplicate semantically similar contexts to reduce redundancy",
    )

    context_deduplication_threshold: float = Field(
        default=0.92,
        ge=0.5,
        le=0.99,
        description="Similarity threshold for context deduplication (0.5-0.99)",
    )

    enable_agentic_memory: bool = Field(
        default=False,
        description="Enable structured note-taking (NOTES.md) and checkpoints for agentic memory (experimental)",
    )

    # Model-Aware Context Compaction (Phase 2 Orchestrator Enhancement)
    enable_model_aware_compaction: bool = Field(
        default=True,
        description="Enable model-aware context compaction using model registry context limits",
    )

    context_compaction_threshold_percentage: float = Field(
        default=0.5,
        ge=0.1,
        le=0.9,
        description="Percentage of model's effective context limit that triggers compaction (0.1-0.9)",
    )

    # Model Capabilities Routing (Phase 1 Orchestrator Enhancement)
    enable_model_capabilities_routing: bool = Field(
        default=True,
        description="Enable capability-aware model routing via model registry",
    )

    # =========================================================================
    # Orchestrator Resilience (Phase 10)
    # =========================================================================
    enable_orchestrator_resilience: bool = Field(
        default=True,
        description="Enable resilience patterns (circuit breaker, timeout, bulkhead) for orchestrator",
    )

    orchestrator_timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=600,
        description="Maximum time in seconds for orchestrator execution (30-600)",
    )

    orchestrator_max_concurrent: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent orchestrations allowed (bulkhead limit) (1-20)",
    )

    orchestrator_circuit_breaker_threshold: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of failures before circuit breaker opens (1-10)",
    )

    # =========================================================================
    # AI UX Service Migration (Phase 11)
    # =========================================================================
    enable_orchestrated_ai_ux: bool = Field(
        default=False,
        description="Enable orchestrated AI UX composite analysis for parallel execution (gradual rollout)",
    )

    # =========================================================================
    # Alert Recommendations Migration (Phase 12)
    # =========================================================================
    enable_orchestrated_alert_analysis: bool = Field(
        default=False,
        description="Enable orchestrated alert analysis for parallel correlation and root cause (gradual rollout)",
    )

    # =========================================================================
    # Studio AI Orchestration (StudioShell AI Enhancement)
    # =========================================================================
    # DISTINCTION: Studio AI vs AI UX
    #
    # Studio AI (enable_studio_ai, default=False):
    #   - Deep AI intelligence features for content analysis
    #   - Session/conversation/canvas/diagram/trace intelligence
    #   - Requires LLM calls for each analysis
    #   - Higher cost, gradual rollout
    #   - Use case: "Summarize this session", "Detect anomalies in traces"
    #
    # AI UX (enable_ai_ux, default=True):
    #   - Lightweight UX enhancements using AI
    #   - Disclosure, nudges, error recovery, onboarding
    #   - Uses cached/batched LLM calls, lower cost
    #   - Production-ready, enabled by default
    #   - Use case: "Show personalized next steps", "Suggest recovery from error"
    #
    # Both can be enabled independently. AI UX is for user experience polish,
    # while Studio AI is for deep content analysis and intelligence.
    # =========================================================================
    enable_studio_ai: bool = Field(
        default=False,
        description="Enable unified Studio AI orchestration for deep content intelligence (gradual rollout). "
        "See AI UX (enable_ai_ux) for lightweight UX enhancements.",
    )

    # -------------------------------------------------------------------------
    # Granular Intelligence Flags (require enable_studio_ai master flag)
    # -------------------------------------------------------------------------
    enable_session_intelligence: bool = Field(
        default=False,
        description="Enable session intelligence: summarize, group, similarity analysis",
    )

    enable_conversation_intelligence: bool = Field(
        default=False,
        description="Enable conversation intelligence: intent detection, context optimization, goal tracking",
    )

    enable_canvas_intelligence: bool = Field(
        default=False,
        description="Enable canvas intelligence: artifact type suggestions, code analysis, diff explanation",
    )

    enable_diagram_intelligence: bool = Field(
        default=False,
        description="Enable diagram intelligence: analyze diagrams, convert to code",
    )

    enable_trace_intelligence: bool = Field(
        default=False,
        description="Enable trace intelligence: summarize agent traces, detect anomalies",
    )

    enable_hitl_ai: bool = Field(
        default=False,
        description="Enable HITL AI: risk assessment, decision history for agent approvals",
    )

    enable_genui: bool = Field(
        default=False,
        description="Enable generative UI: dynamic component rendering based on AI suggestions",
    )

    # =========================================================================
    # AI UX Features (Phase 6 AI-Native Integration)
    # =========================================================================
    # Lightweight UX enhancements using AI. Production-ready, enabled by default.
    # See Studio AI section above for deep content intelligence features.
    # =========================================================================
    enable_ai_disclosure: bool = Field(
        default=True,
        description="Enable AI-powered progressive disclosure analysis for adaptive UI complexity",
    )

    enable_ai_empty_states: bool = Field(
        default=True,
        description="Enable AI-powered empty state suggestions with contextual CTAs",
    )

    enable_ai_nudges: bool = Field(
        default=True,
        description="Enable AI-powered smart nudge recommendations based on user behavior",
    )

    enable_ai_error_recovery: bool = Field(
        default=True,
        description="Enable AI-powered error classification and recovery suggestions",
    )

    enable_ai_onboarding: bool = Field(
        default=True,
        description="Enable AI-powered onboarding personalization based on detected intent",
    )

    enable_ai_metrics_insights: bool = Field(
        default=True,
        description="Enable AI-generated HEART metrics insights and predictions",
    )

    enable_ai_persona_analysis: bool = Field(
        default=True,
        description="Enable AI-powered persona behavior analysis and mismatch detection",
    )

    # AI UX Advanced Features
    enable_ai_ux: bool = Field(
        default=True,
        description="Master switch for all AI UX features (disclosure, nudges, error recovery, etc.). "
        "Independent from enable_studio_ai which controls deep content intelligence.",
    )

    enable_ai_ux_parallel_graph: bool = Field(
        default=True,
        description="Enable parallel graph execution using LangGraph Send API for faster analysis",
    )

    enable_ai_ux_streaming: bool = Field(
        default=True,
        description="Enable streaming responses for composite analysis via SSE",
    )

    enable_ai_ux_websocket: bool = Field(
        default=True,
        description="Enable WebSocket for real-time AI suggestions and live updates",
    )

    enable_ai_ux_redis_cache: bool = Field(
        default=False,
        description="Enable Redis caching for LLM responses (reduces cost, requires Redis)",
    )

    ai_ux_redis_cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="TTL for Redis-cached AI UX responses (60s-1h)",
    )

    # =========================================================================
    # Frontend Redis L2 Cache (useTieredCache hook)
    # =========================================================================
    enable_frontend_redis_l2_cache: bool = Field(
        default=False,
        description="Enable Redis L2 caching for frontend useTieredCache hook (cross-tab sharing)",
    )

    frontend_redis_l2_cache_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="TTL for frontend Redis L2 cache entries (60s-1h)",
    )

    enable_frontend_redis_l2_rate_limiting: bool = Field(
        default=True,
        description="Enable rate limiting for frontend Redis L2 cache API (prevents cache flooding)",
    )

    frontend_redis_l2_rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum frontend cache API requests per minute per user (1-1000)",
    )

    enable_batch_composite_analysis: bool = Field(
        default=True,
        description="Enable batch composite analysis (runs persona, disclosure, error analyses in parallel)",
    )

    # =========================================================================
    # AI-Native Enhancements for HITL Dialogs
    # =========================================================================
    enable_ai_explanations: bool = Field(
        default=False,
        description="Enable AI-generated explanations for HITL dialogs using ExplanationOrchestrator (gradual rollout)",
    )

    # =========================================================================
    # Human-in-the-Loop (HITL) Features for Confidence-Based Agent Approval
    # =========================================================================
    enable_agent_hitl: bool = Field(
        default=True,
        description="Enable confidence-based human-in-the-loop for agent approvals",
    )

    agent_hitl_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Confidence threshold below which human approval is required (0.0-1.0)",
    )

    agent_hitl_auto_approve_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Confidence threshold at or above which auto-approval occurs (0.0-1.0)",
    )

    agent_hitl_approval_timeout_seconds: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Timeout for approval requests in seconds (60s-24h, default 1h)",
    )

    enable_agent_hitl_push_notifications: bool = Field(
        default=True,
        description="Enable push notifications for HITL approval requests",
    )

    enable_agent_hitl_websocket: bool = Field(
        default=True,
        description="Enable WebSocket for real-time HITL approval requests and updates",
    )

    # =========================================================================
    # WebSocket Infrastructure Features (ADR-0068 WebSocket Standardization)
    # =========================================================================
    enable_websocket_new_base: bool = Field(
        default=True,
        description="Enable new WebSocketBase infrastructure with standardized lifecycle, auth, and metrics. "
        "When False, uses legacy WebSocket handlers.",
    )

    enable_websocket_server_heartbeat: bool = Field(
        default=True,
        description="Enable server-initiated heartbeat for WebSocket connections. "
        "Sends heartbeat every 30s and detects dead connections after 2 missed intervals.",
    )

    enable_websocket_enhanced_metrics: bool = Field(
        default=True,
        description="Enable enhanced WebSocket metrics collection (connection counts, message rates, latency). "
        "Integrates with OpenTelemetry for observability.",
    )

    websocket_heartbeat_interval_seconds: int = Field(
        default=30,
        ge=10,
        le=120,
        description="Interval between server heartbeat messages in seconds (10-120)",
    )

    websocket_idle_timeout_seconds: int = Field(
        default=1800,
        ge=60,
        le=7200,
        description="Idle timeout for WebSocket connections in seconds (60-7200, default 30 min)",
    )

    websocket_rate_limit_per_minute: int = Field(
        default=600,
        ge=60,
        le=6000,
        description="Default rate limit for WebSocket messages per minute (60-6000)",
    )

    model_config = SettingsConfigDict(
        env_prefix="FF_",  # All flags use FF_ prefix in environment
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from environment
    )

    @property
    def is_test_mode(self) -> bool:
        """
        Check if running in test mode.

        When FF_TEST_MODE is set to a truthy value (true, 1, yes),
        all feature flag checks in require_feature() are bypassed.
        This enables testing of disabled features without complex mocking.

        Returns:
            True if FF_TEST_MODE is set to a truthy value, False otherwise.
        """
        test_mode = os.environ.get("FF_TEST_MODE", "").lower()
        return test_mode in ("true", "1", "yes")

    @property
    def effective_suggestion_strategy(self) -> str:
        """
        Get the effective suggestion strategy, considering both new and deprecated flags.

        Backward Compatibility:
        - If enable_llm_suggestions is explicitly set to False, returns "heuristic"
        - Otherwise, uses the new suggestion_strategy value

        Returns:
            One of: "llm", "heuristic", or "hybrid"
        """
        # If deprecated flag is False, map to heuristic strategy
        if not self.enable_llm_suggestions:
            return "heuristic"
        # Otherwise use the new strategy field
        return self.suggestion_strategy

    def get_rate_limit(self, feature: str | None = None) -> int:
        """
        Get the effective rate limit for a feature.

        Uses feature-specific override if set, otherwise falls back to default.

        Args:
            feature: Optional feature name ("suggestions", "frontend_cache", "websocket", None for API)

        Returns:
            Rate limit in requests per minute
        """
        if feature == "suggestions":
            return self.suggestion_rate_limit_per_minute
        elif feature == "frontend_cache":
            return self.frontend_redis_l2_rate_limit_per_minute
        elif feature == "websocket":
            return self.websocket_rate_limit_per_minute
        elif feature is None or feature == "api":
            return self.rate_limit_requests_per_minute
        else:
            # Unknown feature, use default
            return self.default_rate_limit_per_minute

    def get_cache_ttl(self, feature: str | None = None) -> int:
        """
        Get the effective cache TTL for a feature.

        Uses feature-specific override if set, otherwise falls back to default.

        Args:
            feature: Optional feature name ("llm", "suggestions", "ai_ux", "frontend_cache", "openfga")

        Returns:
            Cache TTL in seconds
        """
        cache_ttl_map = {
            "llm": self.cache_ttl_seconds,
            "suggestions": self.suggestion_cache_ttl_seconds,
            "ai_ux": self.ai_ux_redis_cache_ttl_seconds,
            "frontend_cache": self.frontend_redis_l2_cache_ttl_seconds,
            "openfga": self.openfga_cache_ttl_seconds,
        }
        return cache_ttl_map.get(feature, self.default_cache_ttl_seconds) if feature else self.default_cache_ttl_seconds

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature is enabled

        Args:
            feature_name: Name of the feature flag (e.g., 'enable_pydantic_ai_routing')

        Returns:
            True if feature is enabled, False otherwise
        """
        return getattr(self, feature_name, False)

    def require_feature(self, feature_name: str, display_name: str | None = None) -> None:
        """
        Require a feature to be enabled, raising FeatureDisabledError if not.

        Use this at the entry point of feature-gated functionality.

        When FF_TEST_MODE is set to a truthy value, all feature checks are
        bypassed to enable testing of disabled features.

        Args:
            feature_name: Name of the feature flag attribute
            display_name: Human-readable feature name for error message

        Raises:
            FeatureDisabledError: If the feature is disabled and not in test mode
        """
        # Test mode bypasses all feature flag checks
        if self.is_test_mode:
            return

        if not self.is_feature_enabled(feature_name):
            from mcp_server_langgraph.core.exceptions import FeatureDisabledError

            raise FeatureDisabledError(
                feature_name=display_name or feature_name.replace("enable_", "").replace("_", " ").title(),
                flag_name=f"FF_{feature_name.upper()}",
            )

    def get_feature_value(self, feature_name: str, default: Any | None = None) -> Any:
        """
        Get feature flag value with fallback

        Args:
            feature_name: Name of the feature flag
            default: Default value if flag not found

        Returns:
            Feature flag value or default
        """
        return getattr(self, feature_name, default)

    def should_use_experimental(self, feature_name: str) -> bool:
        """
        Check if experimental feature should be enabled

        Requires both the master experimental switch and individual feature flag.

        Args:
            feature_name: Name of the experimental feature

        Returns:
            True if both master switch and feature are enabled
        """
        if not self.enable_experimental_features:
            return False

        return self.is_feature_enabled(feature_name)

    def get_ui_features_for_role(self, role: str) -> dict[str, bool]:
        """
        Get UI feature availability based on user role.

        Admins get access to all features. Regular users get filtered access
        based on feature flags (e.g., cost_dashboard_users controls whether
        non-admins can see the cost dashboard).

        Args:
            role: User role (e.g., 'admin', 'user', 'viewer')

        Returns:
            Dictionary mapping feature names to their enabled status for this role.

        Example:
            >>> flags.get_ui_features_for_role('admin')
            {'workflows': True, 'sessions': True, 'cost_dashboard': True, ...}

            >>> flags.get_ui_features_for_role('user')
            {'workflows': True, 'sessions': True, 'cost_dashboard': False, ...}
        """
        is_admin = role.lower() == "admin"

        return {
            # Canvas feature flags (StudioShell is now default at /studio)
            "studio_canvas_shell": self.studio_canvas_shell,
            "canvas_editable": self.canvas_editable,
            "canvas_agents": self.canvas_agents,
            "canvas_ai_palette": self.canvas_ai_palette,
            "canvas_compliance": self.canvas_compliance,
            "canvas_help": self.canvas_help,
            # DevTools feature flags
            "devtools_panel": self.devtools_panel,
            "devtools_ai_insights": self.devtools_ai_insights,
            "devtools_ai_layout": self.devtools_ai_layout,
            "devtools_network_tab": self.devtools_network_tab,
            # Core features
            "workflows": self.enable_workflows_feature,
            "sessions": self.enable_sessions_feature,
            # Cost dashboard: admins always see it; users only if enable_cost_dashboard_users
            "cost_dashboard": (
                self.enable_cost_dashboard if is_admin else (self.enable_cost_dashboard and self.enable_cost_dashboard_users)
            ),
            "observability": self.enable_observability_ui,
            "code_export": self.enable_code_export,
            "ai_suggestions": self.enable_ai_suggestions,
            "ai_suggestions_websocket": self.enable_ai_suggestions_websocket,
            "suggestion_strategy": self.suggestion_strategy,
            "llm_suggestions": self.enable_llm_suggestions,  # DEPRECATED: use suggestion_strategy
            "notification_preferences": self.enable_notification_preferences,
            "mcp_websocket": self.enable_mcp_websocket,
            "interactive_artifacts": self.enable_interactive_artifacts,
            "url_content_fetch": self.enable_url_content_fetch,
            "slash_commands": self.enable_slash_commands,
            "style_presets": self.enable_style_presets,
            # UX Enhancement Features
            "user_preferences_sync": self.enable_user_preferences_sync,
            "session_export": self.enable_session_export,
            "project_context": self.enable_project_context,
            "onboarding_wizard": self.enable_onboarding_wizard,
            "guided_tour": self.enable_guided_tour,
            "sus_survey": self.enable_sus_survey,
            "command_palette": self.enable_command_palette,
            "keyboard_shortcuts": self.enable_keyboard_shortcuts,
            "theme_customization": self.enable_theme_customization,
            "confirmation_dialogs": self.enable_confirmation_dialogs,
            # AI UX Features (Phase 6 AI-Native Integration)
            "ai_ux": self.enable_ai_ux,  # Master AI UX toggle
            "ai_ux_websocket": self.enable_ai_ux_websocket,  # AI UX WebSocket
            "ai_ux_streaming": self.enable_ai_ux_streaming,  # AI UX streaming
            "ai_disclosure": self.enable_ai_disclosure,
            "ai_empty_states": self.enable_ai_empty_states,
            "ai_nudges": self.enable_ai_nudges,
            "ai_error_recovery": self.enable_ai_error_recovery,
            "ai_onboarding": self.enable_ai_onboarding,
            "ai_metrics_insights": self.enable_ai_metrics_insights,
            "ai_persona_analysis": self.enable_ai_persona_analysis,
            "batch_composite_analysis": self.enable_batch_composite_analysis,
            # HITL Features
            "agent_hitl": self.enable_agent_hitl,
            # Granular Intelligence Flags (StudioShell AI)
            "studio_ai": self.enable_studio_ai,
            "session_intelligence": self.enable_session_intelligence,
            "conversation_intelligence": self.enable_conversation_intelligence,
            "canvas_intelligence": self.enable_canvas_intelligence,
            "diagram_intelligence": self.enable_diagram_intelligence,
            "trace_intelligence": self.enable_trace_intelligence,
            "hitl_ai": self.enable_hitl_ai,
            "genui": self.enable_genui,
            # Frontend Redis L2 Cache
            "frontend_redis_l2_cache": self.enable_frontend_redis_l2_cache,
            # WebSocket Infrastructure Features
            "websocket_new_base": self.enable_websocket_new_base,
            "websocket_server_heartbeat": self.enable_websocket_server_heartbeat,
            "websocket_enhanced_metrics": self.enable_websocket_enhanced_metrics,
        }


# Global feature flags instance
feature_flags = FeatureFlags()


def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance"""
    return feature_flags


def is_enabled(feature_name: str) -> bool:
    """
    Convenience function to check if a feature is enabled

    Args:
        feature_name: Name of the feature flag

    Returns:
        True if enabled, False otherwise

    Example:
        if is_enabled('enable_pydantic_ai_routing'):
            # Use Pydantic AI routing
    """
    return feature_flags.is_feature_enabled(feature_name)


# Alias for backward compatibility
is_feature_enabled = is_enabled


def feature_gated(feature_name: str, display_name: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator to gate a function behind a feature flag.

    This decorator provides a cleaner alternative to calling require_feature()
    at the beginning of a function. It automatically checks the feature flag
    and raises FeatureDisabledError if the feature is disabled.

    The decorator is designed to be easily mockable in tests - you can simply
    mock the decorated function directly without needing to patch feature flags.

    Args:
        feature_name: Name of the feature flag attribute (e.g., 'enable_skills_system')
        display_name: Human-readable feature name for error messages (optional)

    Returns:
        A decorator that wraps the function with feature flag checking

    Raises:
        FeatureDisabledError: If the feature is disabled when the function is called

    Example:
        @feature_gated("enable_skills_system", "Skills System")
        def execute_skill(skill_name: str) -> SkillResult:
            # This function only runs if enable_skills_system is True
            ...

        @feature_gated("enable_multi_agent_orchestration")
        async def run_orchestrated_task(task: str) -> str:
            # Works with async functions too
            ...
    """
    import asyncio

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            feature_flags.require_feature(feature_name, display_name)
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            feature_flags.require_feature(feature_name, display_name)
            return await func(*args, **kwargs)  # type: ignore[misc, no-any-return]

        # Choose the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper

    return decorator
