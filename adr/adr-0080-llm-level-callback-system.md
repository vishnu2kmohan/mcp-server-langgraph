# 80. LLM-Level Callback System

Date: 2025-12-21

## Status

Proposed

## Category

Architecture & Integration

## Context

A multi-framework audit comparing hook/callback capabilities across Claude Agent SDK, Google ADK, and OpenAI Agents SDK revealed that our current hook system (ADR-0077) lacks LLM-level and session-level interception points.

**Current Hook System (ADR-0077)**:

| Hook | Purpose | Status |
|------|---------|--------|
| `PRE_TOOL_USE` | Before tool execution | Implemented |
| `POST_TOOL_USE` | After tool execution | Implemented |
| `USER_PROMPT_SUBMIT` | User sends prompt | Implemented |
| `STOP` | Agent stops | Implemented |
| `SUBAGENT_STOP` | Subagent stops | Implemented |
| `PRE_COMPACT` | Before context compaction | Implemented |

**Framework Comparison - Callbacks**:

| Callback Type | Claude SDK | Google ADK | OpenAI SDK | Ours | Gap? |
|---------------|------------|------------|------------|------|------|
| Before Tool | `PreToolUse` | `before_tool_callback` | - | `PRE_TOOL_USE` | No |
| After Tool | `PostToolUse` | `after_tool_callback` | - | `POST_TOOL_USE` | No |
| **Before Model** | - | `before_model_callback` | - | - | **YES** |
| **After Model** | - | `after_model_callback` | - | - | **YES** |
| Before Agent | - | `before_agent_callback` | - | - | **YES** |
| After Agent | - | `after_agent_callback` | - | - | **YES** |
| **Session Start** | `SessionStart` | - | - | - | **YES** |
| **Session End** | `SessionEnd` | - | - | - | **YES** |
| User Prompt | `UserPromptSubmit` | - | - | `USER_PROMPT_SUBMIT` | No |
| Stop | `Stop` | - | - | `STOP` | No |
| Input Guard | - | - | Input Guardrails | `pii_detection_hook` | No |
| **Output Guard** | - | - | Output Guardrails | - | **YES** |

**Why LLM-Level Callbacks Matter (Google ADK Pattern)**:

| Callback | Use Cases We Can't Do Today |
|----------|---------------------------|
| `BEFORE_MODEL` | Modify prompts, add few-shot examples, LLM-level caching, pre-LLM content blocking, skip expensive API calls |
| `AFTER_MODEL` | Filter/redact output, add disclaimers, format conversion, output guardrails |
| `SESSION_START` | Session initialization, auth at boundary, workspace setup |
| `SESSION_END` | Cleanup, metrics finalization, session summary |

**Practical Examples**:

| Use Case | Required Callback | Current Workaround |
|----------|-------------------|-------------------|
| Skip LLM for cached queries | `BEFORE_MODEL` | None (always call LLM) |
| Block profanity before LLM | `BEFORE_MODEL` | None (waste tokens) |
| Add "AI-generated" disclaimer | `AFTER_MODEL` | Manual in prompt |
| Request-level cost tracking | `BEFORE/AFTER_MODEL` | Partial via LiteLLM |
| Session initialization | `SESSION_START` | Ad-hoc in handlers |

## Decision

Extend the hook system with LLM-level and session-level callbacks following the Google ADK pattern.

### New Hook Events

**File**: `src/mcp_server_langgraph/core/hooks.py`

```python
from enum import Enum

class HookEvent(Enum):
    # Existing tool-level hooks
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    STOP = "Stop"
    SUBAGENT_STOP = "SubagentStop"
    PRE_COMPACT = "PreCompact"

    # NEW: LLM-level hooks (ADK pattern)
    BEFORE_MODEL = "BeforeModel"
    AFTER_MODEL = "AfterModel"

    # NEW: Session-level hooks (Claude SDK pattern)
    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"

    # NEW: Agent-level hooks (ADK pattern)
    BEFORE_AGENT = "BeforeAgent"
    AFTER_AGENT = "AfterAgent"
```

### Hook Data Models

**File**: `src/mcp_server_langgraph/core/llm_hooks.py`

