# Production TODO Items Catalog

**Generated**: 2025-10-18
**Total Items**: 30
**Status**: Active - Technical Debt Sprint

---

## Executive Summary

This document catalogs all TODO items found in production source code (`src/` directory). Each item has been categorized, prioritized, and mapped to implementation requirements.

### Distribution by Category

| Category | Count | Priority |
|----------|-------|----------|
| Monitoring & Alerting | 8 | 🔴 CRITICAL |
| Compliance & Evidence | 10 | 🔴 CRITICAL |
| Core Features | 5 | 🟡 HIGH |
| Integrations | 4 | 🟡 HIGH |
| Infrastructure | 3 | 🟢 MEDIUM |

---

## 🔴 CRITICAL PRIORITY

### Category: Monitoring & Alerting (8 items)

#### 1. SLA Monitoring - Prometheus Integration
**Files**: `src/mcp_server_langgraph/monitoring/sla.py`

| Line | TODO | Impact |
|------|------|--------|
| 157 | Query Prometheus for actual downtime | Uptime SLA tracking inaccurate |
| 235 | Query Prometheus for actual response times | Response time SLA unverified |
| 300 | Query Prometheus for actual error rate | Error rate SLA unmeasured |

**Current State**: Returns mock/hardcoded data
**Required**: Prometheus HTTP API client integration
**Complexity**: Medium (3-5 days)
**Dependencies**: prometheus-api-client library

**Implementation Plan**:
```python
# Add to requirements-pinned.txt
prometheus-api-client==0.5.3

# Implement queries:
# - query_range() for time-series data
# - custom_query() for PromQL expressions
# - Metrics: up, http_request_duration_seconds, http_requests_total
```

#### 2. Alerting System Integration
**Files**: Multiple

| File | Line | TODO | Impact |
|------|------|------|--------|
| `monitoring/sla.py` | 505 | Send to alerting system (PagerDuty, Slack, email) | No SLA breach alerts |
| `schedulers/compliance.py` | 418 | Send to alerting system (PagerDuty, Slack, email) | No compliance alerts |
| `schedulers/compliance.py` | 433 | Send notification to security team | Security events unreported |
| `schedulers/compliance.py` | 452 | Send notification to compliance team | Compliance events unreported |
| `schedulers/cleanup.py` | 167 | Implement notification sending (email, Slack, etc.) | Cleanup failures silent |

**Current State**: Alerting infrastructure exists (`integrations/alerting.py`) but not connected
**Required**: Configuration and integration with alert methods
**Complexity**: Medium (2-3 days)
**Dependencies**: None (alerting.py already implemented)

**Implementation Plan**:
```python
# File: src/mcp_server_langgraph/integrations/alerting.py:407
# Add to config.py:
PAGERDUTY_INTEGRATION_KEY: Optional[str] = None
SLACK_WEBHOOK_URL: Optional[str] = None
OPSGENIE_API_KEY: Optional[str] = None

# Wire up in existing code:
from mcp_server_langgraph.integrations.alerting import AlertingService
alerting = AlertingService()
alerting.send_alert(Alert(...))
```

---

### Category: Compliance & Evidence (10 items)

#### 3. Evidence Collection - Data Integration
**File**: `src/mcp_server_langgraph/core/compliance/evidence.py`

| Line | TODO | Current Value | Impact |
|------|------|---------------|--------|
| 257 | Implement session count query | 0 (hardcoded) | Inaccurate access control metrics |
| 261 | Query user provider for MFA stats | 0 (hardcoded) | Missing MFA adoption data |
| 264 | Query OpenFGA for role count | True (hardcoded) | RBAC metrics incomplete |
| 419 | Query Prometheus for actual uptime data | Mock data | Incorrect availability metrics |
| 426 | Query from incident tracking | 0 (hardcoded) | Missing incident history |
| 457 | Query backup system | Current timestamp | Incorrect backup status |
| 507 | Implement anomaly detection | False (hardcoded) | Security feature missing |

**Current State**: Evidence endpoints return mock data
**Required**: Integration with actual data sources
**Complexity**: High (5-7 days)
**Dependencies**: Session store, UserProvider, OpenFGA client, Prometheus client

