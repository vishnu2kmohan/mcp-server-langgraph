# Feature Flag Catalog

**Total Flags**: 225
**Generated**: 2026-01-11 14:00:11 UTC

This catalog is auto-generated from `src/mcp_server_langgraph/core/feature_flags.py`.

---

## Table of Contents

1. [AI UX](#ai-ux) (13 flags)
2. [Agent Behavior](#agent-behavior) (6 flags)
3. [Agent HITL](#agent-hitl) (7 flags)
4. [Anthropic Best Practices](#anthropic-best-practices) (6 flags)
5. [Authorization](#authorization) (9 flags)
6. [Canvas](#canvas) (6 flags)
7. [Claude Agent SDK](#claude-agent-sdk) (6 flags)
8. [Context Engineering](#context-engineering) (11 flags)
9. [Cost Tracking](#cost-tracking) (4 flags)
10. [DevTools](#devtools) (4 flags)
11. [Experimental](#experimental) (1 flags)
12. [Frontend Cache](#frontend-cache) (1 flags)
13. [LLM](#llm) (9 flags)
14. [MCP Extensions](#mcp-extensions) (5 flags)
15. [Multi-Framework Parity](#multi-framework-parity) (5 flags)
16. [Observability](#observability) (5 flags)
17. [Orchestrator](#orchestrator) (8 flags)
18. [Performance](#performance) (9 flags)
19. [Pydantic AI](#pydantic-ai) (3 flags)
20. [Security](#security) (14 flags)
21. [Studio AI](#studio-ai) (7 flags)
22. [Thinking Budget](#thinking-budget) (2 flags)
23. [UI Features](#ui-features) (30 flags)
24. [Uncategorized](#uncategorized) (49 flags)
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
| `enable_ai_ux` | bool | `True` | `FF_ENABLE_AI_UX` | Master switch for all AI UX features (disclosure, nudges, error recovery, etc... |
| `enable_ai_ux_parallel_graph` | bool | `True` | `FF_ENABLE_AI_UX_PARALLEL_GRAPH` | Enable parallel graph execution using LangGraph Send API for faster analysis |
| `enable_ai_ux_redis_cache` | bool | `False` | `FF_ENABLE_AI_UX_REDIS_CACHE` | Enable Redis caching for LLM responses (reduces cost, requires Redis) |
| `enable_ai_ux_streaming` | bool | `True` | `FF_ENABLE_AI_UX_STREAMING` | Enable streaming responses for composite analysis via SSE |
| `enable_ai_ux_websocket` | bool | `True` | `FF_ENABLE_AI_UX_WEBSOCKET` | Enable WebSocket for real-time AI suggestions and live updates |
| `enable_batch_composite_analysis` | bool | `True` | `FF_ENABLE_BATCH_COMPOSITE_ANALYSIS` | Enable batch composite analysis (runs persona, disclosure, error analyses in ... |

## Agent Behavior

*6 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_agent_memory` | bool | `True` | `FF_ENABLE_AGENT_MEMORY` | Enable conversation memory/checkpointing for stateful agents |
| `enable_multi_agent_orchestration` | bool | `True` | `FF_ENABLE_MULTI_AGENT_ORCHESTRATION` | Enable orchestrator-worker pattern for parallel task execution. Supports up t... |
| `enable_tool_reflection` | bool | `True` | `FF_ENABLE_TOOL_REFLECTION` | Enable agents to reflect on tool usage effectiveness |
| `max_agent_iterations` | int | `10` | `FF_MAX_AGENT_ITERATIONS` | Maximum iterations for agent loops before stopping |
| `max_subagents` | int | `10` | `FF_MAX_SUBAGENTS` | Maximum number of parallel subagents in orchestrator (1-50) |
| `memory_max_messages` | int | `100` | `FF_MEMORY_MAX_MESSAGES` | Maximum messages to retain in conversation history |

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

*9 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_keycloak` | bool | `True` | `FF_ENABLE_KEYCLOAK` | Enable Keycloak integration for authentication |
| `enable_openfga` | bool | `True` | `FF_ENABLE_OPENFGA` | Enable OpenFGA for fine-grained authorization checks |
| `keycloak_role_sync` | bool | `True` | `FF_KEYCLOAK_ROLE_SYNC` | Sync Keycloak roles/groups to OpenFGA on authentication |
| `openfga_cache_ttl_seconds` | int | `60` | `FF_OPENFGA_CACHE_TTL_SECONDS` | Cache authorization check results for N seconds (0=disabled) |
| `openfga_conditions_enabled` | bool | `False` | `FF_OPENFGA_CONDITIONS_ENABLED` | Enable OpenFGA condition evaluation in authorization checks. Requires OpenFGA... |
| `openfga_org_context_enforcement` | bool | `False` | `FF_OPENFGA_ORG_CONTEXT_ENFORCEMENT` | Require org context in authorization checks. When enabled, contextual tuples ... |
| `openfga_org_context_fail_closed` | bool | `True` | `FF_OPENFGA_ORG_CONTEXT_FAIL_CLOSED` | Fail closed when org context is missing and enforcement is enabled. When True... |
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

*9 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_litellm_model_sync` | bool | `False` | `FF_ENABLE_LITELLM_MODEL_SYNC` | Enable background sync of model pricing from LiteLLM to ModelRegistry. When e... |
| `enable_litellm_otel` | bool | `True` | `FF_ENABLE_LITELLM_OTEL` | Enable LiteLLM native OTEL callback for enhanced LLM tracing. Provides gen_ai... |
| `enable_llm_factory_streaming` | bool | `True` | `FF_ENABLE_LLM_FACTORY_STREAMING` | Use LLMFactory.astream() for streaming with resilience patterns (bulkhead, ci... |
| `enable_llm_fallback` | bool | `True` | `FF_ENABLE_LLM_FALLBACK` | Enable automatic fallback to alternative models on failure |
| `enable_llm_hooks` | bool | `True` | `FF_ENABLE_LLM_HOOKS` | Enable LLM-level hooks (BEFORE_MODEL, AFTER_MODEL) for request/response inter... |
| `enable_llm_suggestions` | bool | `True` | `FF_ENABLE_LLM_SUGGESTIONS` | [DEPRECATED] Use suggestion_strategy='llm' instead. When False, uses heuristi... |
| `enable_streaming_responses` | bool | `True` | `FF_ENABLE_STREAMING_RESPONSES` | Enable streaming responses for real-time output |
| `enable_streaming_suggestions` | bool | `True` | `FF_ENABLE_STREAMING_SUGGESTIONS` | Enable streaming suggestions via SSE for real-time response |
| `llm_timeout_seconds` | int | `60` | `FF_LLM_TIMEOUT_SECONDS` | Maximum time to wait for LLM responses (10-300 seconds) |

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

*8 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_orchestrated_ai_ux` | bool | `False` | `FF_ENABLE_ORCHESTRATED_AI_UX` | Enable orchestrated AI UX composite analysis for parallel execution (gradual ... |
| `enable_orchestrated_alert_analysis` | bool | `False` | `FF_ENABLE_ORCHESTRATED_ALERT_ANALYSIS` | Enable orchestrated alert analysis for parallel correlation and root cause (g... |
| `enable_orchestrator_resilience` | bool | `True` | `FF_ENABLE_ORCHESTRATOR_RESILIENCE` | Enable resilience patterns (circuit breaker, timeout, bulkhead) for orchestrator |
| `enable_orchestrator_selector` | bool | `False` | `FF_ENABLE_ORCHESTRATOR_SELECTOR` | Enable frontend orchestrator mode selector in chat UI. When enabled, users ca... |
| `enable_orchestrator_status_websocket` | bool | `True` | `FF_ENABLE_ORCHESTRATOR_STATUS_WEBSOCKET` | Enable AI orchestrator status WebSocket endpoint (/api/v1/ws/orchestrator/sta... |
| `orchestrator_circuit_breaker_threshold` | int | `3` | `FF_ORCHESTRATOR_CIRCUIT_BREAKER_THRESHOLD` | Number of failures before circuit breaker opens (1-10) |
| `orchestrator_max_concurrent` | int | `5` | `FF_ORCHESTRATOR_MAX_CONCURRENT` | Maximum concurrent orchestrations allowed (bulkhead limit) (1-20) |
| `orchestrator_timeout_seconds` | int | `300` | `FF_ORCHESTRATOR_TIMEOUT_SECONDS` | Maximum time in seconds for orchestrator execution (30-600) |

## Performance

*9 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `ai_ux_redis_cache_ttl_seconds` | int | `300` | `FF_AI_UX_REDIS_CACHE_TTL_SECONDS` | TTL for Redis-cached AI UX responses (60s-1h) |
| `cache_ttl_seconds` | int | `300` | `FF_CACHE_TTL_SECONDS` | How long to cache LLM responses (60s-24h) |
| `default_cache_ttl_seconds` | int | `300` | `FF_DEFAULT_CACHE_TTL_SECONDS` | Default cache TTL for all features (60s-24h). Feature-specific TTLs override ... |
| `enable_request_batching` | bool | `True` | `FF_ENABLE_REQUEST_BATCHING` | Batch multiple requests to reduce LLM API calls |
| `enable_response_caching` | bool | `False` | `FF_ENABLE_RESPONSE_CACHING` | Cache LLM responses for identical inputs (experimental) |
| `frontend_redis_l2_cache_ttl_seconds` | int | `300` | `FF_FRONTEND_REDIS_L2_CACHE_TTL_SECONDS` | TTL for frontend Redis L2 cache entries (60s-1h) |
| `max_batch_size` | int | `10` | `FF_MAX_BATCH_SIZE` | Maximum number of requests to batch together |
| `router_cache_ttl_seconds` | int | `3600` | `FF_ROUTER_CACHE_TTL_SECONDS` | TTL in seconds for router classification cache (60s-24h). Default 1 hour. Adj... |
| `suggestion_cache_ttl_seconds` | int | `300` | `FF_SUGGESTION_CACHE_TTL_SECONDS` | Time-to-live for suggestion cache entries (60s-1h) |

## Pydantic AI

*3 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_pydantic_ai_responses` | bool | `True` | `FF_ENABLE_PYDANTIC_AI_RESPONSES` | Use Pydantic AI for structured response generation with validation |
| `enable_pydantic_ai_routing` | bool | `True` | `FF_ENABLE_PYDANTIC_AI_ROUTING` | Use Pydantic AI for type-safe routing decisions with confidence scoring |
| `pydantic_ai_confidence_threshold` | float | `0.7` | `FF_PYDANTIC_AI_CONFIDENCE_THRESHOLD` | Minimum confidence score to trust Pydantic AI routing (0.0-1.0) |

## Security

*14 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `default_rate_limit_per_minute` | int | `60` | `FF_DEFAULT_RATE_LIMIT_PER_MINUTE` | Default rate limit for all features (requests per minute per user). Feature-s... |
| `enable_distributed_rate_limiting` | bool | `False` | `FF_ENABLE_DISTRIBUTED_RATE_LIMITING` | Use Redis for distributed rate limiting (required for multi-instance deployme... |
| `enable_encrypted_sessions` | bool | `False` | `FF_ENABLE_ENCRYPTED_SESSIONS` | Enable at-rest encryption for session data. Provides GDPR/HIPAA compliance fo... |
| `enable_frontend_redis_l2_rate_limiting` | bool | `True` | `FF_ENABLE_FRONTEND_REDIS_L2_RATE_LIMITING` | Enable rate limiting for frontend Redis L2 cache API (prevents cache flooding) |
| `enable_input_validation` | bool | `True` | `FF_ENABLE_INPUT_VALIDATION` | Validate and sanitize all user inputs |
| `enable_pii_tokenization` | bool | `True` | `FF_ENABLE_PII_TOKENIZATION` | Enable PII tokenization layer for GDPR/HIPAA compliance. Automatically detect... |
| `enable_rate_limiting` | bool | `True` | `FF_ENABLE_RATE_LIMITING` | Enable rate limiting to prevent abuse |
| `frontend_redis_l2_rate_limit_per_minute` | int | `60` | `FF_FRONTEND_REDIS_L2_RATE_LIMIT_PER_MINUTE` | Maximum frontend cache API requests per minute per user (1-1000) |
| `hallucination_report_rate_limit_per_minute` | int | `10` | `FF_HALLUCINATION_REPORT_RATE_LIMIT_PER_MINUTE` | Maximum hallucination reports per minute per user (1-100). Prevents abuse of ... |
| `max_input_length` | int | `10000` | `FF_MAX_INPUT_LENGTH` | Maximum input length in characters |
| `rate_limit_requests_per_minute` | int | `60` | `FF_RATE_LIMIT_REQUESTS_PER_MINUTE` | Maximum requests per minute per user (API global rate limit) |
| `skills_marketplace_rate_limit` | int | `10` | `FF_SKILLS_MARKETPLACE_RATE_LIMIT` | Rate limit for skills marketplace API requests (requests per second). Prevent... |
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
| `enable_studio_ai` | bool | `False` | `FF_ENABLE_STUDIO_AI` | Enable unified Studio AI orchestration for deep content intelligence (gradual... |

## Thinking Budget

*2 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `default_thinking_level` | str | `"medium"` | `FF_DEFAULT_THINKING_LEVEL` | Default thinking level (low, medium, high, ultra) |
| `enable_thinking_budget` | bool | `True` | `FF_ENABLE_THINKING_BUDGET` | Enable thinking budget management for extended reasoning |

## UI Features

*30 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `enable_ai_suggestions` | bool | `True` | `FF_ENABLE_AI_SUGGESTIONS` | Enable AI-powered suggestions in UI (master toggle for all suggestion features) |
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
| `suggestion_strategy` | str | `"llm"` | `FF_SUGGESTION_STRATEGY` | Suggestion generation strategy: 'llm' (AI-powered, best quality), 'heuristic'... |

## Uncategorized

*49 flags in this category*

| Flag | Type | Default | Environment Variable | Description |
|------|------|---------|---------------------|-------------|
| `context_graph_async_persistence` | bool | `True` | `FF_CONTEXT_GRAPH_ASYNC_PERSISTENCE` | Persist decision traces asynchronously to avoid blocking hot path (FF_CONTEXT... |
| `context_graph_batch_size` | int | `100` | `FF_CONTEXT_GRAPH_BATCH_SIZE` | Batch size for async decision trace persistence (FF_CONTEXT_GRAPH_BATCH_SIZE)... |
| `context_graph_retention_days` | int | `2555` | `FF_CONTEXT_GRAPH_RETENTION_DAYS` | Retention period for decision traces in days (FF_CONTEXT_GRAPH_RETENTION_DAYS... |
| `context_graph_sampling_rate` | float | `1.0` | `FF_CONTEXT_GRAPH_SAMPLING_RATE` | Sampling rate for decision trace capture (FF_CONTEXT_GRAPH_SAMPLING_RATE). 1.... |
| `default_critique_rounds` | int | `1` | `FF_DEFAULT_CRITIQUE_ROUNDS` | Default number of critique rounds for plan refinement (0-3). Higher values im... |
| `enable_ai_quality_metrics` | bool | `True` | `FF_ENABLE_AI_QUALITY_METRICS` | Enable AI Quality Metrics card in Admin Dashboard. Shows hallucination report... |
| `enable_capability_resolution` | bool | `False` | `FF_ENABLE_CAPABILITY_RESOLUTION` | Enable hierarchical capability resolution via CapabilityProvider. Master flag... |
| `enable_context_graph` | bool | `False` | `FF_ENABLE_CONTEXT_GRAPH` | Enable context graph decision trace capture (FF_ENABLE_CONTEXT_GRAPH). When e... |
| `enable_enhanced_model_selector` | bool | `True` | `FF_ENABLE_ENHANCED_MODEL_SELECTOR` | Enable enhanced model selector UI features: recent models history, search/fil... |
| `enable_enhanced_router_output` | bool | `False` | `FF_ENABLE_ENHANCED_ROUTER_OUTPUT` | Enable enhanced RouterOutput with skills_needed, execution_mode, and routing_... |
| `enable_hallucination_reporting` | bool | `True` | `FF_ENABLE_HALLUCINATION_REPORTING` | Enable hallucination reporting feature in chat UI. Allows users to flag AI re... |
| `enable_hierarchical_capability_provider` | bool | `False` | `FF_ENABLE_HIERARCHICAL_CAPABILITY_PROVIDER` | Master toggle for ADR-0092 Hierarchical Capability Architecture. Enables the ... |
| `enable_hierarchical_orchestrator` | bool | `False` | `FF_ENABLE_HIERARCHICAL_ORCHESTRATOR` | Enable hierarchical orchestration with coordinator-worker pattern. Phase 4 fe... |
| `enable_hitl_undo_rollback` | bool | `False` | `FF_ENABLE_HITL_UNDO_ROLLBACK` | Enable reversible actions with undo/rollback capability. Allows undoing agent... |
| `enable_insights_session_dismissal` | bool | `True` | `FF_ENABLE_INSIGHTS_SESSION_DISMISSAL` | Enable session-based dismissal for CrossInsightsPanel (resets on session chan... |
| `enable_kb_focus` | bool | `True` | `FF_ENABLE_KB_FOCUS` | Enable Knowledge Base focus mode selector in chat input (Perplexity-style). A... |
| `enable_mobile_drawer` | bool | `True` | `FF_ENABLE_MOBILE_DRAWER` | Enable mobile drawer navigation for small screens |
| `enable_model_selector_in_shell` | bool | `False` | `FF_ENABLE_MODEL_SELECTOR_IN_SHELL` | Enable model selector in StudioShell chat input. When enabled, shows model se... |
| `enable_multi_pattern_execution` | bool | `False` | `FF_ENABLE_MULTI_PATTERN_EXECUTION` | Enable multiple execution patterns (ReACT, programmatic, orchestrator). Allow... |
| `enable_panel_zoom` | bool | `True` | `FF_ENABLE_PANEL_ZOOM` | Enable panel zoom/maximize feature for full-width panel views |
| `enable_plan_cache` | bool | `True` | `FF_ENABLE_PLAN_CACHE` | Enable Redis caching for execution plans. Improves performance by caching pla... |
| `enable_plan_search` | bool | `False` | `FF_ENABLE_PLAN_SEARCH` | Enable semantic template search for execution plans using vector embeddings. ... |
| `enable_plan_templates` | bool | `False` | `FF_ENABLE_PLAN_TEMPLATES` | Enable template suggestion features for execution plans. Uses LLM to suggest ... |
| `enable_precedent_search` | bool | `False` | `FF_ENABLE_PRECEDENT_SEARCH` | Enable semantic precedent search in Qdrant (FF_ENABLE_PRECEDENT_SEARCH). Allo... |
| `enable_progressive_context_discovery` | bool | `False` | `FF_ENABLE_PROGRESSIVE_CONTEXT_DISCOVERY` | Use progressive discovery for complex multi-entity queries. When enabled, com... |
| `enable_progressive_skill_loading` | bool | `False` | `FF_ENABLE_PROGRESSIVE_SKILL_LOADING` | Enable 4-stage progressive skill loading for token efficiency. Loads skills p... |
| `enable_rich_text_chat_input` | bool | `True` | `FF_ENABLE_RICH_TEXT_CHAT_INPUT` | Use RichTextInput with formatting toolbar (bold, italic, code, mentions) in c... |
| `enable_router_agent` | bool | `False` | `FF_ENABLE_ROUTER_AGENT` | Enable RouterAgent for intelligent task classification and routing. Phase 3 f... |
| `enable_semantic_memory_search` | bool | `False` | `FF_ENABLE_SEMANTIC_MEMORY_SEARCH` | Enable vector-based semantic memory search. Uses embeddings to find relevant ... |
| `enable_semantic_skill_search` | bool | `False` | `FF_ENABLE_SEMANTIC_SKILL_SEARCH` | Enable vector-based semantic skill discovery. Uses embeddings to find relevan... |
| `enable_semantic_tool_search` | bool | `False` | `FF_ENABLE_SEMANTIC_TOOL_SEARCH` | Enable vector-based semantic tool discovery. Uses embeddings to find relevant... |
| `enable_streaming_metrics` | bool | `True` | `FF_ENABLE_STREAMING_METRICS` | Enable Prometheus metrics for LLM streaming operations (TTFC, inter-chunk lat... |
| `enable_studio_md_loading` | bool | `False` | `FF_ENABLE_STUDIO_MD_LOADING` | Enable STUDIO.md configuration file discovery and parsing. Loads hierarchical... |
| `enable_swarm_orchestrator` | bool | `False` | `FF_ENABLE_SWARM_ORCHESTRATOR` | Enable SwarmOrchestrator for race/cascade/consensus patterns. Phase 4 feature... |
| `enable_token_refresh` | bool | `True` | `FF_ENABLE_TOKEN_REFRESH` | Enable automatic token refresh for Keycloak tokens |
| `enable_url_fetch_in_shell` | bool | `False` | `FF_ENABLE_URL_FETCH_IN_SHELL` | Enable URL content fetching (#url pattern) in StudioShell chat input. When en... |
| `enable_user_capability_selection` | bool | `False` | `FF_ENABLE_USER_CAPABILITY_SELECTION` | Enable user-facing tool and skill selection in chat UI. Allows users to expli... |
| `enable_workflow_from_chat` | bool | `False` | `FF_ENABLE_WORKFLOW_FROM_CHAT` | Enable chat-to-workflow generation feature with versioning and code editor. R... |
| `force_high_risk_review` | bool | `True` | `FF_FORCE_HIGH_RISK_REVIEW` | Force human review for high-risk execution plans. Safety feature - set FF_FOR... |
| `max_thinking_budget` | str | `"medium"` | `FF_MAX_THINKING_BUDGET` | Maximum thinking budget level (none, low, medium, high, ultra). Caps thinking... |
| `multi_agent_strategy` | str | `"orchestrator"` | `FF_MULTI_AGENT_STRATEGY` | Multi-agent coordination strategy: 'orchestrator' (hierarchical with coordina... |
| `orchestration_compat_mode` | bool | `True` | `FF_ORCHESTRATION_COMPAT_MODE` | Enable compatibility mode for backward compatibility. When True, uses legacy ... |
| `precedent_search_max_results` | int | `10` | `FF_PRECEDENT_SEARCH_MAX_RESULTS` | Maximum precedent search results to return (FF_PRECEDENT_SEARCH_MAX_RESULTS).... |
| `precedent_search_min_score` | float | `0.5` | `FF_PRECEDENT_SEARCH_MIN_SCORE` | Minimum similarity score for precedent search results (FF_PRECEDENT_SEARCH_MI... |
| `show_chat_avatars` | bool | `True` | `FF_SHOW_CHAT_AVATARS` | Show user and assistant avatars in chat messages (Sprint 3.1 feature) |
| `skills_marketplace_max_concurrent_fetches` | int | `5` | `FF_SKILLS_MARKETPLACE_MAX_CONCURRENT_FETCHES` | Maximum number of concurrent skill metadata fetches. Limits parallel API call... |
| `skills_marketplace_retry_base_delay` | float | `0.1` | `FF_SKILLS_MARKETPLACE_RETRY_BASE_DELAY` | Base delay in seconds for exponential backoff on marketplace retries. Actual ... |
| `skills_marketplace_retry_max_attempts` | int | `3` | `FF_SKILLS_MARKETPLACE_RETRY_MAX_ATTEMPTS` | Maximum retry attempts for transient marketplace API errors (5xx). Uses expon... |
| `use_model_registry_for_frontend` | bool | `True` | `FF_USE_MODEL_REGISTRY_FOR_FRONTEND` | Use ModelRegistry.get_frontend_models() instead of hardcoded AVAILABLE_MODELS... |

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
```
