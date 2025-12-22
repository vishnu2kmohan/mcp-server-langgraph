# 81. Handoff Pattern for Multi-Agent Systems

Date: 2025-12-21

## Status

Proposed

## Category

Architecture & Multi-Agent

## Context

A multi-framework audit comparing our multi-agent orchestration against Google ADK and OpenAI Agents SDK identified the **Handoff** pattern as a valuable addition to our existing Subagent pattern.

**Current Multi-Agent Pattern (Subagent)**:

Our Subagent pattern (ADR-0078) provides parallel task execution with coordinator control:

```
Coordinator Agent
       │
       ├──────────────────────────────┐
       │                              │
       ▼                              ▼
   Subagent A                    Subagent B
   (separate context)            (separate context)
       │                              │
       └──────────────────────────────┘
                    │
                    ▼
            Coordinator synthesizes results
```

**Characteristics**:
- Caller retains control
- Subagents have isolated context
- Results return to caller for synthesis
- Parallel execution possible
- Best for: decomposed tasks, parallel work

**Handoff Pattern (OpenAI/ADK)**:

The Handoff pattern provides sequential control transfer with context sharing:

```
Agent A (Triage)
       │
       │ handoff_to_agent_b(context)
       │
       ▼
Agent B (Specialist)
       │
       │ (continues conversation with user)
       │
       ▼
Response to User (from Agent B)
```

**Characteristics**:
- Control **transfers** to new agent
- Full conversation history shared (filterable)
- Caller loses control after handoff
- Sequential specialization
- Best for: escalation, routing, domain handoffs

**Framework Comparison**:

| Feature | OpenAI SDK | Google ADK | Ours |
|---------|------------|------------|------|
| Subagent (parallel) | `as_tool()` | Tool-based | `Subagent` class |
| **Handoff (transfer)** | `Handoff` | `transfer_to_agent` | **Gap** |
| Sequential | Manual | `SequentialAgent` | Manual |
| Parallel | Manual | `ParallelAgent` | `BaseOrchestrator` |
| Loop | Manual | `LoopAgent` | Manual |

**Why Handoff Matters**:

| Use Case | With Subagent Only | With Handoff |
|----------|-------------------|--------------|
| Customer Support Routing | Awkward - user talks to coordinator | Natural - user continues with specialist |
| Escalation Flows | Results return to basic agent | Expert takes over completely |
| Domain Specialization | Coordinator must relay answers | Specialist answers directly |
| Context-Heavy Workflows | Context lost between agents | Context preserved across handoffs |

## Decision

Implement the Handoff pattern as a **complement** to (not replacement for) the Subagent pattern.

### Core Components

#### 1. Handoff Class

**File**: `src/mcp_server_langgraph/agents/handoff.py`

```python
from dataclasses import dataclass, field
from typing import Any, Callable
from langchain_core.tools import BaseTool
from langchain_core.messages import BaseMessage

@dataclass
class HandoffContext:
    """Context passed during a handoff."""
    from_agent: str
    to_agent: str
    messages: list[BaseMessage]
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class HandoffResult:
    """Result of a handoff execution."""
    success: bool
    agent: str
    response: str | None = None
    error: str | None = None
    messages_transferred: int = 0

class Handoff:
    """Transfer control to another agent with optional context filtering.

    Unlike Subagent (parallel, results return to caller), Handoff:
    - Transfers control completely to target agent
    - Shares conversation history (optionally filtered)
    - Target agent responds directly to user
    """

    def __init__(
        self,
        target_agent: str,
        description: str | None = None,
        context_filter: "ContextFilter | None" = None,
        input_data: dict[str, Any] | None = None,
        on_handoff: Callable[[HandoffContext], None] | None = None,
    ):
        self.target_agent = target_agent
        self.description = description or f"Hand off to {target_agent}"
        self.context_filter = context_filter
        self.input_data = input_data or {}
        self.on_handoff = on_handoff

    def as_tool(self) -> BaseTool:
        """Convert handoff to a tool the LLM can call."""
        return HandoffTool(
            name=f"transfer_to_{self.target_agent}",
            description=self.description,
            handoff=self,
        )

    async def execute(
        self,
        from_agent: str,
        messages: list[BaseMessage],
        context: dict[str, Any],
    ) -> HandoffResult:
        """Execute the handoff."""
        # Filter context if filter provided
        filtered_messages = messages
        if self.context_filter:
            filtered_messages = self.context_filter.filter(messages)

        # Create handoff context
        handoff_context = HandoffContext(
            from_agent=from_agent,
            to_agent=self.target_agent,
            messages=filtered_messages,
            metadata={**context, **self.input_data},
        )

        # Call on_handoff callback if provided
        if self.on_handoff:
            self.on_handoff(handoff_context)

        # Signal handoff (actual execution happens in orchestrator)
        return HandoffResult(
            success=True,
            agent=self.target_agent,
            messages_transferred=len(filtered_messages),
        )
```