```python
from pydantic import BaseModel
from typing import Any, Literal
from dataclasses import dataclass

class TokenUsage(BaseModel):
    """Token usage from LLM call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0

class LlmRequest(BaseModel):
    """Interceptable LLM request."""
    messages: list[dict[str, Any]]
    model: str
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    config: dict[str, Any] = {}

class LlmResponse(BaseModel):
    """Interceptable LLM response."""
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    usage: TokenUsage
    model: str
    finish_reason: str

@dataclass
class BeforeModelInput:
    """Input for BEFORE_MODEL hook."""
    request: LlmRequest
    session_id: str
    user_id: str | None
    context: dict[str, Any]

@dataclass
class BeforeModelResult:
    """Result from BEFORE_MODEL hook."""
    behavior: Literal["continue", "skip", "modify"]
    modified_request: LlmRequest | None = None
    cached_response: LlmResponse | None = None  # For skip behavior
    message: str | None = None

@dataclass
class AfterModelInput:
    """Input for AFTER_MODEL hook."""
    request: LlmRequest
    response: LlmResponse
    session_id: str
    user_id: str | None
    latency_ms: float
    context: dict[str, Any]

@dataclass
class AfterModelResult:
    """Result from AFTER_MODEL hook."""
    behavior: Literal["allow", "modify", "block"]
    modified_response: LlmResponse | None = None
    message: str | None = None
```

**File**: `src/mcp_server_langgraph/core/session_hooks.py`

```python
from pydantic import BaseModel
from typing import Any
from dataclasses import dataclass

@dataclass
class SessionStartInput:
    """Input for SESSION_START hook."""
    session_id: str
    user_id: str | None
    username: str | None
    roles: list[str]
    metadata: dict[str, Any]

@dataclass
class SessionStartResult:
    """Result from SESSION_START hook."""
    behavior: Literal["allow", "deny"]
    session_config: dict[str, Any] | None = None  # Inject config
    message: str | None = None

@dataclass
class SessionEndInput:
    """Input for SESSION_END hook."""
    session_id: str
    user_id: str | None
    duration_ms: float
    message_count: int
    token_usage: TokenUsage
    metadata: dict[str, Any]

@dataclass
class SessionEndResult:
    """Result from SESSION_END hook."""
    # Primarily for logging/cleanup, no blocking behavior
    summary: str | None = None
```

### LLM Factory Integration

**File**: `src/mcp_server_langgraph/llm/factory.py`

```python
from mcp_server_langgraph.core.hooks import HookEvent
from mcp_server_langgraph.core.llm_hooks import (
    LlmRequest,
    LlmResponse,
    BeforeModelInput,
    BeforeModelResult,
    AfterModelInput,
    AfterModelResult,
)
from mcp_server_langgraph.core.hook_registry import HookDispatcher

class LLMFactory:
    """LLM factory with hook integration."""

    def __init__(
        self,
        hook_dispatcher: HookDispatcher | None = None,
    ):
        self.hook_dispatcher = hook_dispatcher

    async def complete(
        self,
        request: LlmRequest,
        session_id: str,
        user_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> LlmResponse:
        """Execute LLM call with before/after hooks."""
        context = context or {}

        # BEFORE_MODEL hook - can modify request or return cached response
        if self.hook_dispatcher:
            before_input = BeforeModelInput(
                request=request,
                session_id=session_id,
                user_id=user_id,
                context=context,
            )
            before_result: BeforeModelResult = await self.hook_dispatcher.dispatch(
                HookEvent.BEFORE_MODEL,
                "llm",
                before_input,
            )

            if before_result.behavior == "skip":
                # Return cached response, skip LLM call
                return before_result.cached_response

            if before_result.behavior == "modify":
                request = before_result.modified_request or request

        # Execute actual LLM call
        start_time = time.monotonic()
        response = await self._call_llm(request)
        latency_ms = (time.monotonic() - start_time) * 1000

        # AFTER_MODEL hook - can modify or block response
        if self.hook_dispatcher:
            after_input = AfterModelInput(
                request=request,
                response=response,
                session_id=session_id,
                user_id=user_id,
                latency_ms=latency_ms,
                context=context,
            )
            after_result: AfterModelResult = await self.hook_dispatcher.dispatch(
                HookEvent.AFTER_MODEL,
                "llm",
                after_input,
            )

            if after_result.behavior == "block":
                raise LLMOutputBlockedError(after_result.message)

            if after_result.behavior == "modify":
                response = after_result.modified_response or response

        return response
```

