# Architecture Decision Records (ADRs)

**Last Updated**: 2025-11-12
**Total ADRs**: 54

## Overview

This directory contains all Architecture Decision Records (ADRs) for the MCP Server LangGraph project.
ADRs document significant architectural decisions, their context, rationale, and consequences.

## Format

Each ADR follows this structure:
- **Title**: Brief description of the decision
- **Status**: Proposed, Accepted, Deprecated, or Superseded
- **Date**: When the decision was made
- **Context**: The problem or opportunity
- **Decision**: What was decided
- **Consequences**: Positive and negative outcomes

## Index

### Authentication & Authorization

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0002](adr-0002-openfga-authorization.md) | 2. Fine-Grained Authorization with OpenFGA | Unknown | Unknown |
| [ADR-0032](adr-0032-jwt-standardization.md) | 32. JWT Standardization Across All Authentication Flows | Unknown | Unknown |
| [ADR-0033](adr-0033-service-principal-design.md) | 33. Service Principal Design and Authentication Modes | Unknown | Unknown |
| [ADR-0034](adr-0034-api-key-jwt-exchange.md) | 34. API Key to JWT Exchange Pattern | Unknown | Unknown |
| [ADR-0035](adr-0035-kong-jwt-validation.md) | 35. Kong JWT Validation Strategy | Unknown | Unknown |
| [ADR-0038](adr-0038-scim-implementation.md) | 38. SCIM 2.0 Implementation Approach | Unknown | Unknown |
| [ADR-0039](adr-0039-openfga-permission-inheritance.md) | 39. OpenFGA Permission Inheritance for Service Principals | Unknown | Unknown |

### Core Architecture

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0001](adr-0001-llm-multi-provider.md) | 1. Multi-Provider LLM Support via LiteLLM | Unknown | Unknown |
| [ADR-0003](adr-0003-dual-observability.md) | 3. Dual Observability: OpenTelemetry + LangSmith | Unknown | Unknown |
| [ADR-0004](adr-0004-mcp-streamable-http.md) | 4. MCP StreamableHTTP Transport Protocol | Unknown | Unknown |
| [ADR-0006](adr-0006-session-storage-architecture.md) | 6. Pluggable Session Storage Architecture | Unknown | Unknown |
| [ADR-0007](adr-0007-authentication-provider-pattern.md) | 7. Pluggable Authentication Provider Pattern | Unknown | Unknown |
| [ADR-0019](adr-0019-async-first-architecture.md) | 19. Async-First Architecture | Unknown | Unknown |
| [ADR-0020](adr-0020-dual-mcp-transport-protocol.md) | 20. Dual MCP Transport Protocol (STDIO + StreamableHTTP) | Unknown | Unknown |
| [ADR-0026](adr-0026-lazy-observability-initialization.md) | Lazy Observability Initialization | Unknown | 2025-01-17 |
| [ADR-0031](adr-0031-keycloak-authoritative-identity.md) | 31. Keycloak as Authoritative Identity Provider | Unknown | Unknown |
| [ADR-0037](adr-0037-identity-federation.md) | 37. Identity Federation Architecture | Unknown | Unknown |

### Data & Storage

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0015](adr-0015-memory-checkpointing.md) | 15. Memory Checkpointing for Stateful Agents | Unknown | Unknown |
| [ADR-0022](adr-0022-distributed-conversation-checkpointing.md) | 22. Distributed Conversation Checkpointing for Auto-Scaling | Unknown | Unknown |
| [ADR-0036](adr-0036-hybrid-session-model.md) | 36. Hybrid Session Model for Long-Running Tasks | Unknown | Unknown |
| [ADR-0051](adr-0051-memorystore-redis-externalname-service.md) | 51. Memorystore Redis ExternalName Service with Cloud DNS | Unknown | Unknown |

### Development & Tooling

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0011](adr-0011-cookiecutter-template-strategy.md) | 11. Cookiecutter Template for Project Generation | Unknown | Unknown |
| [ADR-0021](adr-0021-cicd-pipeline-strategy.md) | 21. CI/CD Pipeline Strategy | Unknown | Unknown |

### Infrastructure & Deployment

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0013](adr-0013-multi-deployment-target-strategy.md) | 13. Multi-Deployment Target Strategy | Unknown | Unknown |
| [ADR-0040](adr-0040-gcp-gke-autopilot-deployment.md) | 40. GCP GKE Autopilot Deployment Strategy | Supported as alternative (see `deployments/cloudrun/`), but GKE is primary | Unknown |
| [ADR-0044](adr-0044-test-infrastructure-quick-wins.md) | Test Infrastructure Quick Wins | Accepted | 2025-11-06 |
| [ADR-0045](adr-0045-test-infrastructure-phase-2-foundation.md) | Test Infrastructure Phase 2 - Real Infrastructure Foundation | Accepted | 2025-11-06 |
| [ADR-0046](adr-0046-deployment-configuration-tdd-infrastructure.md) | Deployment Configuration TDD Infrastructure | Accepted | 2025-11-06 |

