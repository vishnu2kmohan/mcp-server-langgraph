# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting significant architectural decisions made in this project.

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences.

## ADR Format

Each ADR follows this structure:

```markdown
# [Number]. [Title]

Date: YYYY-MM-DD

## Status

[Proposed | Accepted | Deprecated | Superseded]

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive Consequences

- Benefit 1
- Benefit 2

### Negative Consequences

- Drawback 1
- Drawback 2

### Neutral Consequences

- Trade-off 1

## Alternatives Considered

1. **Alternative 1**
   - Description
   - Why rejected

2. **Alternative 2**
   - Description
   - Why rejected

## References

- Links to relevant documentation
- Related ADRs
```

## Index of ADRs

| Number | Title | Status | Date |
|--------|-------|--------|------|
| [0001](0001-llm-multi-provider.md) | Multi-Provider LLM Support via LiteLLM | Accepted | 2025-10-11 |
| [0002](0002-openfga-authorization.md) | Fine-Grained Authorization with OpenFGA | Accepted | 2025-10-11 |
| [0003](0003-dual-observability.md) | Dual Observability: OpenTelemetry + LangSmith | Accepted | 2025-10-11 |
| [0004](0004-mcp-streamable-http.md) | MCP StreamableHTTP Transport Protocol | Accepted | 2025-10-11 |
| [0005](0005-pydantic-ai-integration.md) | Type-Safe Agent Responses with Pydantic AI | Accepted | 2025-10-11 |

## When to Create an ADR

Create an ADR when you make a significant architectural decision, including:

- Choosing between alternative technologies or frameworks
- Adopting a new pattern or architectural style
- Making changes that affect multiple components
- Decisions with long-term consequences
- Trade-offs that future maintainers should understand

## How to Create an ADR

1. Copy the template above
2. Assign the next sequential number
3. Use a descriptive title (verb-noun format preferred)
4. Fill in all sections thoughtfully
5. Get review from team members
6. Commit to the repository

## ADR Lifecycle

- **Proposed**: Under discussion, not yet decided
- **Accepted**: Decision approved and being implemented
- **Deprecated**: No longer recommended but still in use
- **Superseded**: Replaced by a newer ADR (link to successor)

## Benefits of ADRs

1. **Historical Context**: Future maintainers understand why decisions were made
2. **Onboarding**: New team members learn architectural rationale quickly
3. **Discussion**: Provides structure for architectural discussions
4. **Accountability**: Documents who decided what and when
5. **Learning**: Captures lessons learned from alternatives considered