### Built-in Hooks

**File**: `src/mcp_server_langgraph/sdk/llm_hooks.py`

```python
"""Built-in LLM-level hooks."""

from mcp_server_langgraph.core.llm_hooks import (
    BeforeModelInput,
    BeforeModelResult,
    AfterModelInput,
    AfterModelResult,
)

async def response_caching_hook(input: BeforeModelInput) -> BeforeModelResult:
    """Check cache for identical requests, skip LLM if found."""
    cache_key = _compute_cache_key(input.request)
    cached = await cache.get(cache_key)
    if cached:
        return BeforeModelResult(behavior="skip", cached_response=cached)
    return BeforeModelResult(behavior="continue")

async def profanity_pre_filter_hook(input: BeforeModelInput) -> BeforeModelResult:
    """Block requests containing profanity before LLM call."""
    if _contains_profanity(input.request.messages):
        return BeforeModelResult(
            behavior="skip",
            cached_response=_blocked_response("Content policy violation"),
        )
    return BeforeModelResult(behavior="continue")

async def disclaimer_injection_hook(input: AfterModelInput) -> AfterModelResult:
    """Add AI-generated disclaimer to responses."""
    modified = input.response.model_copy()
    modified.content = f"[AI Generated] {input.response.content}"
    return AfterModelResult(behavior="modify", modified_response=modified)

async def pii_output_filter_hook(input: AfterModelInput) -> AfterModelResult:
    """Detect and redact PII from LLM outputs."""
    redacted_content = _redact_pii(input.response.content)
    if redacted_content != input.response.content:
        modified = input.response.model_copy()
        modified.content = redacted_content
        return AfterModelResult(behavior="modify", modified_response=modified)
    return AfterModelResult(behavior="allow")

async def output_format_hook(input: AfterModelInput) -> AfterModelResult:
    """Enforce output format requirements."""
    expected_format = input.context.get("output_format")
    if expected_format and not _validate_format(input.response.content, expected_format):
        return AfterModelResult(
            behavior="block",
            message=f"Output does not match expected format: {expected_format}",
        )
    return AfterModelResult(behavior="allow")
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Request Flow                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  User Request                                                           │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SESSION_START Hook                            │   │
│  │  • Auth at boundary                                              │   │
│  │  • Session initialization                                        │   │
│  │  • Inject session config                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BEFORE_AGENT Hook                             │   │
│  │  • Request validation                                            │   │
│  │  • Early exit for invalid requests                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    BEFORE_MODEL Hook                             │   │
│  │  • Prompt modification                                           │   │
│  │  • Response caching (skip LLM)                                   │   │
│  │  • Pre-LLM content blocking                                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    LLM Call (LiteLLM)                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AFTER_MODEL Hook                              │   │
│  │  • Output filtering/redaction                                    │   │
│  │  • Disclaimer injection                                          │   │
│  │  • Format validation                                             │   │
│  │  • Output guardrails                                             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PRE_TOOL_USE / POST_TOOL_USE                  │   │
│  │  (Existing tool-level hooks)                                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AFTER_AGENT Hook                              │   │
│  │  • Response sanitization                                         │   │
│  │  • Final transformation                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SESSION_END Hook                              │   │
│  │  • Cleanup                                                       │   │
│  │  • Metrics finalization                                          │   │
│  │  • Session summary                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│       │                                                                 │
│       ▼                                                                 │
│  Response to User                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `enable_llm_hooks` | False | Enable BEFORE_MODEL and AFTER_MODEL hooks |
| `enable_session_hooks` | False | Enable SESSION_START and SESSION_END hooks |
| `enable_agent_hooks` | False | Enable BEFORE_AGENT and AFTER_AGENT hooks |

### Configuration

```python
# Hook configuration
LLM_HOOK_TIMEOUT_MS = 5000  # Max time for hook execution
LLM_HOOK_CACHE_TTL_SECONDS = 300  # Cache TTL for response caching hook
SESSION_HOOK_TIMEOUT_MS = 3000  # Max time for session hooks

