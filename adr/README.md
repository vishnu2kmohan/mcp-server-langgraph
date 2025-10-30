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
| [0001](adr-0001-llm-multi-provider.md) | Multi-Provider LLM Support via LiteLLM | Accepted | 2025-10-11 |
| [0002](adr-0002-openfga-authorization.md) | Fine-Grained Authorization with OpenFGA | Accepted | 2025-10-11 |
| [0003](adr-0003-dual-observability.md) | Dual Observability: OpenTelemetry + LangSmith | Accepted | 2025-10-11 |
| [0004](adr-0004-mcp-streamable-http.md) | MCP StreamableHTTP Transport Protocol | Accepted | 2025-10-11 |
| [0005](adr-0005-pydantic-ai-integration.md) | Type-Safe Agent Responses with Pydantic AI | Accepted | 2025-10-11 |
| [0006](adr-0006-session-storage-architecture.md) | Pluggable Session Storage Architecture | Accepted | 2025-10-13 |
| [0007](adr-0007-authentication-provider-pattern.md) | Pluggable Authentication Provider Pattern | Accepted | 2025-10-13 |
| [0008](adr-0008-infisical-secrets-management.md) | Infisical for Secrets Management | Accepted | 2025-10-13 |
| [0009](adr-0009-feature-flag-system.md) | Feature Flag System for Gradual Rollouts | Accepted | 2025-10-13 |
| [0010](adr-0010-langgraph-functional-api.md) | LangGraph Functional API over Object-Oriented | Accepted | 2025-10-13 |
| [0011](adr-0011-cookiecutter-template-strategy.md) | Cookiecutter Template for Project Generation | Accepted | 2025-10-13 |
| [0012](adr-0012-compliance-framework-integration.md) | Built-In Compliance Framework (GDPR, SOC 2, HIPAA) | Accepted | 2025-10-13 |
| [0013](adr-0013-multi-deployment-target-strategy.md) | Multi-Deployment Target Strategy | Accepted | 2025-10-13 |
| [0014](adr-0014-pydantic-type-safety.md) | Pydantic Type Safety Strategy | Accepted | 2025-10-13 |
| [0015](adr-0015-memory-checkpointing.md) | Memory Checkpointing for Stateful Agents | Accepted | 2025-10-13 |
| [0016](adr-0016-property-based-testing-strategy.md) | Property-Based Testing with Hypothesis | Accepted | 2025-10-13 |
| [0017](adr-0017-error-handling-strategy.md) | Error Handling Strategy | Accepted | 2025-10-13 |
| [0018](adr-0018-semantic-versioning-strategy.md) | Semantic Versioning Strategy | Accepted | 2025-10-13 |
| [0019](adr-0019-async-first-architecture.md) | Async-First Architecture | Accepted | 2025-10-13 |
| [0020](adr-0020-dual-mcp-transport-protocol.md) | Dual MCP Transport Protocol (STDIO + StreamableHTTP) | Accepted | 2025-10-13 |
| [0021](adr-0021-cicd-pipeline-strategy.md) | CI/CD Pipeline Strategy | Accepted | 2025-10-13 |
| [0022](adr-0022-distributed-conversation-checkpointing.md) | Distributed Conversation Checkpointing with Redis | Accepted | 2025-10-15 |
| [0023](adr-0023-anthropic-tool-design-best-practices.md) | Anthropic Tool Design Best Practices | Accepted | 2025-10-17 |
| [0024](adr-0024-agentic-loop-implementation.md) | Agentic Loop Implementation (Gather-Action-Verify-Repeat) | Accepted | 2025-10-17 |
| [0025](adr-0025-anthropic-best-practices-enhancements.md) | Anthropic Best Practices - Advanced Enhancements | Accepted | 2025-10-17 |
| [0026](adr-0026-lazy-observability-initialization.md) | Lazy Observability Initialization | Accepted | 2025-10-17 |
| [0027](adr-0027-rate-limiting-strategy.md) | Rate Limiting Strategy for API Protection | Accepted | 2025-10-20 |
| [0028](adr-0028-caching-strategy.md) | Multi-Layer Caching Strategy | Accepted | 2025-10-20 |
| [0029](adr-0029-custom-exception-hierarchy.md) | Custom Exception Hierarchy | Accepted | 2025-10-20 |
| [0030](adr-0030-resilience-patterns.md) | Resilience Patterns for Production Systems | Accepted | 2025-10-20 |
| [0031](adr-0031-keycloak-authoritative-identity.md) | Keycloak as Authoritative Identity Provider | Accepted | 2025-01-28 |
| [0032](adr-0032-jwt-standardization.md) | JWT Standardization Across All Authentication Flows | Accepted | 2025-01-28 |
| [0033](adr-0033-service-principal-design.md) | Service Principal Design and Authentication Modes | Accepted | 2025-01-28 |
| [0034](adr-0034-api-key-jwt-exchange.md) | API Key to JWT Exchange Pattern | Accepted | 2025-01-28 |
| [0035](adr-0035-kong-jwt-validation.md) | Kong JWT Validation Strategy | Accepted | 2025-01-28 |
| [0036](adr-0036-hybrid-session-model.md) | Hybrid Session Model for Long-Running Tasks | Accepted | 2025-01-28 |
| [0037](adr-0037-identity-federation.md) | Identity Federation Architecture | Accepted | 2025-01-28 |
| [0038](adr-0038-scim-implementation.md) | SCIM 2.0 Implementation Approach | Accepted | 2025-01-28 |
| [0039](adr-0039-openfga-permission-inheritance.md) | OpenFGA Permission Inheritance for Service Principals | Accepted | 2025-01-28 |

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