### Other

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0005](adr-0005-pydantic-ai-integration.md) | 5. Type-Safe Agent Responses with Pydantic AI | Unknown | Unknown |
| [ADR-0009](adr-0009-feature-flag-system.md) | 9. Feature Flag System for Gradual Rollouts | Unknown | Unknown |
| [ADR-0010](adr-0010-langgraph-functional-api.md) | 10. LangGraph Functional API over Object-Oriented Approach | Unknown | Unknown |
| [ADR-0014](adr-0014-pydantic-type-safety.md) | 14. Pydantic Type Safety Strategy | Unknown | Unknown |
| [ADR-0017](adr-0017-error-handling-strategy.md) | 17. Error Handling Strategy | Unknown | Unknown |
| [ADR-0018](adr-0018-semantic-versioning-strategy.md) | 18. Semantic Versioning Strategy | Unknown | Unknown |
| [ADR-0023](adr-0023-anthropic-tool-design-best-practices.md) | 23. Anthropic Tool Design Best Practices | Unknown | Unknown |
| [ADR-0024](adr-0024-agentic-loop-implementation.md) | 24. Agentic Loop Implementation Following Anthropic Best Practices | Unknown | Unknown |
| [ADR-0025](adr-0025-anthropic-best-practices-enhancements.md) | Anthropic Best Practices - Advanced Enhancements | ✅ Accepted | 2025-10-17 |
| [ADR-0027](adr-0027-rate-limiting-strategy.md) | Rate Limiting Strategy for API Protection | Accepted | 2025-10-20 |
| [ADR-0029](adr-0029-custom-exception-hierarchy.md) | Custom Exception Hierarchy | Accepted | 2025-10-20 |
| [ADR-0042](adr-0042-dependency-injection-configuration-fixes.md) | Dependency Injection Configuration Fixes | Accepted | 2025-01-28 |
| [ADR-0043](adr-0043-cost-monitoring-dashboard.md) | Cost Monitoring Dashboard | Unknown | Unknown |
| [ADR-0047](adr-0047-visual-workflow-builder.md) | Visual Workflow Builder | Unknown | Unknown |
| [ADR-0050](adr-0050-dependency-singleton-pattern-justification.md) | Dependency Singleton Pattern Justification | Accepted | 2025-11-10 |
| [ADR-0054](adr-0054-pod-failure-prevention-framework.md) | Pod Failure Prevention Framework | Accepted | 2025-11-12 |

### Performance & Resilience

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0028](adr-0028-caching-strategy.md) | Multi-Layer Caching Strategy | Accepted | 2025-10-20 |
| [ADR-0030](adr-0030-resilience-patterns.md) | Resilience Patterns for Production Systems | Accepted | 2025-10-20 |

### Security & Compliance

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0008](adr-0008-infisical-secrets-management.md) | 8. Infisical for Secrets Management | Unknown | Unknown |
| [ADR-0012](adr-0012-compliance-framework-integration.md) | 12. Built-In Compliance Framework (GDPR, SOC 2, HIPAA) | Unknown | Unknown |
| [ADR-0041](adr-0041-postgresql-gdpr-storage.md) | Pure PostgreSQL for GDPR/HIPAA/SOC2 Compliance Storage | Accepted | 2025-11-02 |

### Testing & Quality

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0016](adr-0016-property-based-testing-strategy.md) | 16. Property-Based Testing with Hypothesis | Unknown | Unknown |
| [ADR-0048](adr-0048-postgres-storage-integration-tests.md) | PostgreSQL Storage Integration Tests | Accepted | 2025-11-06 |
| [ADR-0049](adr-0049-pytest-fixture-consolidation.md) | Pytest Fixture Consolidation and Organization | Unknown | Unknown |
| [ADR-0052](adr-0052-pytest-xdist-isolation-strategy.md) | Pytest-xdist Isolation Strategy | Unknown | Unknown |
| [ADR-0053](adr-0053-ci-cd-failure-prevention-framework.md) | CI/CD Failure Prevention Framework | Accepted | 2025-11-12 |

## Creating a New ADR

1. Determine the next ADR number:
   ```bash
   ls adr/adr-*.md | sort -V | tail -1
   ```

2. Create a new file:
   ```bash
   cp adr/adr-0001-llm-multi-provider.md adr/adr-XXXX-your-title.md
   ```

3. Update the content:
   - Change the ADR number and title
   - Fill in Status, Date, Context, Decision, and Consequences
   - Add relevant tags

4. Sync to Mintlify documentation:
   ```bash
   python scripts/sync-adrs.py
   ```

5. Update this index:
   ```bash
   python scripts/generate_adr_index.py
   ```

## Validation

To validate ADR numbering and sync status:

```bash
# Check for duplicate ADR numbers
pytest tests/regression/test_documentation_structure.py::TestADRNumbering::test_no_duplicate_adr_numbers

# Check ADR sync status
python scripts/sync-adrs.py --check

# Validate this index is up-to-date
python scripts/generate_adr_index.py --check
```

## Related Documentation

- [Architecture Overview](../docs/architecture/overview.mdx) - High-level system architecture
- [Mintlify ADRs](../docs/architecture/) - User-friendly ADR documentation
- [ADR Sync Script](../scripts/sync-adrs.py) - Keep ADRs in sync with Mintlify

---

**Auto-generated by**: `scripts/generate_adr_index.py`
**Do not edit manually**: Run the script to regenerate this file.
