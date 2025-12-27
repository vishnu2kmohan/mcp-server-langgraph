# Feature Flag Catalog

**Total Flags**: 165 (1 deprecated, 3 new)
**Last Updated**: 2025-12-27 (Sprint Block 5 Consolidation)

This catalog is generated from `src/mcp_server_langgraph/core/feature_flags.py`.

> **Sprint Block 5 Changes**: Deprecated `enable_multi_agent_collaboration` (merged into `multi_agent_strategy`), deprecated `enable_llm_suggestions` (replaced by `suggestion_strategy`), added unified helper methods `get_rate_limit()` and `get_cache_ttl()`.

---

## Table of Contents

1. [AI UX](#ai-ux) (13 flags)
2. [Agent Behavior](#agent-behavior) (7 flags)
3. [Agent HITL](#agent-hitl) (7 flags)
4. [Anthropic Best Practices](#anthropic-best-practices) (6 flags)
5. [Authorization](#authorization) (6 flags)
6. [Canvas](#canvas) (6 flags)
7. [Claude Agent SDK](#claude-agent-sdk) (6 flags)
8. [Context Engineering](#context-engineering) (11 flags)
9. [Cost Tracking](#cost-tracking) (4 flags)
10. [DevTools](#devtools) (4 flags)
11. [Experimental](#experimental) (1 flags)
12. [Frontend Cache](#frontend-cache) (1 flags)
13. [LLM](#llm) (6 flags)
14. [MCP Extensions](#mcp-extensions) (5 flags)
15. [Multi-Framework Parity](#multi-framework-parity) (5 flags)
16. [Observability](#observability) (5 flags)
17. [Orchestrator](#orchestrator) (6 flags)
18. [Performance](#performance) (7 flags)
19. [Pydantic AI](#pydantic-ai) (3 flags)
20. [Security](#security) (11 flags)
21. [Studio AI](#studio-ai) (7 flags)
22. [Thinking Budget](#thinking-budget) (2 flags)
23. [UI Features](#ui-features) (29 flags)
24. [Uncategorized](#uncategorized) (1 flags)
25. [WebSocket](#websocket) (5 flags)

---

## AI UX

*13 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_ai_disclosure` | bool | `True` | `FF_ENABLE_AI_DISCLOSURE` | Enable AI-powered progressive disclosure analysis for adaptive UI complexity |
| `enable_ai_empty_states` | bool | `True` | `FF_ENABLE_AI_EMPTY_STATES` | Enable AI-powered empty state suggestions with contextual CTAs |
| `enable_ai_error_recovery` | bool | `True` | `FF_ENABLE_AI_ERROR_RECOVERY` | Enable AI-powered error classification and recovery suggestions |
| `enable_ai_metrics_insights` | bool | `True` | `FF_ENABLE_AI_METRICS_INSIGHTS` | Enable AI-generated HEART metrics insights and predictions |
| `enable_ai_nudges` | bool | `True` | `FF_ENABLE_AI_NUDGES` | Enable AI-powered smart nudge recommendations based on user behavior |
| `enable_ai_onboarding` | bool | `True` | `FF_ENABLE_AI_ONBOARDING` | Enable AI-powered onboarding personalization based on detected intent |
| `enable_ai_persona_analysis` | bool | `True` | `FF_ENABLE_AI_PERSONA_ANALYSIS` | Enable AI-powered persona behavior analysis and mismatch detection |
| `enable_ai_ux` | bool | `True` | `FF_ENABLE_AI_UX` | Master switch for all AI UX features (disclosure, nudges, error recovery, etc.) |
| `enable_ai_ux_parallel_graph` | bool | `True` | `FF_ENABLE_AI_UX_PARALLEL_GRAPH` | Enable parallel graph execution using LangGraph Send API for faster analysis |
| `enable_ai_ux_redis_cache` | bool | `False` | `FF_ENABLE_AI_UX_REDIS_CACHE` | Enable Redis caching for LLM responses (reduces cost, requires Redis) |
| `enable_ai_ux_streaming` | bool | `True` | `FF_ENABLE_AI_UX_STREAMING` | Enable streaming responses for composite analysis via SSE |
| `enable_ai_ux_websocket` | bool | `True` | `FF_ENABLE_AI_UX_WEBSOCKET` | Enable WebSocket for real-time AI suggestions and live updates |
| `enable_batch_composite_analysis` | bool | `True` | `FF_ENABLE_BATCH_COMPOSITE_ANALYSIS` | Enable batch composite analysis (runs persona, disclosure, error analyses in ... |

## Agent Behavior

*8 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_agent_memory` | bool | `True` | `FF_ENABLE_AGENT_MEMORY` | Enable conversation memory/checkpointing for stateful agents |
| `enable_multi_agent_orchestration` | bool | `True` | `FF_ENABLE_MULTI_AGENT_ORCHESTRATION` | Enable orchestrator-worker pattern for parallel task execution. Supports up t... |
| `multi_agent_strategy` | str | `"orchestrator"` | `FF_MULTI_AGENT_STRATEGY` | Multi-agent coordination strategy: 'orchestrator' (hierarchical), 'peer' (decentralized), or 'hybrid' (adaptive). Replaces deprecated enable_multi_agent_collaboration flag. |
| `enable_tool_reflection` | bool | `True` | `FF_ENABLE_TOOL_REFLECTION` | Enable agents to reflect on tool usage effectiveness |
| `max_agent_iterations` | int | `10` | `FF_MAX_AGENT_ITERATIONS` | Maximum iterations for agent loops before stopping |
| `max_subagents` | int | `10` | `FF_MAX_SUBAGENTS` | Maximum number of parallel subagents in orchestrator (1-50) |
| `memory_max_messages` | int | `100` | `FF_MEMORY_MAX_MESSAGES` | Maximum messages to retain in conversation history |

> **Note**: `enable_multi_agent_collaboration` was deprecated in Sprint Block 5.
> Use `enable_multi_agent_orchestration` + `multi_agent_strategy` instead.

## Agent HITL

*7 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `agent_hitl_approval_timeout_seconds` | int | `3600` | `FF_AGENT_HITL_APPROVAL_TIMEOUT_SECONDS` | Timeout for approval requests in seconds (60s-24h, default 1h) |
| `agent_hitl_auto_approve_threshold` | float | `0.9` | `FF_AGENT_HITL_AUTO_APPROVE_THRESHOLD` | Confidence threshold at or above which auto-approval occurs (0.0-1.0) |
| `agent_hitl_confidence_threshold` | float | `0.7` | `FF_AGENT_HITL_CONFIDENCE_THRESHOLD` | Confidence threshold below which human approval is required (0.0-1.0) |
| `enable_agent_hitl` | bool | `True` | `FF_ENABLE_AGENT_HITL` | Enable confidence-based human-in-the-loop for agent approvals |
| `enable_agent_hitl_push_notifications` | bool | `True` | `FF_ENABLE_AGENT_HITL_PUSH_NOTIFICATIONS` | Enable push notifications for HITL approval requests |
| `enable_agent_hitl_websocket` | bool | `True` | `FF_ENABLE_AGENT_HITL_WEBSOCKET` | Enable WebSocket for real-time HITL approval requests and updates |
| `enable_ai_explanations` | bool | `False` | `FF_ENABLE_AI_EXPLANATIONS` | Enable AI-generated explanations for HITL dialogs using ExplanationOrchestrat... |

## Anthropic Best Practices

*6 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_defer_loading` | bool | `False` | `FF_ENABLE_DEFER_LOADING` | Enable defer_loading for tools to reduce initial token usage (experimental) |
| `enable_programmatic_tools` | bool | `False` | `FF_ENABLE_PROGRAMMATIC_TOOLS` | Enable programmatic tool calling from sandbox code (experimental). Allows san... |
| `enable_skills_marketplace` | bool | `True` | `FF_ENABLE_SKILLS_MARKETPLACE` | Enable skills marketplace integration with Anthropic skills repo. Fetches ski... |
| `enable_skills_system` | bool | `True` | `FF_ENABLE_SKILLS_SYSTEM` | Enable SKILL.md-based skills system for agent capabilities. Provides structur... |
| `enable_think_tool` | bool | `True` | `FF_ENABLE_THINK_TOOL` | Enable think tool for structured reasoning during tool chains (54% improvement) |
| `enable_tool_examples` | bool | `True` | `FF_ENABLE_TOOL_EXAMPLES` | Enable input_examples for tools to improve accuracy (72% -> 90% improvement) |

## Authorization

*6 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_keycloak` | bool | `True` | `FF_ENABLE_KEYCLOAK` | Enable Keycloak integration for authentication |
| `enable_openfga` | bool | `True` | `FF_ENABLE_OPENFGA` | Enable OpenFGA for fine-grained authorization checks |
| `keycloak_role_sync` | bool | `True` | `FF_KEYCLOAK_ROLE_SYNC` | Sync Keycloak roles/groups to OpenFGA on authentication |
| `openfga_cache_ttl_seconds` | int | `60` | `FF_OPENFGA_CACHE_TTL_SECONDS` | Cache authorization check results for N seconds (0=disabled) |
| `openfga_strict_mode` | bool | `False` | `FF_OPENFGA_STRICT_MODE` | Fail-closed on OpenFGA errors (strict) vs fail-open (permissive) |
| `openfga_sync_on_login` | bool | `True` | `FF_OPENFGA_SYNC_ON_LOGIN` | Synchronize user roles to OpenFGA on every login |

## Canvas

*6 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `canvas_agents` | bool | `False` | `FF_CANVAS_AGENTS` | Phase 4: Enable background agent panel |
| `canvas_ai_palette` | bool | `False` | `FF_CANVAS_AI_PALETTE` | Phase 4: Enable AI fallback in command palette |
| `canvas_compliance` | bool | `False` | `FF_CANVAS_COMPLIANCE` | Phase 5: Enable compliance dashboards (GDPR, HIPAA, SOC2, FedRAMP) |
| `canvas_editable` | bool | `False` | `FF_CANVAS_EDITABLE` | Phase 2: Enable editable artifacts in Canvas panel |
| `canvas_help` | bool | `False` | `FF_CANVAS_HELP` | Phase 6: Enable in-app help pane with contextual assistance |
| `studio_canvas_shell` | bool | `True` | `FF_STUDIO_CANVAS_SHELL` | Phase 1: Enable Studio Canvas shell at /studio (StudioShellLayout) |

## Claude Agent SDK

*6 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_sdk_agent_definition` | bool | `True` | `FF_ENABLE_SDK_AGENT_DEFINITION` | Enable Claude Agent SDK AgentDefinition pattern for declarative subagent crea... |
| `enable_sdk_can_use_tool` | bool | `False` | `FF_ENABLE_SDK_CAN_USE_TOOL` | Enable Claude Agent SDK can_use_tool callback for dynamic tool permission che... |
| `enable_sdk_file_checkpointing` | bool | `False` | `FF_ENABLE_SDK_FILE_CHECKPOINTING` | Enable Claude Agent SDK file checkpointing for rollback capability. Adds I/O ... |
| `enable_sdk_hooks` | bool | `True` | `FF_ENABLE_SDK_HOOKS` | Enable Claude Agent SDK hook system (PreToolUse, PostToolUse, UserPromptSubmi... |
| `enable_sdk_interrupt` | bool | `True` | `FF_ENABLE_SDK_INTERRUPT` | Enable Claude Agent SDK interrupt capability for graceful operation cancellat... |
| `enable_sdk_structured_output` | bool | `True` | `FF_ENABLE_SDK_STRUCTURED_OUTPUT` | Enable Claude Agent SDK structured output validation via JSON Schema. Product... |

## Context Engineering

*11 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `context_compaction_threshold_percentage` | float | `0.5` | `FF_CONTEXT_COMPACTION_THRESHOLD_PERCENTAGE` | Percentage of model's effective context limit that triggers compaction (0.1-0.9) |
| `context_deduplication_threshold` | float | `0.92` | `FF_CONTEXT_DEDUPLICATION_THRESHOLD` | Similarity threshold for context deduplication (0.5-0.99) |
| `context_split_threshold` | float | `0.8` | `FF_CONTEXT_SPLIT_THRESHOLD` | Percentage of effective limit that triggers splitting (0.5-0.95) |
| `enable_agentic_memory` | bool | `False` | `FF_ENABLE_AGENTIC_MEMORY` | Enable structured note-taking (NOTES.md) and checkpoints for agentic memory (... |
| `enable_context_ranking` | bool | `True` | `FF_ENABLE_CONTEXT_RANKING` | Rank contexts by relevance before loading into context window |
| `enable_dynamic_context_splitting` | bool | `True` | `FF_ENABLE_DYNAMIC_CONTEXT_SPLITTING` | Enable dynamic context splitting for large tasks |
| `enable_lost_in_middle_mitigation` | bool | `True` | `FF_ENABLE_LOST_IN_MIDDLE_MITIGATION` | Reorder context to place key info at start/end for better attention |
| `enable_model_aware_compaction` | bool | `True` | `FF_ENABLE_MODEL_AWARE_COMPACTION` | Enable model-aware context compaction using model registry context limits |
| `enable_model_capabilities_routing` | bool | `True` | `FF_ENABLE_MODEL_CAPABILITIES_ROUTING` | Enable capability-aware model routing via model registry |
| `enable_semantic_deduplication` | bool | `True` | `FF_ENABLE_SEMANTIC_DEDUPLICATION` | Deduplicate semantically similar contexts to reduce redundancy |
| `enable_short_tool_descriptions` | bool | `True` | `FF_ENABLE_SHORT_TOOL_DESCRIPTIONS` | Use short-form tool descriptions to reduce token usage (~40% savings) |

## Cost Tracking

*4 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `cost_alert_thresholds` | list[float] | `[0.5, 0.75, 0.9]` | `FF_COST_ALERT_THRESHOLDS` | Percentage thresholds for cost alerts (e.g., [0.5, 0.75, 0.9]) |
| `enable_cost_tracking` | bool | `True` | `FF_ENABLE_COST_TRACKING` | Enable token and cost budget tracking for orchestrations |
| `orchestration_cost_limit` | float | `0.5` | `FF_ORCHESTRATION_COST_LIMIT` | Maximum cost in dollars per single orchestration (0.01-100.0) |
| `session_cost_limit` | float | `5.0` | `FF_SESSION_COST_LIMIT` | Maximum cost in dollars per session (0.10-1000.0) |

## DevTools

*4 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `devtools_ai_insights` | bool | `False` | `FF_DEVTOOLS_AI_INSIGHTS` | Enable AI Insights tab in DevTools for anomaly detection and suggestions |
| `devtools_ai_layout` | bool | `False` | `FF_DEVTOOLS_AI_LAYOUT` | Enable AI-powered layout suggestions in DevTools based on context |
| `devtools_network_tab` | bool | `True` | `FF_DEVTOOLS_NETWORK_TAB` | Enable Network tab in DevTools for API/WebSocket monitoring |
| `devtools_panel` | bool | `True` | `FF_DEVTOOLS_PANEL` | Enable DevTools panel for debugging (master toggle) |

## Experimental

*1 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_experimental_features` | bool | `False` | `FF_ENABLE_EXPERIMENTAL_FEATURES` | Master switch for all experimental features |

## Frontend Cache

*1 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_frontend_redis_l2_cache` | bool | `False` | `FF_ENABLE_FRONTEND_REDIS_L2_CACHE` | Enable Redis L2 caching for frontend useTieredCache hook (cross-tab sharing) |

## LLM

*7 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_llm_fallback` | bool | `True` | `FF_ENABLE_LLM_FALLBACK` | Enable automatic fallback to alternative models on failure |
| `enable_llm_hooks` | bool | `True` | `FF_ENABLE_LLM_HOOKS` | Enable LLM-level hooks (BEFORE_MODEL, AFTER_MODEL) for request/response inter... |
| `enable_llm_suggestions` | bool | `True` | `FF_ENABLE_LLM_SUGGESTIONS` | **[DEPRECATED]** Use `suggestion_strategy` instead. When False, uses heuristics only. |
| `suggestion_strategy` | str | `"llm"` | `FF_SUGGESTION_STRATEGY` | Suggestion generation strategy: 'llm' (AI-powered, best quality), 'heuristic' (rule-based, lower cost), or 'hybrid' (adaptive). Replaces deprecated enable_llm_suggestions flag. |
| `enable_streaming_responses` | bool | `True` | `FF_ENABLE_STREAMING_RESPONSES` | Enable streaming responses for real-time output |
| `enable_streaming_suggestions` | bool | `True` | `FF_ENABLE_STREAMING_SUGGESTIONS` | Enable streaming suggestions via SSE for real-time response |
| `llm_timeout_seconds` | int | `60` | `FF_LLM_TIMEOUT_SECONDS` | Maximum time to wait for LLM responses (10-300 seconds) |

> **Note**: `enable_llm_suggestions` was deprecated in Sprint Block 5.
> Use `suggestion_strategy` instead. The `effective_suggestion_strategy` property provides backward compatibility.

## MCP Extensions

*5 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_bash_tool` | bool | `False` | `FF_ENABLE_BASH_TOOL` | Enable enhanced bash tool for sandboxed command execution beyond Python. |
| `enable_computer_use` | bool | `False` | `FF_ENABLE_COMPUTER_USE` | Enable computer use tools for screen capture, input simulation, and browser a... |
| `enable_hooks_mcp_extension` | bool | `False` | `FF_ENABLE_HOOKS_MCP_EXTENSION` | Enable hooks MCP tool for listing registered hooks and available events. Expe... |
| `enable_orchestration_mcp_resources` | bool | `False` | `FF_ENABLE_ORCHESTRATION_MCP_RESOURCES` | Expose multi-agent orchestration as MCP resources (orchestrator://tasks, arti... |
| `enable_orchestration_mcp_tools` | bool | `False` | `FF_ENABLE_ORCHESTRATION_MCP_TOOLS` | Expose orchestration operations as MCP tools (decompose, execute, status, can... |

## Multi-Framework Parity

*5 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_handoff_pattern` | bool | `True` | `FF_ENABLE_HANDOFF_PATTERN` | Enable Handoff pattern (ADR-0081) for explicit agent-to-agent control transfe... |
| `enable_loop_agent` | bool | `False` | `FF_ENABLE_LOOP_AGENT` | Enable LoopAgent pattern (Google ADK parity) for iterative task execution wit... |
| `enable_mcp_client` | bool | `True` | `FF_ENABLE_MCP_CLIENT` | Enable MCP client capabilities (ADR-0082) to consume tools from external MCP ... |
| `enable_session_fork` | bool | `False` | `FF_ENABLE_SESSION_FORK` | Enable session fork capability (Claude Agent SDK parity) for branching conver... |
| `enable_session_hooks` | bool | `True` | `FF_ENABLE_SESSION_HOOKS` | Enable session lifecycle hooks (SESSION_START, SESSION_END) for initializatio... |

## Observability

*5 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_detailed_logging` | bool | `True` | `FF_ENABLE_DETAILED_LOGGING` | Include detailed context in logs (may increase log volume) |
| `enable_langsmith` | bool | `False` | `FF_ENABLE_LANGSMITH` | Enable LangSmith tracing for LLM-specific observability |
| `enable_trace_intelligence` | bool | `False` | `FF_ENABLE_TRACE_INTELLIGENCE` | Enable trace intelligence: summarize agent traces, detect anomalies |
| `enable_trace_sampling` | bool | `False` | `FF_ENABLE_TRACE_SAMPLING` | Sample traces rather than capturing all (reduces overhead) |
| `trace_sample_rate` | float | `0.1` | `FF_TRACE_SAMPLE_RATE` | Percentage of traces to sample when sampling enabled (0.0-1.0) |

## Orchestrator

*6 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_orchestrated_ai_ux` | bool | `False` | `FF_ENABLE_ORCHESTRATED_AI_UX` | Enable orchestrated AI UX composite analysis for parallel execution (gradual ... |
| `enable_orchestrated_alert_analysis` | bool | `False` | `FF_ENABLE_ORCHESTRATED_ALERT_ANALYSIS` | Enable orchestrated alert analysis for parallel correlation and root cause (g... |
| `enable_orchestrator_resilience` | bool | `True` | `FF_ENABLE_ORCHESTRATOR_RESILIENCE` | Enable resilience patterns (circuit breaker, timeout, bulkhead) for orchestrator |
| `orchestrator_circuit_breaker_threshold` | int | `3` | `FF_ORCHESTRATOR_CIRCUIT_BREAKER_THRESHOLD` | Number of failures before circuit breaker opens (1-10) |
| `orchestrator_max_concurrent` | int | `5` | `FF_ORCHESTRATOR_MAX_CONCURRENT` | Maximum concurrent orchestrations allowed (bulkhead limit) (1-20) |
| `orchestrator_timeout_seconds` | int | `300` | `FF_ORCHESTRATOR_TIMEOUT_SECONDS` | Maximum time in seconds for orchestrator execution (30-600) |

## Performance

*9 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `ai_ux_redis_cache_ttl_seconds` | int | `300` | `FF_AI_UX_REDIS_CACHE_TTL_SECONDS` | TTL for Redis-cached AI UX responses (60s-1h) |
| `cache_ttl_seconds` | int | `300` | `FF_CACHE_TTL_SECONDS` | How long to cache responses (60s-24h) |
| `default_cache_ttl_seconds` | int | `300` | `FF_DEFAULT_CACHE_TTL_SECONDS` | Default cache TTL for unknown features. Use `get_cache_ttl(feature)` helper method. |
| `default_rate_limit_per_minute` | int | `60` | `FF_DEFAULT_RATE_LIMIT_PER_MINUTE` | Default rate limit for unknown features. Use `get_rate_limit(feature)` helper method. |
| `enable_request_batching` | bool | `True` | `FF_ENABLE_REQUEST_BATCHING` | Batch multiple requests to reduce LLM API calls |
| `enable_response_caching` | bool | `False` | `FF_ENABLE_RESPONSE_CACHING` | Cache LLM responses for identical inputs (experimental) |
| `frontend_redis_l2_cache_ttl_seconds` | int | `300` | `FF_FRONTEND_REDIS_L2_CACHE_TTL_SECONDS` | TTL for frontend Redis L2 cache entries (60s-1h) |
| `max_batch_size` | int | `10` | `FF_MAX_BATCH_SIZE` | Maximum number of requests to batch together |
| `suggestion_cache_ttl_seconds` | int | `300` | `FF_SUGGESTION_CACHE_TTL_SECONDS` | Time-to-live for suggestion cache entries (60s-1h) |

> **Helper Methods**: Use `get_rate_limit(feature)` and `get_cache_ttl(feature)` to get unified rate limits and cache TTLs with feature-specific overrides. See [Programmatic Access](#programmatic-access) for details.

## Pydantic AI

*3 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_pydantic_ai_responses` | bool | `True` | `FF_ENABLE_PYDANTIC_AI_RESPONSES` | Use Pydantic AI for structured response generation with validation |
| `enable_pydantic_ai_routing` | bool | `True` | `FF_ENABLE_PYDANTIC_AI_ROUTING` | Use Pydantic AI for type-safe routing decisions with confidence scoring |
| `pydantic_ai_confidence_threshold` | float | `0.7` | `FF_PYDANTIC_AI_CONFIDENCE_THRESHOLD` | Minimum confidence score to trust Pydantic AI routing (0.0-1.0) |

## Security

*11 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_distributed_rate_limiting` | bool | `False` | `FF_ENABLE_DISTRIBUTED_RATE_LIMITING` | Use Redis for distributed rate limiting (required for multi-instance deployme... |
| `enable_encrypted_sessions` | bool | `False` | `FF_ENABLE_ENCRYPTED_SESSIONS` | Enable at-rest encryption for session data. Provides GDPR/HIPAA compliance fo... |
| `enable_frontend_redis_l2_rate_limiting` | bool | `True` | `FF_ENABLE_FRONTEND_REDIS_L2_RATE_LIMITING` | Enable rate limiting for frontend Redis L2 cache API (prevents cache flooding) |
| `enable_input_validation` | bool | `True` | `FF_ENABLE_INPUT_VALIDATION` | Validate and sanitize all user inputs |
| `enable_pii_tokenization` | bool | `True` | `FF_ENABLE_PII_TOKENIZATION` | Enable PII tokenization layer for GDPR/HIPAA compliance. Automatically detect... |
| `enable_rate_limiting` | bool | `True` | `FF_ENABLE_RATE_LIMITING` | Enable rate limiting to prevent abuse |
| `frontend_redis_l2_rate_limit_per_minute` | int | `60` | `FF_FRONTEND_REDIS_L2_RATE_LIMIT_PER_MINUTE` | Maximum frontend cache API requests per minute per user (1-1000) |
| `max_input_length` | int | `10000` | `FF_MAX_INPUT_LENGTH` | Maximum input length in characters |
| `rate_limit_requests_per_minute` | int | `60` | `FF_RATE_LIMIT_REQUESTS_PER_MINUTE` | Maximum requests per minute per user |
| `suggestion_rate_limit_per_minute` | int | `60` | `FF_SUGGESTION_RATE_LIMIT_PER_MINUTE` | Maximum suggestion requests per minute per user (1-1000) |
| `websocket_rate_limit_per_minute` | int | `600` | `FF_WEBSOCKET_RATE_LIMIT_PER_MINUTE` | Default rate limit for WebSocket messages per minute (60-6000) |

## Studio AI

*7 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_canvas_intelligence` | bool | `False` | `FF_ENABLE_CANVAS_INTELLIGENCE` | Enable canvas intelligence: artifact type suggestions, code analysis, diff ex... |
| `enable_conversation_intelligence` | bool | `False` | `FF_ENABLE_CONVERSATION_INTELLIGENCE` | Enable conversation intelligence: intent detection, context optimization, goa... |
| `enable_diagram_intelligence` | bool | `False` | `FF_ENABLE_DIAGRAM_INTELLIGENCE` | Enable diagram intelligence: analyze diagrams, convert to code |
| `enable_genui` | bool | `False` | `FF_ENABLE_GENUI` | Enable generative UI: dynamic component rendering based on AI suggestions |
| `enable_hitl_ai` | bool | `False` | `FF_ENABLE_HITL_AI` | Enable HITL AI: risk assessment, decision history for agent approvals |
| `enable_session_intelligence` | bool | `False` | `FF_ENABLE_SESSION_INTELLIGENCE` | Enable session intelligence: summarize, group, similarity analysis |
| `enable_studio_ai` | bool | `False` | `FF_ENABLE_STUDIO_AI` | Enable unified Studio AI orchestration for StudioShell AI capabilities (gradu... |

## Thinking Budget

*2 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `default_thinking_level` | str | `"medium"` | `FF_DEFAULT_THINKING_LEVEL` | Default thinking level (low, medium, high, ultra) |
| `enable_thinking_budget` | bool | `True` | `FF_ENABLE_THINKING_BUDGET` | Enable thinking budget management for extended reasoning |

## UI Features

*29 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_ai_suggestions` | bool | `True` | `FF_ENABLE_AI_SUGGESTIONS` | Enable AI-powered suggestions in UI |
| `enable_ai_suggestions_websocket` | bool | `True` | `FF_ENABLE_AI_SUGGESTIONS_WEBSOCKET` | Enable AI suggestions WebSocket endpoint (/api/v1/ws/ai/suggestions). Require... |
| `enable_code_export` | bool | `True` | `FF_ENABLE_CODE_EXPORT` | Enable code export feature in workflow builder |
| `enable_command_palette` | bool | `True` | `FF_ENABLE_COMMAND_PALETTE` | Enable command palette (Cmd+K) for quick actions |
| `enable_confirmation_dialogs` | bool | `True` | `FF_ENABLE_CONFIRMATION_DIALOGS` | Enable confirmation dialogs for destructive actions |
| `enable_conversation_history_validation` | bool | `True` | `FF_ENABLE_CONVERSATION_HISTORY_VALIDATION` | Validate and sanitize conversation history to prevent prompt injection |
| `enable_cost_dashboard` | bool | `True` | `FF_ENABLE_COST_DASHBOARD` | Enable cost dashboard for admins |
| `enable_cost_dashboard_users` | bool | `False` | `FF_ENABLE_COST_DASHBOARD_USERS` | Enable cost dashboard for regular users (not just admins) |
| `enable_guided_tour` | bool | `True` | `FF_ENABLE_GUIDED_TOUR` | Enable guided tour after onboarding for feature discovery |
| `enable_interactive_artifacts` | bool | `True` | `FF_ENABLE_INTERACTIVE_ARTIFACTS` | Enable interactive artifact rendering in chat (Sandpack for JSX/TSX/MDX, Merm... |
| `enable_keyboard_shortcuts` | bool | `True` | `FF_ENABLE_KEYBOARD_SHORTCUTS` | Enable customizable keyboard shortcuts |
| `enable_mcp_websocket` | bool | `True` | `FF_ENABLE_MCP_WEBSOCKET` | Enable MCP 2025-11-25 WebSocket protocol for real-time bidirectional communic... |
| `enable_notification_preferences` | bool | `True` | `FF_ENABLE_NOTIFICATION_PREFERENCES` | Enable notification preferences UI for users to customize notification types |
| `enable_observability_ui` | bool | `True` | `FF_ENABLE_OBSERVABILITY_UI` | Enable observability/trace UI feature |
| `enable_onboarding_wizard` | bool | `True` | `FF_ENABLE_ONBOARDING_WIZARD` | Enable onboarding wizard for first-time users |
| `enable_personalized_suggestions` | bool | `True` | `FF_ENABLE_PERSONALIZED_SUGGESTIONS` | Enable personalized suggestions based on conversation history |
| `enable_project_context` | bool | `True` | `FF_ENABLE_PROJECT_CONTEXT` | Enable .studio/context.md project context files (AGENTS.md equivalent) |
| `enable_session_export` | bool | `True` | `FF_ENABLE_SESSION_EXPORT` | Enable exporting chat sessions to Markdown, JSON, or HTML formats |
| `enable_sessions_feature` | bool | `True` | `FF_ENABLE_SESSIONS_FEATURE` | Enable chat sessions UI feature |
| `enable_slash_commands` | bool | `True` | `FF_ENABLE_SLASH_COMMANDS` | Enable slash commands (/) for quick actions and workflow templates in chat input |
| `enable_style_presets` | bool | `True` | `FF_ENABLE_STYLE_PRESETS` | Enable response style presets selector in chat (concise, detailed, etc.) |
| `enable_suggestion_prewarm` | bool | `False` | `FF_ENABLE_SUGGESTION_PREWARM` | Pre-compute suggestions for common topics (experimental, increases startup time) |
| `enable_suggestion_quality_tracking` | bool | `True` | `FF_ENABLE_SUGGESTION_QUALITY_TRACKING` | Track suggestion click rates and quality metrics for improvement |
| `enable_sus_survey` | bool | `True` | `FF_ENABLE_SUS_SURVEY` | Enable System Usability Scale (SUS) survey after 3 sessions or 7 days |
| `enable_theme_customization` | bool | `True` | `FF_ENABLE_THEME_CUSTOMIZATION` | Enable theme customization (light/dark/system) |
| `enable_url_content_fetch` | bool | `True` | `FF_ENABLE_URL_CONTENT_FETCH` | Enable #URL content fetch feature for including web content in chat context (... |
| `enable_user_preferences_sync` | bool | `True` | `FF_ENABLE_USER_PREFERENCES_SYNC` | Enable syncing user preferences (theme, accessibility, model defaults) to bac... |
| `enable_workflows_feature` | bool | `True` | `FF_ENABLE_WORKFLOWS_FEATURE` | Enable workflow builder UI feature |
| `max_conversation_history_messages` | int | `5` | `FF_MAX_CONVERSATION_HISTORY_MESSAGES` | Maximum conversation history messages to include for personalization (1-20) |

## Uncategorized

*1 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_token_refresh` | bool | `True` | `FF_ENABLE_TOKEN_REFRESH` | Enable automatic token refresh for Keycloak tokens |

## WebSocket

*5 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_websocket_enhanced_metrics` | bool | `True` | `FF_ENABLE_WEBSOCKET_ENHANCED_METRICS` | Enable enhanced WebSocket metrics collection (connection counts, message rate... |
| `enable_websocket_new_base` | bool | `True` | `FF_ENABLE_WEBSOCKET_NEW_BASE` | Enable new WebSocketBase infrastructure with standardized lifecycle, auth, an... |
| `enable_websocket_server_heartbeat` | bool | `True` | `FF_ENABLE_WEBSOCKET_SERVER_HEARTBEAT` | Enable server-initiated heartbeat for WebSocket connections. Sends heartbeat ... |
| `websocket_heartbeat_interval_seconds` | int | `30` | `FF_WEBSOCKET_HEARTBEAT_INTERVAL_SECONDS` | Interval between server heartbeat messages in seconds (10-120) |
| `websocket_idle_timeout_seconds` | int | `1800` | `FF_WEBSOCKET_IDLE_TIMEOUT_SECONDS` | Idle timeout for WebSocket connections in seconds (60-7200, default 30 min) |

---

## Usage

Feature flags can be configured via environment variables with the `FF_` prefix:

```bash
# Enable a feature
export FF_ENABLE_LANGSMITH=true

# Set a numeric value
export FF_LLM_TIMEOUT_SECONDS=120

# Configure in .env file
FF_ENABLE_OPENFGA=true
FF_OPENFGA_STRICT_MODE=true
```

## Programmatic Access

```python
from mcp_server_langgraph.core.feature_flags import get_feature_flags

flags = get_feature_flags()

# Check if feature is enabled
if flags.enable_langsmith:
    print("LangSmith tracing enabled")

# Require feature (raises FeatureDisabledError if disabled)
flags.require_feature("enable_langsmith", "LangSmith Tracing")

# --- Sprint Block 5 Consolidation Helper Methods ---

# Get unified rate limits with feature-specific overrides
rate_limit = flags.get_rate_limit("suggestions")  # Returns suggestion_rate_limit_per_minute
rate_limit = flags.get_rate_limit("api")          # Returns rate_limit_requests_per_minute
rate_limit = flags.get_rate_limit("unknown")      # Returns default_rate_limit_per_minute

# Get unified cache TTLs with feature-specific overrides
cache_ttl = flags.get_cache_ttl("llm")         # Returns cache_ttl_seconds
cache_ttl = flags.get_cache_ttl("suggestions") # Returns suggestion_cache_ttl_seconds
cache_ttl = flags.get_cache_ttl("openfga")     # Returns openfga_cache_ttl_seconds
cache_ttl = flags.get_cache_ttl("unknown")     # Returns default_cache_ttl_seconds

# Get effective suggestion strategy (backward-compatible)
# Returns "heuristic" if enable_llm_suggestions=False, otherwise suggestion_strategy
strategy = flags.effective_suggestion_strategy  # "llm" | "heuristic" | "hybrid"

# Multi-agent strategy
strategy = flags.multi_agent_strategy  # "orchestrator" | "peer" | "hybrid"
```

## Deprecation Notes (Sprint Block 5)

The following flags were deprecated and consolidated:

| Deprecated Flag | Replacement |
|-----------------|-------------|
| `enable_multi_agent_collaboration` | `enable_multi_agent_orchestration` + `multi_agent_strategy` |
| `enable_llm_suggestions` | `suggestion_strategy` (use `effective_suggestion_strategy` property) |

**Migration Example:**

```python
# Before (deprecated)
if flags.enable_multi_agent_collaboration:
    use_collaboration()

# After (recommended)
if flags.enable_multi_agent_orchestration:
    if flags.multi_agent_strategy == "orchestrator":
        use_orchestrator_pattern()
    elif flags.multi_agent_strategy == "peer":
        use_peer_pattern()
```
