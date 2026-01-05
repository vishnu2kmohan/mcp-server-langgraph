# ADR-0092: Hierarchical Capability Architecture

| Status | Proposed |
|--------|----------|
| Date | 2026-01-04 |
| Authors | Claude Opus 4.5 |
| Deciders | Architecture Review |
| Consulted | Anthropic Agent Skills Spec, Claude Code Memory Spec |
| Informed | All Contributors |

## Context and Problem Statement

The current agent architecture has a gap between routing recommendations and execution capabilities:

1. **RouterAgent recommends tools** via `tools_needed` field but WorkerAgent doesn't bind them
2. **Skills are flat** - no hierarchical scoping (org → project → team → user)
3. **No STUDIO.md** - unlike CLAUDE.md, no workspace memory integration
4. **Memory is ephemeral** - no cross-session persistence at appropriate scopes

Research into industry standards revealed:
- **CLAUDE.md Memory Hierarchy**: Enterprise Policy → Project Memory → Project Rules → User Memory
- **Anthropic Agent Skills**: Progressive disclosure (metadata → instructions → referenced files)
- **Google ADK Context Architecture**: Working Context → Session → Memory → Artifacts

### Problem Statement

How do we enable **all agents** to be **tool-aware** and **skill-aware** via **composition** (not inheritance), with **hierarchical scoping** for enterprise, organization, project, team, user, session, and task contexts?

## Decision Drivers

1. **Composition over Inheritance**: Enhance existing agents, don't create new subclasses
2. **Anthropic Compatibility**: Align with CLAUDE.md and Agent Skills specifications
3. **Enterprise Scoping**: Support org → project → team → user hierarchies
4. **Progressive Disclosure**: Load context hierarchically (metadata first, details on demand)
5. **User Control**: Allow users to select/override tools alongside router suggestions
6. **Minimal Disruption**: Existing agents continue working without breaking changes

## Decision

Implement an 8-layer Hierarchical Capability Architecture with composition-based capability injection.

### 1. Scope Hierarchy (7 Levels)

```
┌─────────────────────────────────────────────────────────────┐
│                    ENTERPRISE                                │
│  /etc/studio/STUDIO.md (policy, compliance, guardrails)     │
├─────────────────────────────────────────────────────────────┤
│                    ORGANIZATION                              │
│  .studio/orgs/{org_id}/STUDIO.md (org defaults, cost limits)│
├─────────────────────────────────────────────────────────────┤
│                    PROJECT                                   │
│  ./STUDIO.md (project skills, coding standards)              │
├─────────────────────────────────────────────────────────────┤
│                    TEAM                                      │
│  .studio/teams/{team_id}/STUDIO.md (team preferences)        │
├─────────────────────────────────────────────────────────────┤
│                    USER                                      │
│  ~/.studio/STUDIO.md (personal preferences, API keys)        │
├─────────────────────────────────────────────────────────────┤
│                    SESSION                                   │
│  In-memory (conversation history, working context)           │
├─────────────────────────────────────────────────────────────┤
│                    TASK                                      │
│  Ephemeral (router output, current tool bindings)            │
└─────────────────────────────────────────────────────────────┘
```

**Precedence**: Lower scopes override higher scopes (Task > Session > User > Team > Project > Org > Enterprise)

### 2. CapabilityProvider Protocol

Agents receive capability context without subclassing via composition:

```python
class CapabilityProvider(Protocol):
    """Protocol for providing tools and skills to agents."""

    async def get_tools(
        self,
        scope: CapabilityScope,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> list[Tool]: ...

    async def get_skills(
        self,
        scope: CapabilityScope,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> list[Skill]: ...

    async def get_memory(
        self,
        scope: CapabilityScope,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> MemoryContext: ...
```

### 3. STUDIO.md Specification

Compatible with CLAUDE.md format (YAML frontmatter + Markdown):

```yaml
---
name: my-project
description: Project configuration for MCP Server LangGraph
version: "1.0.0"

tools:
  enabled:
    - web_search
    - code_execution
  disabled:
    - shell_access

skills:
  enabled:
    - "@anthropic/web-research"
    - "@internal/code-review"

memory:
  inherit: true
  imports:
    - "@project/coding-standards.md"
---

# Project Instructions
These instructions apply to all agents working in this project context.
```

## Consequences

### Positive

1. **All agents become capability-aware** without subclassing
2. **Enterprise governance** via STUDIO.md at /etc/studio/
3. **User control** over tool/skill selection alongside router suggestions
4. **Progressive disclosure** minimizes context token usage
5. **CLAUDE.md compatibility** for existing Claude Code users
6. **Backward compatible** - existing agents work without changes

### Negative

1. **Complexity increase** with 7 scope levels
2. **Discovery overhead** for recursive STUDIO.md traversal
3. **Cache invalidation** challenges across scope changes
4. **Testing surface** increases significantly

### Mitigations

1. **Scope caching**: Cache resolved capabilities with scope-key TTL
2. **Lazy loading**: Only load STUDIO.md when first accessed at scope
3. **Validation hooks**: Pre-commit validation for STUDIO.md format
4. **Observability**: Trace capability resolution for debugging

## Related ADRs

- **ADR-0090**: Agent Orchestration Architecture (RouterAgent, WorkerAgent)
- **ADR-0089**: Prompt Architecture Centralization
- **ADR-0088**: Frontend Hook Selection Guidance (WebSocket patterns)

## References

- [Anthropic Agent Skills Specification](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Code Memory Hierarchy](https://code.claude.com/docs/en/memory)
- [Google ADK Context Architecture](https://developers.googleblog.com/en/building-ai-agents-with-google-adk/)
- [LangGraph ReACT Agent](https://langchain-ai.github.io/langgraph/reference/prebuilt/#langgraph.prebuilt.create_react_agent)
