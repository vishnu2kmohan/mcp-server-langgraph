# 9. Feature Flag System for Gradual Rollouts

Date: 2025-10-13

## Status

Accepted

## Category

Infrastructure & Deployment

## Context

Production systems need safe feature deployment mechanisms:
- **Gradual Rollouts**: Enable features for subset of users
- **A/B Testing**: Compare feature variants
- **Emergency Disable**: Turn off problematic features instantly
- **Experimental Features**: Beta test without full deployment
- **Configuration**: Change behavior without code deployment

Hardcoded feature switches create problems:
- Code changes required to enable/disable features
- Cannot toggle features per environment
- No runtime configuration
- Requires redeployment for feature changes

## Decision

Implement environment-based feature flag system using **Pydantic settings with validation**.

### Architecture

```python
class FeatureFlags(BaseSettings):
    # Pydantic AI Features
    enable_pydantic_ai_routing: bool = True
    pydantic_ai_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # LLM Features
    enable_llm_fallback: bool = True
    llm_timeout_seconds: int = Field(default=60, ge=10, le=300)

    # Authorization
    enable_openfga: bool = True
    openfga_strict_mode: bool = False

    # Observability
    enable_langsmith: bool = False
    enable_trace_sampling: bool = False

    # Experimental
    enable_experimental_features: bool = False
    enable_multi_agent_collaboration: bool = False

    model_config = SettingsConfigDict(
        env_prefix="FF_",  # FF_ENABLE_PYDANTIC_AI_ROUTING=false
        env_file=".env",
    )
```

### Usage

**Direct Flag Access:**
```python
from mcp_server_langgraph.core.feature_flags import feature_flags

if feature_flags.enable_pydantic_ai_routing:
    decision = await pydantic_agent.route_message(message)
else:
    decision = keyword_based_routing(message)
```

**Feature-Gated Functions (Recommended):**
```python
from mcp_server_langgraph.core.feature_flags import feature_gated

@feature_gated("enable_multi_agent_orchestration", "Multi-Agent Orchestration")
def decompose_task(self, task: str) -> TaskDecomposition:
    # Only runs if feature is enabled
    ...

@feature_gated("enable_programmatic_tools", "Programmatic Tools")
async def call_tool(self, name: str, args: dict) -> ToolResult:
    # Works with async functions too
    ...
```

### Testing Utilities

**FF_TEST_MODE**: Environment variable that bypasses all feature flag checks when set to `true`.

```bash
# Enable test mode (all feature checks pass)
export FF_TEST_MODE=true
```

```python
# Check if test mode is active
if feature_flags.is_test_mode:
    # All feature checks are bypassed
    pass
```

This enables testing of feature-gated functionality without enabling each flag individually.

## Consequences

### Positive Consequences

- **Safe Rollouts**: Enable features incrementally
- **Environment-Specific**: Different flags per environment
- **Runtime Configuration**: No code changes to toggle features
- **Type Safety**: Pydantic validation prevents invalid values
- **Documentation**: Flags self-document with descriptions

### Negative Consequences

- **Code Complexity**: if/else checks throughout codebase
- **Testing Burden**: Must test with flags on/off
- **Configuration Sprawl**: Many environment variables

## Alternatives Considered

1. **LaunchDarkly**: Third-party service, cost, complexity
2. **Code-Based Toggles**: No runtime config, requires deployment
3. **Database Flags**: Requires database, slower

**Why Rejected**: Environment variables simplest for our needs

## Implementation

90+ feature flags across categories:
- Pydantic AI (3 flags)
- LLM (4 flags)
- Authorization (4 flags)
- Observability (4 flags)
- Performance (4 flags)
- Agent Behavior (3 flags)
- Security (4 flags)
- Experimental (3 flags)
- UI/UX Features (15+ flags)
- AI Features (12+ flags)
- Multi-Agent Orchestration (8+ flags)
- SDK Integration (6 flags)
- Multi-Framework Parity (6 flags)
- HITL (5 flags)
- Tools & Skills (8+ flags)
- Context Management (6+ flags)

### Multi-Framework Parity Flags (ADR-0077/0078/0079)

These flags control features added for parity with Claude Agent SDK, Google ADK, and OpenAI Agents SDK:

| Flag | Default | Description |
|------|---------|-------------|
| `enable_computer_use` | `false` | Computer automation tools (mouse, keyboard, browser) |
| `enable_loop_agent` | `false` | LoopAgent orchestration pattern (Google ADK parity) |
| `enable_session_fork` | `false` | Session forking for conversation branching |
| `enable_llm_hooks` | `true` | LLM-level callbacks (BEFORE_MODEL, AFTER_MODEL) |
| `enable_session_hooks` | `true` | Session lifecycle hooks |
| `enable_handoff_pattern` | `true` | Agent-to-agent handoff |

## References

- Implementation: `src/mcp_server_langgraph/core/feature_flags.py`
- Related ADRs: [ADR-0005](adr-0005-pydantic-ai-integration.md), [ADR-0077](adr-0077-claude-agent-sdk-integration.md), [ADR-0078](adr-0078-multi-agent-orchestrator-patterns.md)
