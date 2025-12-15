# ADR-0070: Unified Audit Logging Facility

**Status**: ✅ Implemented
**Date**: 2025-12-14
**Author**: Claude Code (Opus 4.5) + Vishnu Mohan
**Related**: GDPR, HIPAA, SOC 2 Type II, FedRAMP, EU AI Act

---

## Context

Enterprise AI systems require comprehensive audit logging to meet regulatory compliance requirements across multiple jurisdictions. The MCP Server LangGraph platform serves customers in healthcare (HIPAA), financial services (SOC 2), government (FedRAMP), and EU markets (GDPR, EU AI Act).

### Problem Statement

**Critical Compliance Gaps Identified:**

1. **No unified event model** - Existing audit logging was fragmented across connection-specific endpoints
2. **Missing AI operation logging** - EU AI Act Articles 12, 19, 72 require detailed AI decision logging
3. **No tamper-evidence** - FedRAMP AU-9 requires cryptographic integrity protection
4. **Fragmented retention** - Different regulations have different retention requirements (6 months to 7 years)
5. **No compliance reports** - Auditors need regulation-specific export formats

### Regulatory Requirements Summary

| Regulation | Key Requirements | Retention |
|------------|------------------|-----------|
| GDPR | Track PII access, support Art. 15/17/20 rights | 7 years |
| HIPAA | Audit ePHI access, log who/what/when | 6 years |
| SOC 2 | Access controls (CC6.x), system ops (CC7.x) | 3 years |
| FedRAMP | AU-2 events, AU-3 content, AU-9 integrity, AU-11 retention | 7 years |
| EU AI Act | AI decision logs, model details, user interactions | 6 months minimum |

## Decision

Implement a comprehensive Unified Audit Logging Facility that:

1. **Answers WHO did WHAT, WHEN, and WHERE** for every auditable action
2. **Provides cryptographic tamper-evidence** using HMAC-SHA256 hash chains
3. **Supports all five regulatory frameworks** with regulation-specific tagging
4. **Enables compliance reporting** with API endpoints for each regulation
5. **Integrates seamlessly** via HTTP middleware and decorators

## Solution Architecture

### Core Components

```
src/mcp_server_langgraph/audit/
├── __init__.py          # Module exports
├── models.py            # Pydantic models (UnifiedAuditEvent, AuditActor, etc.)
├── constants.py         # Regulation enum, RetentionDays enum
├── exceptions.py        # Custom exception hierarchy
├── service.py           # UnifiedAuditService (core business logic)
├── integrity.py         # HashChainBuilder, verify_chain (FedRAMP AU-9)
├── decorators.py        # @audit_action, @audit_ai_operation, @audit_data_access
├── context.py           # OpenTelemetry trace correlation
├── alerts.py            # Anomaly detection (failed logins, bulk exports)
├── metrics.py           # Prometheus metrics
├── notifications.py     # Slack/PagerDuty integration
└── scheduler.py         # Daily integrity verification
```

### Unified Audit Event Model

```python
class UnifiedAuditEvent(BaseModel):
    # Core identifiers
    event_id: str                    # UUID v4
    timestamp: datetime              # UTC, NTP-synchronized

    # Event classification
    category: AuditEventCategory     # AUTHENTICATION, AUTHORIZATION, DATA_ACCESS, etc.
    event_type: AuditEventType       # LOGIN_SUCCESS, DATA_READ, AI_INVOKE, etc.

    # WHO performed the action
    actor: AuditActor                # actor_id, actor_type, username, roles

    # WHAT was affected
    resource_type: str               # workflow, session, connection, ai_model
    resource_id: str                 # Unique resource identifier
    action: str                      # Human-readable description
    outcome: Literal["success", "failure", "denied", "error"]

    # WHERE it occurred
    context: AuditContext            # request_id, trace_id, ip_address, etc.

    # AI-specific (EU AI Act)
    ai_operation: AIOperationDetails | None  # model_id, tokens, latency, decision_type

    # Integrity (FedRAMP AU-9)
    sequence_number: int | None      # Sequential ordering
    previous_hash: str | None        # Hash chain link
    event_hash: str | None           # HMAC-SHA256 of event

    # Compliance
    regulation_tags: list[str]       # ["GDPR", "HIPAA", "SOC2", etc.]
    retention_days: int              # Default: 2555 (7 years)
```