**Implementation Plan**:
```python
# Session count:
from mcp_server_langgraph.auth.session import session_factory
session_store = session_factory()
active_sessions = await session_store.get_all_sessions()

# MFA stats:
from mcp_server_langgraph.auth.user_provider import user_provider_factory
provider = user_provider_factory()
users = await provider.list_users()
mfa_count = sum(1 for u in users if u.mfa_enabled)

# RBAC roles:
from mcp_server_langgraph.auth.openfga import OpenFGAClient
openfga = OpenFGAClient()
roles = await openfga.list_relations()
```

#### 4. Storage Backend Integration
**Files**: `src/mcp_server_langgraph/core/compliance/`

| File | Line | TODO | Impact |
|------|------|------|--------|
| `retention.py` | 330 | Integrate with actual conversation storage backend | Cannot enforce retention |
| `retention.py` | 353 | Integrate with audit log storage and cold storage backend | No audit archival |
| `data_deletion.py` | 325 | Integrate with audit log storage | GDPR deletion unaudited |

**Current State**: Placeholder implementations
**Required**: Redis/PostgreSQL storage integration
**Complexity**: High (7-10 days)
**Dependencies**: Database schema, migration scripts

**Implementation Plan**:
```python
# Conversation storage (use existing Redis checkpointer):
from langgraph.checkpoint.redis import RedisSaver
checkpoint = RedisSaver(redis_url)
# Query by user_id, apply retention policies

# Audit log storage (new PostgreSQL table):
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    metadata JSONB
);

# Cold storage (S3/GCS for archive):
from google.cloud import storage
bucket = storage_client.bucket('audit-archive')
```

#### 5. User Session Analysis
**File**: `src/mcp_server_langgraph/schedulers/compliance.py`

| Line | TODO | Impact |
|------|------|--------|
| 271 | Query user provider for all users | Cannot perform access reviews |
| 279 | Implement user session analysis | SOC2 AC-2 requirement missing |

**Current State**: Compliance scheduler exists but doesn't analyze sessions
**Required**: Session pattern analysis, anomaly detection
**Complexity**: Medium (4-6 days)
**Dependencies**: Session store, user provider

---

## 🟡 HIGH PRIORITY

### Category: Core Features (5 items)

#### 6. Search Tools Implementation
**File**: `src/mcp_server_langgraph/tools/search_tools.py`

| Line | TODO | Impact |
|------|------|--------|
| 37 | Implement actual knowledge base search | Feature incomplete |
| 86 | Implement actual web search | Feature incomplete |

**Current State**: Stub implementations returning mock data
**Required**: Integration with search APIs or vector databases
**Complexity**: Medium (3-5 days)
**Dependencies**: API keys (Tavily, SerpAPI, etc.) or Qdrant setup

**Implementation Plan**:
```python
# Knowledge base search (use existing Qdrant):
from qdrant_client import QdrantClient
client = QdrantClient(url=settings.qdrant_url, port=settings.qdrant_port)
results = client.search(
    collection_name="knowledge_base",
    query_vector=embedding,
    limit=5
)

# Web search (Tavily API):
from tavily import TavilyClient
tavily = TavilyClient(api_key=settings.tavily_api_key)
results = tavily.search(query, max_results=5)
```

#### 7. GDPR User Profile Integration
**File**: `src/mcp_server_langgraph/api/gdpr.py`

| Line | TODO | Impact |
|------|------|--------|
| 268 | Integrate with actual user profile storage | Cannot update profiles |
| 335 | Pass OpenFGA client from app state | Authorization not enforced |

**Current State**: GDPR endpoints exist but not fully functional
**Required**: Storage backend + OpenFGA integration
**Complexity**: Medium (3-4 days)
**Dependencies**: User storage schema, OpenFGA client

#### 8. HIPAA Security Integration
**File**: `src/mcp_server_langgraph/auth/hipaa.py`

| Line | TODO | Impact |
|------|------|--------|
| 207 | Send alert to security team | HIPAA violations unreported |
| 320 | Send to SIEM system | Security events not logged |

