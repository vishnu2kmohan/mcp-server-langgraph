# 77. Claude Agent SDK Integration Pattern

Date: 2025-12-21

## Status

Accepted

## Category

Architecture & Integration

## Context

The Claude Agent SDK provides patterns for building AI agents with advanced capabilities like hooks, interrupts, file checkpointing, and structured output validation. While mcp-server-langgraph already has excellent multi-provider LLM support via LiteLLM and sophisticated multi-agent orchestration via LangGraph, adopting select SDK patterns can improve developer experience and enable new capabilities.

**Key SDK Features Analyzed**:

| SDK Feature | Our Status | Recommendation |
|-------------|------------|----------------|
| Tool Execution | LangChain `@tool` | Keep LangGraph (LLM agnostic) |
| Hook System | Not implemented | **Adopt SDK pattern** |
| Interrupt | Not implemented | **Adopt SDK pattern** |
| File Checkpoint | Not implemented | **Adopt SDK pattern** |
| Structured Output | Pydantic only | **Add JSON Schema layer** |
| `can_use_tool` | OpenFGA only | **Add callback layer** |
| `AgentDefinition` | Complex patterns | **Add simple adapter** |
| State Checkpointing | Redis/MemorySaver | Keep LangGraph (superior) |
| Multi-Agent | Rich patterns | Keep LangGraph (more powerful) |
| Resilience | ADR-0026 patterns | Keep existing (production-grade) |
| Observability | OpenTelemetry | Keep existing (enterprise-grade) |
| Auth/AuthZ | Keycloak + OpenFGA | Keep existing (fine-grained) |

**Goals**:
1. Cherry-pick high-value SDK patterns without disrupting existing infrastructure
2. Maintain LLM-agnostic architecture (LiteLLM + LangChain)
3. Gate new features behind feature flags for gradual rollout
4. Follow TDD workflow for all implementations

## Decision

Implement a **side-by-side integration** that adopts valuable SDK patterns while preserving existing strengths.

### Adopted SDK Patterns

#### 1. Hook System (Phase 1)

**Implementation**: `src/mcp_server_langgraph/sdk/hooks.py`

```python
# Hook protocol following SDK pattern
@dataclass
class HookContext:
    tool_name: str
    tool_input: dict[str, Any]
    session_id: str | None
    user_id: str | None

@dataclass
class HookResult:
    behavior: Literal["allow", "deny", "modify"]
    message: str | None = None
    updated_input: dict[str, Any] | None = None

# Hook types
PreToolUseHook = Callable[[HookContext], Awaitable[HookResult]]
PostToolUseHook = Callable[[HookContext, Any], Awaitable[None]]
```

**Feature Flag**: `enable_sdk_hooks` (default: True)

**Integration Point**: `src/mcp_server_langgraph/mcp/handlers/base.py`

#### 2. Interrupt Capability (Phase 2)

**Implementation**: `src/mcp_server_langgraph/core/interrupt.py`

```python
class InterruptController:
    """Thread-safe interrupt signaling for agent operations."""

    async def signal_interrupt(self, session_id: str) -> bool: ...
    async def check_interrupted(self, session_id: str) -> bool: ...
    async def clear_interrupt(self, session_id: str) -> None: ...
```

**Feature Flag**: `enable_sdk_interrupt` (default: True)

**Integration Point**: `src/mcp_server_langgraph/core/agent.py`

#### 3. File Checkpointing (Phase 3)

**Implementation**:
- `src/mcp_server_langgraph/core/file_journal.py`
- `src/mcp_server_langgraph/core/file_rewind.py`

```python
class FileJournal:
    """Track file operations for rollback."""

    async def checkpoint(self, message_id: str) -> str: ...
    async def record_change(self, file_path: str, operation: str, content_before: bytes) -> None: ...
    async def rewind_to(self, checkpoint_id: str) -> list[str]: ...
```

**Feature Flag**: `enable_sdk_file_checkpointing` (default: False - experimental)

**Integration Point**: `src/mcp_server_langgraph/mcp/handlers/execution.py`

#### 4. Structured Output Validation (Phase 4)

**Implementation**:
- `src/mcp_server_langgraph/core/output_format.py`
- `src/mcp_server_langgraph/core/schema_validator.py`

```python
class OutputFormat(TypedDict):
    type: Literal["json_schema"]
    schema: dict[str, Any]

class OutputValidator:
    """Validate agent output against JSON Schema."""

    def validate(self, output: Any, format: OutputFormat) -> ValidationResult: ...
```

**Feature Flag**: `enable_sdk_structured_output` (default: True)

**Integration Point**: `src/mcp_server_langgraph/mcp/models.py`

