# Compliance & Governance Guide

**MCP Server with LangGraph - Enterprise Compliance Features**

This guide covers the comprehensive compliance, governance, and regulatory features built into the MCP Server with LangGraph.

---

## Table of Contents

- [Overview](#overview)
- [GDPR Compliance](#gdpr-compliance)
- [SOC 2 Compliance](#soc-2-compliance)
- [HIPAA Compliance](#hipaa-compliance)
- [SLA Monitoring](#sla-monitoring)
- [Data Retention](#data-retention)
- [Audit Logging](#audit-logging)
- [Compliance Dashboards](#compliance-dashboards)
- [Automation & Scheduling](#automation--scheduling)
- [Compliance Reporting](#compliance-reporting)
- [Quick Start](#quick-start)

---

## Overview

The MCP Server with LangGraph includes production-ready compliance features for:

- **GDPR**: Data subject rights (access, rectification, erasure, portability, consent)
- **SOC 2**: Trust Services Criteria evidence collection and reporting
- **HIPAA**: Technical safeguards (emergency access, audit controls, integrity, session timeout)
- **SLA Monitoring**: Automated uptime, response time, and error rate tracking
- **Data Retention**: Configurable retention policies with automated cleanup

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Compliance Layer                          │
├─────────────────────────────────────────────────────────────┤
│  GDPR APIs  │  SOC 2 Evidence  │  HIPAA Controls  │  SLA    │
│  (REST)     │  (Automated)     │  (Middleware)    │ Monitor │
├─────────────────────────────────────────────────────────────┤
│              Automation & Scheduling (APScheduler)           │
├─────────────────────────────────────────────────────────────┤
│  Daily Checks │ Weekly Reviews │ Monthly Reports │ Cleanup  │
├─────────────────────────────────────────────────────────────┤
│           Observability (Grafana + Prometheus)               │
├─────────────────────────────────────────────────────────────┤
│  SLA Dashboard │ SOC 2 Dashboard │ Auth Dashboard │ Security │
└─────────────────────────────────────────────────────────────┘
```

---

## GDPR Compliance

**General Data Protection Regulation (EU) - Data Subject Rights Implementation**

### Features

✅ **Article 15 - Right to Access**
✅ **Article 16 - Right to Rectification**
✅ **Article 17 - Right to Erasure ("Right to be Forgotten")**
✅ **Article 20 - Right to Data Portability**
✅ **Article 21 - Consent Management**

### API Endpoints

#### 1. Data Access (Article 15)

```bash
# Get all user data
GET /api/v1/users/me/data

# Response includes:
# - User profile
# - Active sessions
# - Conversations
# - Preferences
# - Audit logs
# - Consent records
```

#### 2. Data Rectification (Article 16)

```bash
# Update user profile
PATCH /api/v1/users/me
Content-Type: application/json

{
  "name": "Updated Name",
  "email": "newemail@example.com"
}
```

#### 3. Data Erasure (Article 17)

```bash
# Delete all user data (requires confirmation)
DELETE /api/v1/users/me?confirm=true

# WARNING: This action is irreversible!
# Deletes:
# - User profile
# - All sessions
# - Conversations
# - Preferences
# - OpenFGA tuples
# - Anonymizes audit logs (preserves compliance trail)
```

#### 4. Data Portability (Article 20)

```bash
# Export data in machine-readable format
GET /api/v1/users/me/export?format=json

# Export in human-readable format
GET /api/v1/users/me/export?format=csv

# Response: Downloadable file with all user data
```

#### 5. Consent Management (Article 21)

```bash
# Give consent
POST /api/v1/users/me/consent
Content-Type: application/json

{
  "consent_type": "analytics",
  "granted": true,
  "metadata": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}

# Withdraw consent
POST /api/v1/users/me/consent
{
  "consent_type": "analytics",
  "granted": false
}

# Get consent status
GET /api/v1/users/me/consent
```

### Consent Types

- `analytics` - Usage analytics and tracking
- `marketing` - Marketing communications
- `third_party` - Third-party data sharing
- `profiling` - Automated decision-making/profiling

### Implementation Details

**Location**: `src/mcp_server_langgraph/api/gdpr.py`

**Services**:
- `DataExportService` - Multi-format data export (JSON, CSV)
- `DataDeletionService` - Cascade deletion with audit trail

**Testing**: `tests/test_gdpr.py` (30+ tests, comprehensive coverage)

---

## SOC 2 Compliance

**Service Organization Control 2 - Trust Services Criteria**

### Trust Services Criteria Covered

#### Security (CC)

- **CC6.1 - Access Control**: Active session tracking, MFA statistics, RBAC
- **CC6.2 - Logical Access**: Authentication providers, authorization system
- **CC6.6 - Audit Logs**: Comprehensive logging, 7-year retention, tamper-proof
- **CC7.2 - System Monitoring**: Prometheus/Grafana metrics, alerting
- **CC8.1 - Change Management**: Version control, CI/CD, code review

#### Availability (A)

- **A1.2 - SLA Monitoring**: 99.9% uptime target, backup verification

#### Processing Integrity (PI)

- **PI1.4 - Data Retention**: Automated cleanup, configurable policies

### Evidence Collection

**Automated Daily Collection** (6 AM UTC):

```python
from mcp_server_langgraph.core.compliance.evidence import EvidenceCollector

collector = EvidenceCollector(session_store=session_store)
evidence_items = await collector.collect_all_evidence()

# Collects 14+ evidence items:
# - Active sessions count
# - MFA statistics
# - Logging system status
# - Prometheus metrics
# - Version control info
# - Uptime percentage
# - Backup timestamps
# - Retention policies
```

**Evidence Types**:
- `security` - Security controls
- `availability` - Uptime and backups
- `confidentiality` - Encryption and access logs
- `processing_integrity` - Data validation and retention
- `privacy` - GDPR compliance evidence

### Compliance Reporting

**Report Types**:

1. **Daily Reports** (1-day period)
   - Quick compliance check
   - Evidence collection status
   - Immediate issue detection

2. **Weekly Reports** (7-day period)
   - Access reviews
   - User activity analysis
   - Inactive account detection

3. **Monthly Reports** (30-day period)
   - Comprehensive compliance summary
   - Trend analysis
   - Audit-ready documentation

**Generate Report**:

```python
from mcp_server_langgraph.core.compliance.evidence import EvidenceCollector

collector = EvidenceCollector(session_store=session_store)
report = await collector.generate_compliance_report(
    report_type="monthly",
    period_days=30
)

print(f"Compliance Score: {report.compliance_score:.1f}%")
print(f"Passed Controls: {report.passed_controls}/{report.total_controls}")
print(f"Findings: {len(report.findings)}")
```

### Access Reviews

**Weekly Automated Reviews** (Monday 9 AM UTC):

```python
from mcp_server_langgraph.schedulers import get_compliance_scheduler

scheduler = get_compliance_scheduler()
report = await scheduler.trigger_weekly_review()

# Reviews:
# - Active vs inactive users
# - Role assignments
# - Session activity
# - Access patterns
# - Recommendations for security improvements
```

### Implementation Details

**Location**:
- Evidence Collection: `src/mcp_server_langgraph/core/compliance/evidence.py`
- Scheduler: `src/mcp_server_langgraph/schedulers/compliance.py`

**Testing**: `tests/test_soc2_evidence.py` (36 tests, 97% pass rate)

---

## HIPAA Compliance

**Health Insurance Portability and Accountability Act - Technical Safeguards**

### Implemented Controls

#### 164.312(a)(2)(i) - Emergency Access Procedure

**Grant Emergency Access**:

```python
from mcp_server_langgraph.auth.hipaa import HIPAAControls

hipaa = HIPAAControls()

grant = await hipaa.grant_emergency_access(
    user_id="user:doctor_smith",
    reason="Patient emergency - cardiac arrest in ER",
    approver_id="user:supervisor_jones",
    duration_hours=2  # Time-limited access
)

# Automatically expires after 2 hours
# Comprehensive audit logging
# Security team alerting
```

#### 164.312(b) - Audit Controls (PHI Access Logging)

**Log PHI Access**:

```python
await hipaa.log_phi_access(
    user_id="user:doctor_smith",
    action="read",
    patient_id="patient:12345",
    resource_id="medical_record:67890",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0...",
    success=True
)

# Tamper-proof audit trail
# 7-year retention (exceeds 6-year HIPAA minimum)
# SIEM integration ready
```

#### 164.312(c)(1) - Integrity Controls (HMAC Checksums)

**Generate and Verify Checksums**:

```python
# Generate checksum for data integrity
integrity_check = hipaa.generate_checksum(
    data="patient medical record...",
    data_id="record:12345"
)

# Verify data hasn't been tampered with
is_valid = hipaa.verify_checksum(
    data="patient medical record...",
    expected_checksum=integrity_check.checksum
)

# HMAC-SHA256 algorithm
# Constant-time comparison (prevents timing attacks)
```

#### 164.312(a)(2)(iii) - Automatic Logoff

**Session Timeout Middleware**:

```python
from mcp_server_langgraph.middleware import SessionTimeoutMiddleware

# Automatic logoff after 15 minutes of inactivity (configurable)
app.add_middleware(
    SessionTimeoutMiddleware,
    timeout_minutes=15,  # HIPAA recommendation
    session_store=session_store
)

# Sliding window: activity extends session
# Audit logging of timeout events
```

### HIPAA Compliance Coverage

| Requirement | Implementation | Status |
|-------------|----------------|--------|
| 164.312(a)(1) | Unique User ID | ✅ `user:username` format |
| 164.312(a)(2)(i) | Emergency Access | ✅ Time-limited grants |
| 164.312(a)(2)(iii) | Automatic Logoff | ✅ 15-min timeout middleware |
| 164.312(b) | Audit Controls | ✅ PHI access logging |
| 164.312(c)(1) | Integrity | ✅ HMAC-SHA256 checksums |
| 164.312(e)(1) | Transmission Security | ✅ TLS 1.3 |
| 164.312(a)(2)(iv) | Encryption at Rest | 🚧 Database-level encryption |

### Implementation Details

**Location**:
- HIPAA Controls: `src/mcp_server_langgraph/auth/hipaa.py`
- Session Timeout: `src/mcp_server_langgraph/middleware/session_timeout.py`

**Testing**: Included in `tests/test_auth.py`

---

## SLA Monitoring

**Service Level Agreement - Automated Tracking and Alerting**

### SLA Targets

**Default SLA Targets**:

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| **Uptime** | 99.9% | 99.5% | 99.0% |
| **Response Time (p95)** | 500ms | 600ms | 1000ms |
| **Error Rate** | 1.0% | 2.0% | 5.0% |

**Monthly Downtime Budget** (99.9% SLA):
- Total monthly time: 43,200 minutes (30 days)
- Allowed downtime: **43.2 minutes/month**
- Daily budget: ~1.44 minutes/day
- Hourly budget: ~3.6 seconds/hour

### Measurement

**Measure SLAs**:

```python
from mcp_server_langgraph.monitoring.sla import SLAMonitor
from datetime import datetime, timedelta

monitor = SLAMonitor()  # Uses default targets

# Measure uptime
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=30)

uptime = await monitor.measure_uptime(start_time, end_time)
print(f"Uptime: {uptime.measured_value}%")
print(f"Status: {uptime.status.value}")  # MEETING | AT_RISK | BREACH

# Measure response time
response_time = await monitor.measure_response_time(start_time, end_time)
print(f"p95 Response Time: {response_time.measured_value}ms")

# Measure error rate
error_rate = await monitor.measure_error_rate(start_time, end_time)
print(f"Error Rate: {error_rate.measured_value}%")
```

**Generate SLA Report**:

```python
# Comprehensive report with all measurements
report = await monitor.generate_sla_report(period_days=30)

print(f"Overall Status: {report.overall_status.value}")
print(f"Compliance Score: {report.compliance_score:.1f}%")
print(f"Breaches: {report.breaches}")
print(f"Warnings: {report.warnings}")

# Summary with breach details
for breach in report.summary['breaches']:
    print(f"Breach: {breach['metric']} - Target: {breach['target']}, Actual: {breach['actual']}")
```

### Custom SLA Targets

```python
from mcp_server_langgraph.monitoring.sla import SLAMonitor, SLATarget, SLAMetric

custom_targets = [
    SLATarget(
        metric=SLAMetric.UPTIME,
        target_value=99.95,  # Higher target
        comparison=">=",
        unit="%",
        warning_threshold=99.9,
        critical_threshold=99.8
    ),
    SLATarget(
        metric=SLAMetric.RESPONSE_TIME,
        target_value=300,  # Stricter target
        comparison="<=",
        unit="ms",
        warning_threshold=400,
        critical_threshold=600
    )
]

monitor = SLAMonitor(sla_targets=custom_targets)
```

### Prometheus Alert Rules

**20+ Alert Rules** (`monitoring/prometheus/alerts/sla.yaml`):

- **Uptime Alerts**: Breach, at-risk, monthly budget exhaustion, forecasting
- **Response Time Alerts**: p95 breach, p99 degradation
- **Error Rate Alerts**: Breach, at-risk
- **Dependency Alerts**: Critical dependency down, performance degraded
- **Resource Alerts**: High CPU, high memory
- **Composite Score**: Overall SLA compliance

### Implementation Details

**Location**: `src/mcp_server_langgraph/monitoring/sla.py`

**Testing**: `tests/test_sla_monitoring.py` (33 tests, 88% pass rate)

---

## Data Retention

**Automated Data Lifecycle Management**

### Retention Policies

**Default Retention Periods** (`config/retention_policies.yaml`):

| Data Type | Retention Period | Action |
|-----------|------------------|--------|
| User sessions (inactive) | 90 days | Delete |
| Conversations (active) | 365 days | Archive |
| Conversations (archived) | 90 days | Delete |
| Audit logs | 2555 days (7 years) | Keep |
| Consent records | 2555 days (7 years) | Keep |
| Export files | 7 days | Delete |
| Metrics (raw) | 90 days | Aggregate |
| Metrics (aggregated) | 730 days (2 years) | Keep |

### Configuration

**Edit Retention Policies** (`config/retention_policies.yaml`):

```yaml
data_types:
  user_sessions:
    retention_days: 90
    cleanup_action: delete
    description: "Inactive user sessions"

  audit_logs:
    retention_days: 2555  # 7 years for SOC 2
    cleanup_action: archive
    description: "System audit logs"
    exclusions:
      - legal_hold: true
      - compliance_required: true
```

### Automated Cleanup

**Daily Cleanup** (3 AM UTC):

```python
from mcp_server_langgraph.core.compliance.retention import DataRetentionService

service = DataRetentionService(
    session_store=session_store,
    config_path="config/retention_policies.yaml"
)

# Run all cleanups
results = await service.run_all_cleanups(dry_run=False)

for result in results:
    print(f"{result.data_type}: Deleted {result.items_deleted}, Archived {result.items_archived}")
```

### Dry-Run Mode

**Test Before Deleting**:

```python
# Preview what would be deleted (no actual deletion)
results = await service.run_all_cleanups(dry_run=True)

for result in results:
    print(f"Would delete {result.items_deleted} {result.data_type}")
```

### Implementation Details

**Location**:
- Retention Service: `src/mcp_server_langgraph/core/compliance/retention.py`
- Cleanup Scheduler: `src/mcp_server_langgraph/schedulers/cleanup.py`

---

## Audit Logging

**Comprehensive Audit Trail for Compliance**

### Logged Events

**Authentication**:
- Login attempts (success/failure)
- Logout events
- Token creation/verification/refresh
- MFA challenges
- JWKS cache operations

**Authorization**:
- OpenFGA authorization checks
- Role mapping operations
- Permission grants/revocals
- Tuple write/delete operations

**Data Access** (HIPAA PHI):
- Resource access (read/write/delete)
- Patient record access
- Medical data modifications
- Success/failure status

**Compliance**:
- Evidence collection operations
- Compliance report generation
- Access review executions
- SLA measurements
- Data retention cleanup

### Audit Log Format

**Structured JSON Logging**:

```json
{
  "timestamp": "2025-10-13T11:20:40.669589Z",
  "level": "INFO",
  "event": "authentication.login",
  "user_id": "user:john_doe",
  "session_id": "sess_abc123",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "success": true,
  "details": {
    "provider": "keycloak",
    "mfa_used": true
  },
  "trace_id": "0x3abc713685a04488a74cd1853f5c7b8e",
  "span_id": "0xaca45d636afa4414"
}
```

### Retention

**7-Year Retention** (SOC 2 CC6.6):
- Tamper-proof storage
- Append-only logs
- Integrity verification
- SIEM integration ready

---

## Compliance Dashboards

**Real-Time Compliance Monitoring with Grafana**

### SLA Monitoring Dashboard

**URL**: `/d/sla-monitoring/sla-monitoring`

**Key Metrics**:
- Overall SLA compliance score (weighted)
- Uptime percentage (99.9% target)
- Response time p95 (500ms target)
- Error rate (1% target)
- Monthly downtime budget
- 24-hour uptime forecast

**Panels**: 23 panels across 8 row groups

**Refresh**: 30 seconds (real-time monitoring)

### SOC 2 Compliance Dashboard

**URL**: `/d/soc2-compliance/soc2-compliance`

**Key Metrics**:
- Overall compliance score
- Control status distribution (passed/failed/partial)
- Trust Services Criteria evidence
- Evidence collection rate
- Access review findings
- Compliance automation status

**Panels**: 20 panels across 6 row groups

**Refresh**: 1 minute

### Installation

**Option 1: Grafana UI**

```bash
# Navigate to Grafana → Dashboards → Import
# Upload: monitoring/grafana/dashboards/sla-monitoring.json
# Upload: monitoring/grafana/dashboards/soc2-compliance.json
```

**Option 2: Kubernetes ConfigMap**

```bash
kubectl create configmap grafana-dashboards \
  --from-file=monitoring/grafana/dashboards/sla-monitoring.json \
  --from-file=monitoring/grafana/dashboards/soc2-compliance.json \
  -n monitoring
```

**Option 3: Helm**

```yaml
# values.yaml
grafana:
  dashboards:
    langgraph-agent:
      sla-monitoring:
        file: dashboards/sla-monitoring.json
      soc2-compliance:
        file: dashboards/soc2-compliance.json
```

### Documentation

See `monitoring/grafana/dashboards/README.md` for complete dashboard documentation.

---

## Automation & Scheduling

**APScheduler-Based Compliance Automation**

### Scheduled Jobs

**Daily Jobs**:
- **6 AM UTC**: SOC 2 evidence collection
- **3 AM UTC**: Data retention cleanup

**Weekly Jobs**:
- **Monday 9 AM UTC**: Access reviews

**Monthly Jobs**:
- **1st day, 9 AM UTC**: Comprehensive compliance report

### Manual Triggers

**Trigger Jobs Manually**:

```python
from mcp_server_langgraph.schedulers import get_compliance_scheduler

scheduler = get_compliance_scheduler()

# Trigger daily evidence collection
daily_summary = await scheduler.trigger_daily_check()

# Trigger weekly access review
weekly_report = await scheduler.trigger_weekly_review()

# Trigger monthly compliance report
monthly_summary = await scheduler.trigger_monthly_report()
```

### Configuration

**Enable/Disable Automation**:

```python
from mcp_server_langgraph.schedulers import start_compliance_scheduler

# Start scheduler (enabled by default)
await start_compliance_scheduler(
    session_store=session_store,
    evidence_dir=Path("./evidence"),
    enabled=True  # Set to False to disable
)
```

---

## Compliance Reporting

**Audit-Ready Reports for Compliance Auditors**

### SOC 2 Reports

**Monthly Compliance Report**:

```python
from mcp_server_langgraph.core.compliance.evidence import EvidenceCollector

collector = EvidenceCollector(session_store=session_store)
report = await collector.generate_compliance_report(
    report_type="monthly",
    period_days=30
)

# Save report
report_path = f"./evidence/soc2_monthly_{datetime.utcnow().strftime('%Y%m%d')}.json"
with open(report_path, 'w') as f:
    f.write(report.model_dump_json(indent=2))
```

**Report Contents**:
- Report ID and generation timestamp
- Period covered (start/end dates)
- Evidence items (14+ items with status)
- Compliance score (0-100%)
- Passed/failed/partial control counts
- Findings and recommendations
- Summary statistics

### SLA Reports

**Monthly SLA Report**:

```python
from mcp_server_langgraph.monitoring.sla import SLAMonitor

monitor = SLAMonitor()
report = await monitor.generate_sla_report(period_days=30)

# Report includes:
# - Overall SLA status (MEETING, AT_RISK, BREACH)
# - Compliance score (0-100%)
# - Individual measurements (uptime, response time, error rate)
# - Breach details (target, actual, shortfall)
# - Summary statistics
```

### Access Review Reports

**Weekly Access Review**:

```python
from mcp_server_langgraph.schedulers import get_compliance_scheduler

scheduler = get_compliance_scheduler()
report = await scheduler.trigger_weekly_review()

# Report includes:
# - Active vs inactive users
# - Role assignments
# - Session activity
# - Recommendations (e.g., "Disable inactive accounts")
```

---

## Quick Start

**Get Started with Compliance Features in 5 Minutes**

### 1. Enable Compliance Features

**Environment Variables** (`.env`):

```bash
# SOC 2 Evidence Collection
EVIDENCE_DIR=./evidence
ENABLE_COMPLIANCE_AUTOMATION=true

# HIPAA Controls
HIPAA_EMERGENCY_ACCESS_MAX_DURATION=24  # hours
HIPAA_SESSION_TIMEOUT_MINUTES=15

# SLA Monitoring
SLA_UPTIME_TARGET=99.9
SLA_RESPONSE_TIME_TARGET=500  # ms
SLA_ERROR_RATE_TARGET=1.0  # %

# Data Retention
DATA_RETENTION_CONFIG=config/retention_policies.yaml
```

### 2. Start Compliance Automation

```python
from mcp_server_langgraph.schedulers import start_compliance_scheduler
from mcp_server_langgraph.auth.session import get_session_store
from pathlib import Path

# Start automated compliance checks
await start_compliance_scheduler(
    session_store=get_session_store(),
    evidence_dir=Path("./evidence"),
    enabled=True
)
```

### 3. Import Grafana Dashboards

```bash
# Navigate to Grafana UI
# Dashboards → Import

# Import:
# - monitoring/grafana/dashboards/sla-monitoring.json
# - monitoring/grafana/dashboards/soc2-compliance.json
```

### 4. Test GDPR Endpoints

```bash
# Get user data
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/me/data

# Export data
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/users/me/export?format=json \
  -o user_data.json
```

### 5. View Compliance Reports

```bash
# Check evidence directory
ls -lh ./evidence/

# View latest compliance report
cat ./evidence/soc2_monthly_$(date +%Y%m%d).json | jq .

# View SLA measurements
# (Grafana dashboard: /d/sla-monitoring/sla-monitoring)
```

---

## Additional Resources

### Documentation

- **GDPR Details**: `src/mcp_server_langgraph/api/gdpr.py`
- **SOC 2 Evidence**: `src/mcp_server_langgraph/core/compliance/evidence.py`
- **HIPAA Controls**: `src/mcp_server_langgraph/auth/hipaa.py`
- **SLA Monitoring**: `src/mcp_server_langgraph/monitoring/sla.py`
- **Data Retention**: `src/mcp_server_langgraph/core/compliance/retention.py`

### Testing

- **GDPR Tests**: `tests/test_gdpr.py` (30+ tests)
- **SOC 2 Tests**: `tests/test_soc2_evidence.py` (36 tests)
- **SLA Tests**: `tests/test_sla_monitoring.py` (33 tests)

### Configuration

- **Retention Policies**: `config/retention_policies.yaml`
- **Prometheus Alerts**: `monitoring/prometheus/alerts/sla.yaml`
- **Grafana Dashboards**: `monitoring/grafana/dashboards/README.md`

### Changelog

See `CHANGELOG.md` for detailed implementation history and feature additions.

---

**Questions?** See the main documentation or open an issue on GitHub.

**Compliance Version**: v2.2.0
**Last Updated**: 2025-10-13