#### 2. Context Filters

**File**: `src/mcp_server_langgraph/agents/context_filter.py`

```python
from abc import ABC, abstractmethod
from typing import Any
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage

class ContextFilter(ABC):
    """Abstract base for context filters."""

    @abstractmethod
    def filter(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        """Filter messages before handoff."""
        ...

class KeepAllFilter(ContextFilter):
    """Keep all messages (default behavior)."""

    def filter(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        return messages

class KeepLastNFilter(ContextFilter):
    """Keep only the last N messages."""

    def __init__(self, n: int):
        self.n = n

    def filter(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        return messages[-self.n:] if len(messages) > self.n else messages

class RemoveToolCallsFilter(ContextFilter):
    """Remove all tool call messages."""

    def filter(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        return [
            m for m in messages
            if not isinstance(m, ToolMessage)
            and not (isinstance(m, AIMessage) and m.tool_calls)
        ]

class SummarizeHistoryFilter(ContextFilter):
    """Summarize conversation history to reduce context size."""

    def __init__(self, summarizer: "ConversationSummarizer"):
        self.summarizer = summarizer

    def filter(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        if len(messages) <= 3:
            return messages
        # Summarize all but last 3 messages
        summary = self.summarizer.summarize(messages[:-3])
        return [summary] + messages[-3:]

class CompositeFilter(ContextFilter):
    """Chain multiple filters together."""

    def __init__(self, filters: list[ContextFilter]):
        self.filters = filters

    def filter(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        result = messages
        for f in self.filters:
            result = f.filter(result)
        return result
```

#### 3. Handoff Tool

**File**: `src/mcp_server_langgraph/agents/handoff.py` (continued)

```python
from langchain_core.tools import BaseTool
from pydantic import Field

class HandoffTool(BaseTool):
    """Tool wrapper for handoff, callable by LLM."""

    name: str
    description: str
    handoff: Handoff = Field(exclude=True)

    class Config:
        arbitrary_types_allowed = True

    async def _arun(
        self,
        reason: str = "",
        additional_context: str = "",
    ) -> str:
        """Execute handoff (signals to orchestrator)."""
        # The actual handoff is handled by the orchestrator
        # This tool just signals the intent
        return f"HANDOFF:{self.handoff.target_agent}:{reason}"

    def _run(self, **kwargs) -> str:
        """Sync version (not recommended)."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._arun(**kwargs)
        )
```

#### 4. Orchestrator Integration

**File**: `src/mcp_server_langgraph/agents/orchestrator.py` (extension)