#### 5. can_use_tool Callback (Phase 5)

**Implementation**: `src/mcp_server_langgraph/auth/middleware.py`

```python
# Type alias for callback
CanUseToolCallback = Callable[
    [str, dict[str, Any], dict[str, Any]],
    Coroutine[Any, Any, dict[str, Any]],
]

class AuthMiddleware:
    def __init__(
        self,
        # ... existing params ...
        can_use_tool: CanUseToolCallback | None = None,
    ):
        self._can_use_tool_callback = can_use_tool

    async def can_use_tool(
        self,
        tool: str,
        input: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Dynamic tool permission check (SDK pattern)."""
        ...
```

**Feature Flag**: `enable_sdk_can_use_tool` (default: False - experimental)

**Integration Point**: Layered on top of OpenFGA for dynamic decisions

#### 6. AgentDefinition Pattern (Phase 6)

**Implementation**: `src/mcp_server_langgraph/agents/definition.py`

```python
@dataclass
class AgentDefinition:
    """Declarative agent definition following SDK pattern."""

    name: str
    description: str
    prompt: str
    tools: list[str] | None = None
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None

    def to_subagent_config(self, task_id: str) -> dict[str, Any]: ...
```

**Orchestrator Integration**:

```python
class Orchestrator:
    async def execute_definition(
        self,
        agent: AgentDefinition,
        task_id: str,
    ) -> SubagentResult:
        """Execute an AgentDefinition as a subagent."""
        ...
```

**Feature Flag**: `enable_sdk_agent_definition` (default: False - experimental)

### Feature Flags Summary

| Flag Name | Default | Status |
|-----------|---------|--------|
| `enable_sdk_hooks` | True | Production ready |
| `enable_sdk_interrupt` | True | Production ready |
| `enable_sdk_file_checkpointing` | False | Experimental |
| `enable_sdk_structured_output` | True | Production ready |
| `enable_sdk_can_use_tool` | False | Experimental |
| `enable_sdk_agent_definition` | False | Experimental |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MCP Server Layer                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                         SDK Patterns                              │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │   Hooks     │  │  Interrupt  │  │   File Checkpointing    │   │ │
│  │  │ Pre/Post    │  │  Controller │  │   Journal + Rewind      │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  │                                                                   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │  Structured │  │ can_use_tool│  │   AgentDefinition       │   │ │
│  │  │  Output     │  │  Callback   │  │   Registry + Adapter    │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    Existing Infrastructure                        │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  LiteLLM     │  LangGraph  │  OpenFGA   │  Redis    │  OTel      │ │
│  │  Multi-LLM   │  Agent      │  AuthZ     │  State    │  Traces    │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Consequences

### Positive

1. **Developer Experience**: Simpler patterns for common agent tasks
2. **Flexibility**: Dynamic tool permissions via callbacks
3. **Safety**: File checkpointing enables rollback for risky operations
4. **Consistency**: Hook system provides uniform audit/validation layer
5. **Graceful Cancellation**: Interrupt capability improves UX for long tasks

### Negative

1. **Complexity**: Additional patterns to learn and maintain
2. **Feature Flags**: Multiple experimental features require careful rollout
3. **Testing**: More test coverage required for new patterns

### Neutral

1. **LLM Agnostic**: All patterns work with any LLM provider via LiteLLM
2. **Backward Compatible**: Existing code continues to work unchanged
3. **Optional Adoption**: Teams can adopt patterns incrementally

## Implementation Status

| Phase | Component | Tests | Implementation | Status |
|-------|-----------|-------|----------------|--------|
| 1 | Hook System | 24 tests | `sdk/hooks.py` | Complete |
| 2 | Interrupt | 8 tests | `core/interrupt.py` | Complete |
| 3 | File Checkpointing | 6 tests | `core/file_*.py` | Complete |
| 4 | Structured Output | 6 tests | `mcp/models.py` | Complete |
| 5 | can_use_tool | 8 tests | `auth/middleware.py` | Complete |
| 6 | AgentDefinition | 29 tests | `agents/definition.py` | Complete |

**Total SDK Tests**: 143 passing

## Related ADRs

- ADR-0001: LLM Multi-Provider (LiteLLM foundation)
- ADR-0009: Feature Flag System (gating mechanism)
- ADR-0024: Agentic Loop Implementation (agent patterns)
- ADR-0030: Resilience Patterns (production resilience)

## References

- [Claude Agent SDK - Python Reference](https://platform.claude.com/docs/en/agent-sdk/python)
- [Claude Agent SDK - Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [LangChain Tools Guide 2025](https://latenode.com/blog/langchain-tools-complete-guide-2025)