### Hash Chain Integrity (FedRAMP AU-9)

```
Event 1                Event 2                Event 3
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ seq: 1       │      │ seq: 2       │      │ seq: 3       │
│ prev: null   │─────▶│ prev: hash1  │─────▶│ prev: hash2  │
│ hash: hash1  │      │ hash: hash2  │      │ hash: hash3  │
└──────────────┘      └──────────────┘      └──────────────┘

hash = HMAC-SHA256(secret, previous_hash + json(event))
```

**Tampering Detection:**
- Modified event → hash mismatch detected
- Deleted event → sequence gap detected
- Wrong secret → all hashes fail verification

### API Endpoints

**Unified Audit API (`/api/v1/audit`):**
- `GET /events` - Query with filters (category, event_type, actor, regulation, time range)
- `GET /events/{id}` - Get specific event with full details
- `GET /integrity/verify` - Verify hash chain integrity
- `GET /export` - Export to JSON/CSV for compliance

**Compliance Reports API (`/api/v1/compliance`):**
- `GET /reports/gdpr` - GDPR Article 30 Records of Processing
- `GET /reports/hipaa` - HIPAA 164.312(b) Audit Controls
- `GET /reports/soc2` - SOC 2 Type II Evidence
- `GET /reports/fedramp` - FedRAMP AU Controls
- `GET /reports/eu-ai-act` - EU AI Act Articles 12/19/72

### Middleware Integration

```python
# In app.py
from mcp_server_langgraph.middleware.audit import AuditMiddleware
app.add_middleware(AuditMiddleware)
```

The middleware automatically:
- Captures all HTTP requests (excludes `/health`, `/metrics`)
- Extracts actor from `request.state.user`
- Correlates with OpenTelemetry trace/span IDs
- Logs events asynchronously (non-blocking)
- Handles audit failures gracefully (FedRAMP AU-5)

## Test Coverage

### Test Summary (TDD Approach)

| Category | Tests | Status |
|----------|-------|--------|
| Unit tests (audit/) | 148 | ✅ PASS |
| Integration tests (audit/) | 28 | ✅ PASS |
| Compliance tests | 42 | ✅ PASS |
| API tests (audit + reports) | 21 | ✅ PASS |
| **Total** | **239** | **✅ ALL GREEN** |

### Compliance Validation Tests

- `tests/compliance/test_gdpr_audit_requirements.py` - 9 tests
- `tests/compliance/test_hipaa_audit_requirements.py` - 7 tests
- `tests/compliance/test_soc2_audit_requirements.py` - 7 tests
- `tests/compliance/test_fedramp_audit_requirements.py` - 10 tests
- `tests/compliance/test_eu_ai_act_requirements.py` - 9 tests

## Configuration

### Retention Policies (`config/audit_retention.yaml`)

```yaml
retention_policies:
  default:
    retention_years: 7
    compress_after_days: 90
  gdpr:
    retention_years: 7
    anonymize_after_years: 6
  hipaa:
    retention_years: 6
  fedramp:
    retention_years: 7
    hot_tier_days: 90
    searchable_days: 365
  eu_ai_act:
    retention_months: 6
  soc2:
    retention_years: 3
```

### Pytest Markers

```ini
# pyproject.toml
markers = [
    "gdpr: GDPR compliance tests",
    "hipaa: HIPAA compliance tests (45 CFR 164.312(b))",
    "soc2: SOC 2 compliance tests",
    "fedramp: FedRAMP compliance tests (NIST 800-53 AU controls)",
    "eu_ai_act: EU AI Act compliance tests (Articles 12, 19, 72)",
    "compliance: Generic compliance tests",
]
```

## Alternatives Considered

### 1. Third-Party Audit SaaS (e.g., Splunk, Datadog)
**Rejected because:**
- Data sovereignty concerns (GDPR, FedRAMP)
- Vendor lock-in risk
- Cost at scale
- Limited customization for AI-specific logging