```python
class Orchestrator:
    """Extended with handoff support."""

    def __init__(
        self,
        # ... existing params ...
        handoffs: dict[str, Handoff] | None = None,
    ):
        self.handoffs = handoffs or {}

    async def run(
        self,
        messages: list[BaseMessage],
        agent: str | None = None,
    ) -> OrchestratorResult:
        """Run with handoff detection."""
        current_agent = agent or self.default_agent

        while True:
            # Execute current agent
            result = await self._execute_agent(current_agent, messages)

            # Check for handoff signal
            handoff = self._detect_handoff(result)
            if handoff:
                # Execute handoff
                handoff_result = await handoff.execute(
                    from_agent=current_agent,
                    messages=messages,
                    context=result.context,
                )

                if handoff_result.success:
                    # Transfer to new agent
                    current_agent = handoff.target_agent
                    messages = self._apply_context_filter(
                        messages, handoff.context_filter
                    )
                    continue  # Continue with new agent

            # No handoff, return result
            return result

    def _detect_handoff(self, result: AgentResult) -> Handoff | None:
        """Detect if agent signaled a handoff."""
        if result.tool_calls:
            for call in result.tool_calls:
                if call.name.startswith("transfer_to_"):
                    agent_name = call.name.replace("transfer_to_", "")
                    return self.handoffs.get(agent_name)
        return None
```

### Handoff vs Subagent Usage Guide

| Aspect | Use Subagent | Use Handoff |
|--------|--------------|-------------|
| Task Type | Decomposed parallel work | Sequential specialization |
| Control Flow | Caller retains control | Caller transfers control |
| Context | Isolated per subagent | Shared/filtered history |
| Return | Results to coordinator | Response to user |
| Best For | "Do these 3 things" | "You handle this" |

**Example - Customer Support**:

```python
# Using Subagent (awkward for this case)
result = await orchestrator.spawn_subagent(
    agent="refund_specialist",
    task="Handle refund request",
    context={"user_id": "123"},
)
# Coordinator must relay answer to user

# Using Handoff (natural for this case)
handoff = Handoff(
    target_agent="refund_specialist",
    description="Transfer to refund specialist for refund processing",
    context_filter=KeepLastNFilter(10),  # Keep recent context
)
# Refund specialist continues conversation directly with user
```

**Example - Research Task**:

```python
# Using Subagent (natural for this case)
results = await orchestrator.run_parallel([
    SubagentTask(agent="web_searcher", task="Find recent news"),
    SubagentTask(agent="doc_searcher", task="Search internal docs"),
    SubagentTask(agent="db_searcher", task="Query database"),
])
summary = coordinator.synthesize(results)
# Coordinator combines results

# Using Handoff (awkward for this case)
# Would need sequential handoffs, losing synthesis capability
```

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Multi-Agent Patterns                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Pattern Selection                             │   │
│  │                                                                  │   │
│  │     Parallel Tasks?  ────────────────▶  Use Subagent            │   │
│  │            │                                                     │   │
│  │            ▼                                                     │   │
│  │     Need Synthesis? ─────────────────▶  Use Subagent            │   │
│  │            │                                                     │   │
│  │            ▼                                                     │   │
│  │     Control Transfer? ───────────────▶  Use Handoff             │   │
│  │            │                                                     │   │
│  │            ▼                                                     │   │
│  │     Escalation/Routing? ─────────────▶  Use Handoff             │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌───────────────────────┐        ┌───────────────────────────────┐   │
│  │     Subagent Pattern  │        │      Handoff Pattern          │   │
│  │                       │        │                               │   │
│  │   Coordinator         │        │   Agent A                     │   │
│  │       │               │        │       │                       │   │
│  │   ┌───┼───┐           │        │       │ handoff               │   │
│  │   ▼   ▼   ▼           │        │       ▼                       │   │
│  │   A   B   C           │        │   Agent B ──▶ User            │   │
│  │   │   │   │           │        │                               │   │
│  │   └───┼───┘           │        │   (control transferred)       │   │
│  │       ▼               │        │                               │   │
│  │   Synthesize          │        │                               │   │
│  │       │               │        │                               │   │
│  │       ▼               │        │                               │   │
│  │   Response            │        │                               │   │
│  └───────────────────────┘        └───────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Feature Flag