**Current State**: HIPAA audit logging implemented but alerts not sent
**Required**: Alerting + SIEM integration
**Complexity**: Medium (2-3 days)
**Dependencies**: Alerting service, SIEM connector

---

## 🟢 MEDIUM PRIORITY

### Category: Infrastructure (3 items)

#### 9. Prompt Versioning
**File**: `src/mcp_server_langgraph/prompts/__init__.py`

| Line | TODO | Impact |
|------|------|--------|
| 51 | Implement versioning when needed | Prompt changes not tracked |

**Current State**: Prompts loaded without version control
**Required**: Version metadata, compatibility checks
**Complexity**: Low (1-2 days)
**Dependencies**: None

#### 10. Alerting Configuration
**File**: `src/mcp_server_langgraph/integrations/alerting.py`

| Line | TODO | Impact |
|------|------|--------|
| 407 | Add alerting configuration to settings | Cannot configure alerts |

**Current State**: Alerting service exists but config missing
**Required**: Settings additions
**Complexity**: Low (1 day)
**Dependencies**: None

---

## Implementation Roadmap

### Phase 1: Critical Monitoring (Week 1-2)
- **Days 1-5**: Prometheus integration for SLA monitoring (#1)
- **Days 6-8**: Alerting system wiring (#2)
- **Days 9-10**: Testing and validation

**Deliverable**: Production monitoring with real metrics and alerts

### Phase 2: Compliance Integration (Week 3-4)
- **Days 1-7**: Evidence collection integration (#3)
- **Days 8-14**: Storage backend implementation (#4)
- **Days 15-18**: User session analysis (#5)

**Deliverable**: Compliance endpoints with real data

### Phase 3: Feature Completion (Week 5-6)
- **Days 1-5**: Search tools implementation (#6)
- **Days 6-8**: GDPR integration (#7)
- **Days 9-11**: HIPAA security (#8)
- **Days 12-14**: Infrastructure items (#9, #10)

**Deliverable**: All features production-ready

---

## Acceptance Criteria

### Per TODO Item
- [ ] Implementation complete with tests
- [ ] Documentation updated
- [ ] Configuration added to `.env.example`
- [ ] Integration tests passing
- [ ] Removed from production code
- [ ] GitHub issue closed

### Overall
- [ ] Zero TODOs in `src/` directory
- [ ] All endpoints return real data (no mocks)
- [ ] Monitoring dashboards show live metrics
- [ ] Alerts fire for SLA/compliance violations
- [ ] Test coverage maintained (>80%)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Prometheus unavailable in prod | Medium | High | Add fallback to cached/estimated values |
| External APIs rate-limited | High | Medium | Implement caching and backoff |
| Storage migration complexity | Medium | High | Staged rollout with feature flags |
| Alert fatigue | Medium | Medium | Careful threshold tuning |

---

## Dependencies & Prerequisites

### Required Before Starting
- [ ] Prometheus deployed and accessible
- [ ] PagerDuty/Slack credentials configured
- [ ] Database migrations reviewed
- [ ] Feature flags enabled for new integrations

### Optional (Enhanced Functionality)
- [ ] Tavily API key for web search
- [ ] S3/GCS bucket for audit archives
- [ ] SIEM system connector

---

## Success Metrics

**Before**:
- 30 TODO items in production code
- Mock data in monitoring/compliance endpoints
- No automated alerts
- Manual compliance evidence collection

**After**:
- 0 TODO items in production code
- Live metrics from Prometheus
- Automated alerts to PagerDuty/Slack
- Real-time compliance dashboards
- Full GDPR/HIPAA integration

---

## Related Documents

- [ADR-0012: Compliance Framework Integration](../../adr/adr-0012-compliance-framework-integration.md)

For monitoring and compliance documentation, see the Mintlify docs in the `docs/` directory.

---

**Maintained by**: Technical Debt Sprint Team
**Next Review**: After Phase 1 completion
**GitHub Project**: [Technical Debt Sprint](https://github.com/vishnu2kmohan/mcp-server-langgraph/projects/1)