### 2. Separate Audit Database
**Rejected because:**
- Operational complexity
- Additional infrastructure cost
- PostgreSQL partitioning provides adequate performance

### 3. Event Sourcing Pattern
**Considered but deferred:**
- Overkill for audit logging use case
- Hash chain provides sufficient integrity
- Can be added later if needed

## Consequences

### Positive

1. **Single source of truth** for all audit events
2. **Cryptographic tamper-evidence** meets FedRAMP AU-9
3. **Regulation-specific queries** enable efficient compliance reporting
4. **Automatic capture** via middleware reduces developer burden
5. **Comprehensive test coverage** (239 tests) ensures reliability
6. **Grafana dashboard** provides operational visibility

### Negative

1. **Storage growth** - Audit logs grow continuously (mitigated by retention policies)
2. **Write overhead** - Every request generates an audit event (mitigated by async logging)
3. **Migration complexity** - Existing data needs backfill for unified model

### Risks

1. **Performance impact** - Monitored via `audit_events_latency_seconds` metric
2. **Hash chain corruption** - Daily verification via scheduler detects issues early
3. **Retention misconfiguration** - YAML schema validation prevents errors

## Implementation Notes

### Files Created (17)

| File | Purpose |
|------|---------|
| `audit/models.py` | Pydantic models for audit events |
| `audit/constants.py` | Regulation and retention enums |
| `audit/exceptions.py` | Custom exception hierarchy |
| `audit/service.py` | Core audit service |
| `audit/integrity.py` | Hash chain implementation |
| `audit/decorators.py` | @audit_action, etc. |
| `audit/context.py` | OpenTelemetry integration |
| `audit/alerts.py` | Anomaly detection |
| `audit/metrics.py` | Prometheus metrics |
| `audit/notifications.py` | Slack/PagerDuty |
| `audit/scheduler.py` | Daily verification |
| `middleware/audit.py` | HTTP middleware |
| `api/v1/audit.py` | Audit API router |
| `api/v1/compliance_reports.py` | Reports API router |
| `config/audit_retention.yaml` | Retention config |
| `alembic/.../unified_audit_schema.py` | DB migration |
| `monitoring/.../audit-compliance.json` | Grafana dashboard |

### Database Migration

```sql
-- Key columns added to audit_logs table
ALTER TABLE audit_logs ADD COLUMN category VARCHAR(50);
ALTER TABLE audit_logs ADD COLUMN outcome VARCHAR(20);
ALTER TABLE audit_logs ADD COLUMN sequence_number BIGINT;
ALTER TABLE audit_logs ADD COLUMN previous_hash VARCHAR(64);
ALTER TABLE audit_logs ADD COLUMN event_hash VARCHAR(64);
ALTER TABLE audit_logs ADD COLUMN regulation_tags TEXT[];
ALTER TABLE audit_logs ADD COLUMN retention_days INTEGER DEFAULT 2555;
ALTER TABLE audit_logs ADD COLUMN ai_operation JSONB;

-- Indices for compliance queries
CREATE INDEX idx_audit_regulation ON audit_logs USING GIN(regulation_tags);
CREATE INDEX idx_audit_category ON audit_logs(category);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
```

## References

- [Splunk Audit Logging Guide](https://www.splunk.com/en_us/blog/learn/audit-logs.html)
- [HIPAA Audit Log Requirements 2025](https://www.kiteworks.com/hipaa-compliance/hipaa-audit-log-requirements/)
- [FedRAMP Logging Requirements](https://www.kiteworks.com/regulatory-compliance/fedramp-audit-log/)
- [NIST 800-53 AU Controls](https://csf.tools/reference/nist-sp-800-53/r5/au/)
- [EU AI Act Logging Compliance](https://logdy.dev/blog/post/eu-ai-act-implications-for-log-management-systems-and-compliance)
- [Immutable Audit Log Security](https://www.cossacklabs.com/blog/audit-logs-security/)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2025-12-14 | Claude Code (Opus 4.5) | Initial implementation with 239 passing tests |