# Hook registration
DEFAULT_LLM_HOOKS = [
    ("BEFORE_MODEL", response_caching_hook, 100),  # Priority 100
    ("AFTER_MODEL", pii_output_filter_hook, 100),
    ("AFTER_MODEL", disclaimer_injection_hook, 200),  # Lower priority
]
```

## Consequences

### Positive

1. **LLM-Level Control**: Modify requests/responses at LLM boundary
2. **Cost Savings**: Skip LLM for cached queries
3. **Content Safety**: Pre-LLM blocking saves tokens
4. **Output Guardrails**: Filter harmful content before delivery
5. **Observability**: Track per-LLM-call metrics
6. **Session Lifecycle**: Clean initialization and cleanup

### Negative

1. **Latency**: Hook execution adds overhead
2. **Complexity**: More interception points to understand
3. **Debugging**: Hooks can modify data in unexpected ways

### Neutral

1. **Feature Flagged**: Disabled by default, opt-in
2. **LLM Agnostic**: Works with any LLM via LiteLLM
3. **Backward Compatible**: Existing hooks unchanged

## Implementation Plan

### TDD Test Cases (Write FIRST)

**`tests/unit/core/test_llm_hooks.py`**:
```python
async def test_before_model_hook_modifies_request()
async def test_before_model_hook_skips_llm_with_cached()
async def test_before_model_hook_continues_normally()
async def test_after_model_hook_modifies_response()
async def test_after_model_hook_blocks_response()
async def test_after_model_hook_allows_response()
async def test_multiple_hooks_execute_in_priority_order()
async def test_hook_timeout_is_enforced()
```

**`tests/unit/core/test_session_hooks.py`**:
```python
async def test_session_start_hook_allows_session()
async def test_session_start_hook_denies_session()
async def test_session_start_hook_injects_config()
async def test_session_end_hook_captures_metrics()
async def test_session_end_hook_generates_summary()
```

**`tests/unit/sdk/test_builtin_llm_hooks.py`**:
```python
async def test_response_caching_hook_cache_hit()
async def test_response_caching_hook_cache_miss()
async def test_profanity_pre_filter_blocks()
async def test_disclaimer_injection_adds_prefix()
async def test_pii_output_filter_redacts()
async def test_output_format_hook_validates()
```

### Files to Create

```
src/mcp_server_langgraph/core/
├── llm_hooks.py             # NEW: LLM hook models
└── session_hooks.py         # NEW: Session hook models

src/mcp_server_langgraph/sdk/
└── llm_hooks.py             # NEW: Built-in LLM hooks

tests/unit/core/
├── test_llm_hooks.py        # NEW
└── test_session_hooks.py    # NEW

tests/unit/sdk/
└── test_builtin_llm_hooks.py  # NEW
```

### Files to Modify

```
src/mcp_server_langgraph/core/hooks.py           # Add new HookEvents
src/mcp_server_langgraph/core/hook_registry.py   # Add dispatch methods
src/mcp_server_langgraph/llm/factory.py          # Hook integration
src/mcp_server_langgraph/core/feature_flags.py   # Add feature flags
```

## Related ADRs

- ADR-0077: Claude Agent SDK Integration (existing hook system)
- ADR-0078: Multi-Agent Orchestrator Patterns (subagent hooks)
- ADR-0079: Multi-Framework Tool Parity (output guardrails integration)
- ADR-0082: MCP Client Capabilities (hook-aware tool execution)

## References

- [Google ADK - Callbacks](https://google.github.io/adk-docs/callbacks/)
- [Google ADK - Types of Callbacks](https://google.github.io/adk-docs/callbacks/types-of-callbacks/)
- [Claude Agent SDK - Hooks](https://platform.claude.com/docs/en/agent-sdk/hooks)
- [OpenAI Agents SDK - Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