| Flag | Default | Description |
|------|---------|-------------|
| `enable_handoff_pattern` | False | Enable agent-to-agent handoffs |

### Configuration

```python
# Handoff configuration
HANDOFF_MAX_CHAIN_DEPTH = 5  # Prevent infinite handoff chains
HANDOFF_TIMEOUT_SECONDS = 300  # Max time for handoff chain
HANDOFF_LOG_CONTEXT = True  # Log context transfers for debugging

# Example agent configuration with handoffs
agent_config = AgentConfig(
    handoffs={
        "billing_specialist": Handoff(
            target_agent="billing_specialist",
            description="Transfer to billing for payment issues",
            context_filter=RemoveToolCallsFilter(),
        ),
        "technical_support": Handoff(
            target_agent="technical_support",
            description="Transfer to tech support for technical issues",
            context_filter=KeepLastNFilter(20),
        ),
    }
)
```

## Consequences

### Positive

1. **Natural Escalation**: Clean control transfer for routing scenarios
2. **Context Preservation**: Conversation history flows to specialist
3. **User Experience**: Users talk to the right agent directly
4. **Pattern Completeness**: Matches OpenAI/ADK multi-agent capabilities
5. **Composable**: Works alongside existing Subagent pattern

### Negative

1. **Complexity**: Two multi-agent patterns to choose from
2. **Debugging**: Control flow harder to trace across handoffs
3. **Potential Loops**: Need safeguards against handoff cycles

### Neutral

1. **Feature Flagged**: Disabled by default, opt-in
2. **LLM Agnostic**: Works with any LLM via LiteLLM
3. **Backward Compatible**: Subagent pattern unchanged

## Implementation Plan

### TDD Test Cases (Write FIRST)

**`tests/unit/agents/test_handoff.py`**:
```python
async def test_handoff_transfers_to_target_agent()
async def test_handoff_preserves_messages()
async def test_handoff_with_context_filter()
async def test_handoff_calls_on_handoff_callback()
async def test_handoff_as_tool_returns_tool()
async def test_handoff_tool_signals_transfer()
def test_handoff_result_contains_agent_name()
```

**`tests/unit/agents/test_context_filter.py`**:
```python
def test_keep_all_filter_returns_all()
def test_keep_last_n_filter_truncates()
def test_remove_tool_calls_filter_removes_tools()
def test_summarize_history_filter_summarizes()
def test_composite_filter_chains_filters()
def test_keep_last_n_handles_short_history()
```

**`tests/unit/agents/test_orchestrator_handoff.py`**:
```python
async def test_orchestrator_detects_handoff_signal()
async def test_orchestrator_executes_handoff()
async def test_orchestrator_continues_with_new_agent()
async def test_orchestrator_applies_context_filter()
async def test_orchestrator_limits_handoff_depth()
async def test_orchestrator_handles_handoff_failure()
```

### Files to Create

```
src/mcp_server_langgraph/agents/
├── handoff.py               # NEW: Handoff class, HandoffTool
└── context_filter.py        # NEW: Context filters

tests/unit/agents/
├── test_handoff.py          # NEW
├── test_context_filter.py   # NEW
└── test_orchestrator_handoff.py  # NEW
```

### Files to Modify

```
src/mcp_server_langgraph/agents/__init__.py     # Export Handoff
src/mcp_server_langgraph/agents/orchestrator.py # Handoff integration
src/mcp_server_langgraph/core/feature_flags.py  # Add feature flag
```

## Related ADRs

- ADR-0077: Claude Agent SDK Integration (hook integration for handoffs)
- ADR-0078: Multi-Agent Orchestrator Patterns (Subagent pattern)
- ADR-0080: LLM-Level Callback System (hooks during handoffs)
- ADR-0082: MCP Client Capabilities (tools available during handoffs)

## References

- [OpenAI Agents SDK - Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [Google ADK - Agent-to-Agent Communication](https://google.github.io/adk-docs/a2a/)
- [LangGraph - Agent Handoffs](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
