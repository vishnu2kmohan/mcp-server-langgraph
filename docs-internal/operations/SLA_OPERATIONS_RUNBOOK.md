# SLA Monitoring Operations Runbook

**MCP Server with LangGraph - SLA Incident Response Guide**

This runbook provides step-by-step procedures for responding to SLA breaches and managing service level objectives.

---

## Table of Contents

- [Overview](#overview)
- [SLA Targets](#sla-targets)
- [Alert Severity Levels](#alert-severity-levels)
- [Incident Response Procedures](#incident-response-procedures)
  - [Uptime SLA Breach](#uptime-sla-breach)
  - [Response Time SLA Breach](#response-time-sla-breach)
  - [Error Rate SLA Breach](#error-rate-sla-breach)
  - [Dependency Issues](#dependency-issues)
  - [Resource Exhaustion](#resource-exhaustion)
- [Monitoring & Dashboards](#monitoring--dashboards)
- [Monthly SLA Reporting](#monthly-sla-reporting)
- [Post-Incident Review](#post-incident-review)
- [Escalation Procedures](#escalation-procedures)

---

## Overview

This runbook covers operational procedures for managing Service Level Agreements (SLAs) for the MCP Server with LangGraph.

**SLA Owner**: Operations Team
**On-Call Rotation**: 24/7 coverage
**Escalation Path**: On-Call → Team Lead → VP Engineering

---

## SLA Targets

### Production SLA Commitments

| Metric | Target | Warning Threshold | Critical Threshold | Monthly Budget |
|--------|--------|-------------------|-------------------|----------------|
| **System Uptime** | 99.9% | 99.5% | 99.0% | 43.2 min downtime/month |
| **API Response Time (p95)** | <500ms | 600ms | 1000ms | N/A |
| **Error Rate** | <1.0% | 2.0% | 5.0% | N/A |

### Downtime Budget

**99.9% SLA allows**:
- **Monthly**: 43.2 minutes downtime
- **Weekly**: ~10.1 minutes downtime
- **Daily**: ~1.44 minutes downtime
- **Hourly**: ~4.3 seconds downtime

**Track budget**:
```bash
# View remaining downtime budget in Grafana
# Dashboard: SLA Monitoring → Monthly Downtime Budget Remaining
```

---

## Alert Severity Levels

### Critical Alerts (Page Immediately)

- `SLAUptimeBreach` - Uptime < 99.9% for 5 minutes
- `SLAResponseTimeBreach` - p95 > 500ms for 10 minutes
- `SLAErrorRateBreach` - Error rate > 1% for 5 minutes
- `SLADependencyDown` - Critical dependency offline
- `SLAMonthlyUptimeBudgetExhausted` - >80% of monthly budget used

### Warning Alerts (Notify Team)

- `SLAUptimeAtRisk` - Uptime between 99.5-99.9%
- `SLAResponseTimeAtRisk` - p95 between 400-500ms
- `SLAErrorRateAtRisk` - Error rate between 0.5-1%
- `SLAProjectedBreach` - Forecasted breach in 24 hours
- `SLAResourceCPUHigh` - CPU > 80%
- `SLAResourceMemoryHigh` - Memory > 80%

---

## Incident Response Procedures

### Uptime SLA Breach

**Alert**: `SLAUptimeBreach`
**Severity**: Critical
**Page**: Yes

#### Symptoms

- System uptime < 99.9% for 5+ minutes
- Pods restarting frequently
- Health check failures

#### Immediate Actions (5 minutes)

1. **Acknowledge Alert**
   ```bash
   # Silence alert for 30 minutes
   curl -X POST http://alertmanager:9093/api/v1/silences \
     -d '{"matchers":[{"name":"alertname","value":"SLAUptimeBreach"}],"startsAt":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'","endsAt":"'$(date -u -d '+30 minutes' +%Y-%m-%dT%H:%M:%SZ)'","createdBy":"oncall","comment":"Investigating uptime breach"}'
   ```

2. **Check System Status**
   ```bash
   # Check pod status
   kubectl get pods -n production -l app=mcp-server-langgraph

   # Check recent events
   kubectl get events -n production --sort-by='.lastTimestamp' | tail -20

   # Check logs for errors
   kubectl logs -n production -l app=mcp-server-langgraph --tail=100 | grep ERROR
   ```

3. **Check Dependencies**
   ```bash
   # Verify critical dependencies
   kubectl get pods -n production -l app in (postgres,redis,openfga,keycloak)

   # Test connectivity
   kubectl exec -n production deploy/mcp-server-langgraph -- curl -s http://postgres:5432
   kubectl exec -n production deploy/mcp-server-langgraph -- curl -s http://redis:6379
   kubectl exec -n production deploy/mcp-server-langgraph -- curl -s http://openfga:8080/healthz
   kubectl exec -n production deploy/mcp-server-langgraph -- curl -s http://keycloak:8080/health
   ```

#### Investigation (15 minutes)

4. **Review Grafana Dashboards**
   - **SLA Monitoring Dashboard**: Check uptime trend, identify when breach started
   - **Overview Dashboard**: CPU, memory, request rate patterns
   - **Dependency Dashboards**: Postgres, Redis, OpenFGA, Keycloak status

5. **Check Prometheus Metrics**
   ```promql
   # Uptime percentage
   (sum(up{job="mcp-server-langgraph"}) / count(up{job="mcp-server-langgraph"}) * 100)

   # Pod restart count
   increase(kube_pod_container_status_restarts_total{pod=~"mcp-server-langgraph.*"}[1h])

   # Recent errors
   rate(http_requests_total{job="mcp-server-langgraph",status=~"5.."}[5m])
   ```

6. **Identify Root Cause**
   - Pod crashes (OOMKilled, CrashLoopBackOff)
   - Dependency failures (DB connection errors)
   - Resource exhaustion (CPU/memory limits)
   - Network issues (timeouts, connection refused)

#### Resolution

7. **Apply Fix Based on Root Cause**

   **Pod Crashes**:
   ```bash
   # Increase resources
   kubectl patch deployment mcp-server-langgraph -n production \
     -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","resources":{"limits":{"memory":"2Gi","cpu":"2000m"}}}]}}}}'

   # Restart deployment
   kubectl rollout restart deployment/mcp-server-langgraph -n production
   ```

   **Dependency Failures**:
   ```bash
   # Restart dependency
   kubectl rollout restart deployment/postgres -n production

   # Verify connection
   kubectl exec -n production deploy/mcp-server-langgraph -- pg_isready -h postgres
   ```

   **Configuration Issues**:
   ```bash
   # Rollback to previous version
   kubectl rollout undo deployment/mcp-server-langgraph -n production
   ```

8. **Verify Recovery**
   ```bash
   # Check uptime percentage (should be increasing)
   # Grafana: SLA Monitoring → Uptime SLA Gauge

   # Verify all pods are running
   kubectl get pods -n production -l app=mcp-server-langgraph

   # Test health endpoint
   curl https://api.example.com/health
   ```

#### Communication

9. **Update Status Page**
   ```bash
   # Post incident update
   # Status page: https://status.example.com
   # Template: "Investigating elevated error rates affecting API uptime. Engineers are actively working on resolution."
   ```

10. **Notify Stakeholders**
    - **Slack**: #incidents channel
    - **Email**: engineering@example.com
    - **PagerDuty**: Update incident notes

#### Documentation

11. **Create Incident Record**
    ```bash
    # Create incident report
    cat > incidents/$(date +%Y%m%d)_uptime_breach.md <<EOF
    # Incident: Uptime SLA Breach

    **Date**: $(date)
    **Alert**: SLAUptimeBreach
    **Duration**: X minutes
    **Root Cause**: [Description]
    **Resolution**: [Description]
    **Impact**: Uptime dropped to X%
    **Downtime Budget Used**: X minutes
    **Lessons Learned**: [Action items]
    EOF
    ```

---

### Response Time SLA Breach

**Alert**: `SLAResponseTimeBreach`
**Severity**: Critical
**Page**: Yes

#### Symptoms

- API p95 response time > 500ms for 10+ minutes
- Slow user-facing operations
- Timeout errors

#### Immediate Actions (5 minutes)

1. **Acknowledge Alert** (same as above)

2. **Check Current Performance**
   ```bash
   # Query current p95 latency
   curl -s 'http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket{job="mcp-server-langgraph"}[5m]))*1000' | jq .

   # Check slow requests in logs
   kubectl logs -n production -l app=mcp-server-langgraph --tail=100 | grep -E "duration=[0-9]+ms" | sort -t= -k2 -n | tail -20
   ```

3. **Identify Slow Operations**
   ```promql
   # Top 5 slowest endpoints
   topk(5,
     histogram_quantile(0.95,
       sum by (path) (rate(http_request_duration_seconds_bucket{job="mcp-server-langgraph"}[5m]))
     )
   ) * 1000

   # Slowest LLM operations
   topk(5,
     histogram_quantile(0.95,
       sum by (model) (rate(llm_request_duration_seconds_bucket[5m]))
     )
   ) * 1000
   ```

#### Investigation (15 minutes)

4. **Check Resource Utilization**
   ```bash
   # CPU usage
   kubectl top pods -n production -l app=mcp-server-langgraph

   # Database queries
   kubectl exec -n production deploy/postgres -- psql -c "SELECT pid, now() - query_start as duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC LIMIT 10;"

   # Redis latency
   kubectl exec -n production deploy/redis -- redis-cli --latency-history
   ```

5. **Review Grafana Dashboards**
   - **SLA Monitoring**: Response time percentiles trend
   - **LLM Performance**: Model latency, fallback activations
   - **Dependencies**: Database, Redis, OpenFGA latency

6. **Identify Root Cause**
   - Database slow queries (missing indexes, table scans)
   - LLM API latency (provider issues, rate limiting)
   - Memory pressure (GC pauses, swapping)
   - Network latency (dependency communication)
   - High request volume (traffic spike)

#### Resolution

7. **Apply Fix Based on Root Cause**

   **Database Slow Queries**:
   ```bash
   # Add missing index
   kubectl exec -n production deploy/postgres -- psql -c "CREATE INDEX CONCURRENTLY idx_sessions_user_id ON sessions(user_id);"

   # Analyze and vacuum
   kubectl exec -n production deploy/postgres -- psql -c "ANALYZE VERBOSE; VACUUM ANALYZE;"
   ```

   **LLM Provider Issues**:
   ```bash
   # Force fallback to backup model
   kubectl set env deployment/mcp-server-langgraph -n production \
     PRIMARY_MODEL=gpt-4o-mini FALLBACK_MODEL=claude-3-5-sonnet-20241022
   ```

   **Memory Pressure**:
   ```bash
   # Increase memory limits
   kubectl patch deployment mcp-server-langgraph -n production \
     -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
   ```

   **High Request Volume**:
   ```bash
   # Scale up replicas
   kubectl scale deployment mcp-server-langgraph -n production --replicas=10

   # Enable autoscaling
   kubectl autoscale deployment mcp-server-langgraph -n production --min=5 --max=20 --cpu-percent=70
   ```

8. **Verify Recovery**
   ```promql
   # Check p95 latency (should be decreasing)
   histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="mcp-server-langgraph"}[5m])) * 1000

   # Monitor for 10 minutes
   ```

---

### Error Rate SLA Breach

**Alert**: `SLAErrorRateBreach`
**Severity**: Critical
**Page**: Yes

#### Symptoms

- API error rate > 1% for 5+ minutes
- 5xx status codes
- Application errors in logs

#### Immediate Actions (5 minutes)

1. **Acknowledge Alert** (same as above)

2. **Identify Error Types**
   ```bash
   # Top error status codes
   kubectl logs -n production -l app=mcp-server-langgraph --tail=1000 | grep -E "status=(5[0-9]{2})" | sort | uniq -c | sort -rn | head -10

   # Recent exception stack traces
   kubectl logs -n production -l app=mcp-server-langgraph --tail=100 | grep -A 10 "Traceback"
   ```

3. **Check Error Rate by Endpoint**
   ```promql
   # Errors per endpoint
   topk(10,
     sum by (path) (rate(http_requests_total{job="mcp-server-langgraph",status=~"5.."}[5m]))
   )
   ```

#### Investigation (15 minutes)

4. **Analyze Error Patterns**
   - **500 Internal Server Error**: Application bugs, unhandled exceptions
   - **502 Bad Gateway**: Upstream dependency failures
   - **503 Service Unavailable**: Resource exhaustion, rate limiting
   - **504 Gateway Timeout**: Slow operations timing out

5. **Check Dependencies**
   ```bash
   # Database connectivity
   kubectl exec -n production deploy/mcp-server-langgraph -- curl -f http://postgres:5432 || echo "DB unreachable"

   # OpenFGA availability
   kubectl exec -n production deploy/mcp-server-langgraph -- curl -f http://openfga:8080/healthz || echo "OpenFGA unreachable"

   # LLM provider status
   curl -s https://status.anthropic.com/api/v2/status.json | jq .
   curl -s https://status.openai.com/api/v2/status.json | jq .
   ```

6. **Identify Root Cause**
   - Application bugs (recent deployment)
   - Dependency failures (DB, Redis, OpenFGA down)
   - LLM provider outages
   - Configuration errors
   - Resource exhaustion

#### Resolution

7. **Apply Fix Based on Root Cause**

   **Application Bugs**:
   ```bash
   # Rollback to last known good version
   kubectl rollout undo deployment/mcp-server-langgraph -n production

   # Verify rollback
   kubectl rollout status deployment/mcp-server-langgraph -n production
   ```

   **Dependency Failures**:
   ```bash
   # Restart failed dependency
   kubectl rollout restart deployment/openfga -n production

   # Wait for ready
   kubectl wait --for=condition=ready pod -l app=openfga -n production --timeout=300s
   ```

   **LLM Provider Outages**:
   ```bash
   # Switch to backup provider
   kubectl set env deployment/mcp-server-langgraph -n production \
     PRIMARY_MODEL=claude-3-5-sonnet-20241022 FALLBACK_MODEL=gpt-4o-mini
   ```

8. **Verify Recovery**
   ```promql
   # Check error rate (should be decreasing)
   (sum(rate(http_requests_total{job="mcp-server-langgraph",status=~"5.."}[5m]))
   / sum(rate(http_requests_total{job="mcp-server-langgraph"}[5m]))) * 100

   # Monitor for 10 minutes
   ```

---

### Dependency Issues

**Alert**: `SLADependencyDown` or `SLADependencyDegraded`
**Severity**: Critical / Warning

#### Procedure

1. **Identify Failed Dependency**
   ```bash
   # Check all dependencies
   kubectl get pods -n production | grep -E "postgres|redis|openfga|keycloak"
   ```

2. **Restart Dependency**
   ```bash
   # Restart the failed service
   kubectl rollout restart deployment/<dependency-name> -n production
   ```

3. **Verify Recovery**
   ```bash
   # Test connectivity
   kubectl exec -n production deploy/mcp-server-langgraph -- curl -f http://<dependency>:<port>/health
   ```

4. **Check Impact on SLAs**
   - **Grafana**: SLA Monitoring → Dependency Health Status
   - Monitor uptime, response time, error rate for degradation

---

### Resource Exhaustion

**Alert**: `SLAResourceCPUHigh` or `SLAResourceMemoryHigh`
**Severity**: Warning

#### Procedure

1. **Check Resource Usage**
   ```bash
   # Current resource utilization
   kubectl top pods -n production -l app=mcp-server-langgraph

   # Resource limits
   kubectl describe pod -n production -l app=mcp-server-langgraph | grep -A 5 "Limits:"
   ```

2. **Scale Up Resources**
   ```bash
   # Increase CPU/memory limits
   kubectl patch deployment mcp-server-langgraph -n production \
     -p '{"spec":{"template":{"spec":{"containers":[{"name":"mcp-server","resources":{"limits":{"cpu":"4000m","memory":"8Gi"},"requests":{"cpu":"2000m","memory":"4Gi"}}}]}}}}'
   ```

3. **Scale Horizontally**
   ```bash
   # Add more replicas
   kubectl scale deployment mcp-server-langgraph -n production --replicas=10
   ```

4. **Monitor Impact**
   - **Grafana**: SLA Monitoring → CPU/Memory Utilization
   - Verify resource usage decreases below warning threshold (80%)

---

## Monitoring & Dashboards

### Primary Dashboards

1. **SLA Monitoring Dashboard**
   - URL: `https://grafana.example.com/d/sla-monitoring/sla-monitoring`
   - Refresh: 30 seconds
   - Key Metrics: Uptime, response time, error rate, dependencies

2. **Overview Dashboard**
   - URL: `https://grafana.example.com/d/langgraph-agent/overview`
   - Refresh: 10 seconds
   - Key Metrics: Request rate, CPU, memory, pod status

3. **Alertmanager**
   - URL: `https://alertmanager.example.com`
   - View active alerts, silence alerts, acknowledge incidents

### Key Metrics to Monitor

**Prometheus Queries**:

```promql
# System uptime percentage
(sum(up{job="mcp-server-langgraph"}) / count(up{job="mcp-server-langgraph"})) * 100

# P95 response time (ms)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="mcp-server-langgraph"}[5m])) * 1000

# Error rate percentage
(sum(rate(http_requests_total{job="mcp-server-langgraph",status=~"5.."}[5m]))
/ sum(rate(http_requests_total{job="mcp-server-langgraph"}[5m]))) * 100

# Remaining downtime budget (minutes)
43.2 - ((time() - (time() - time() % (30 * 24 * 3600))) * (1 - (sum(up{job="mcp-server-langgraph"}) / count(up{job="mcp-server-langgraph"})))) / 60
```

---

## Monthly SLA Reporting

### Generate Monthly Report

**Python Script**:

```python
from mcp_server_langgraph.monitoring.sla import SLAMonitor
from datetime import datetime, timedelta
import json

# Initialize SLA monitor
monitor = SLAMonitor()

# Generate 30-day report
report = await monitor.generate_sla_report(period_days=30)

# Save report
report_path = f"sla_reports/monthly_{datetime.utcnow().strftime('%Y%m')}.json"
with open(report_path, 'w') as f:
    f.write(report.model_dump_json(indent=2))

# Print summary
print(f"=== Monthly SLA Report ===")
print(f"Period: {report.period_start} to {report.period_end}")
print(f"Overall Status: {report.overall_status.value}")
print(f"Compliance Score: {report.compliance_score:.1f}%")
print(f"Breaches: {report.breaches}")
print(f"Warnings: {report.warnings}")
print(f"\nDetailed Summary:")
print(f"  Uptime: {report.summary['uptime_percentage']:.2f}%")
print(f"  Response Time (p95): {report.summary['response_time_p95_ms']:.0f}ms")
print(f"  Error Rate: {report.summary['error_rate_percentage']:.2f}%")

if report.breaches > 0:
    print(f"\nSLA Breaches:")
    for breach in report.summary['breaches']:
        print(f"  - {breach['metric']}: Target {breach['target']}, Actual {breach['actual']}")
```

### Stakeholder Communication

**Email Template**:

```
Subject: Monthly SLA Report - [Month Year]

Hello Team,

Here is the SLA performance summary for [Month Year]:

**Overall SLA Compliance: [X]%**

Metrics:
- Uptime: [X]% (Target: 99.9%)
- Response Time (p95): [X]ms (Target: <500ms)
- Error Rate: [X]% (Target: <1%)

**SLA Status**: [MEETING | AT_RISK | BREACH]

Downtime Budget:
- Monthly Budget: 43.2 minutes
- Used: [X] minutes
- Remaining: [X] minutes

[If breaches occurred:]
Breaches:
- [Date]: [Description] - Duration: [X] minutes
  Root Cause: [Description]
  Resolution: [Description]

Action Items:
- [Action item 1]
- [Action item 2]

Full report: [Link to JSON report]

Dashboards: https://grafana.example.com/d/sla-monitoring/sla-monitoring

Best regards,
Operations Team
```

---

## Post-Incident Review

### Post-Incident Review Template

Create a detailed PIR within 48 hours of major incidents:

```markdown
# Post-Incident Review: [Incident Title]

## Incident Summary

- **Date**: YYYY-MM-DD
- **Duration**: X hours Y minutes
- **Severity**: [Critical | High | Medium | Low]
- **SLA Impact**: [Uptime | Response Time | Error Rate]
- **Business Impact**: [Description]

## Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM | Alert fired: SLAUptimeBreach |
| HH:MM | On-call acknowledged |
| HH:MM | Root cause identified |
| HH:MM | Fix applied |
| HH:MM | Service recovered |
| HH:MM | Incident closed |

## Root Cause Analysis

**What happened?**
[Detailed description]

**Why did it happen?**
[Root cause analysis - 5 whys]

**Contributing factors:**
- [Factor 1]
- [Factor 2]

## Impact

**SLA Metrics**:
- Uptime: X% (dropped from Y%)
- Downtime: X minutes
- Error rate: X%

**Customer Impact**:
- [Number] users affected
- [Number] failed requests
- [Description of user experience]

## Resolution

**Immediate Fix**:
[What was done to restore service]

**Verification**:
[How recovery was verified]

## Action Items

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| [Action 1] | @engineer | YYYY-MM-DD | High |
| [Action 2] | @engineer | YYYY-MM-DD | Medium |
| [Action 3] | @manager | YYYY-MM-DD | High |

## Lessons Learned

**What went well:**
- [Item 1]
- [Item 2]

**What could be improved:**
- [Item 1]
- [Item 2]

**Prevention measures:**
- [Measure 1]
- [Measure 2]
```

---

## Escalation Procedures

### Escalation Path

**Level 1: On-Call Engineer** (Initial Response)
- Acknowledge alert within 5 minutes
- Begin investigation
- Apply immediate fixes
- Escalate if needed

**Level 2: Team Lead** (Complex Issues)
- Escalate if:
  - Incident duration > 30 minutes
  - Root cause unclear
  - Fix requires architecture changes
  - Multiple SLAs breached simultaneously

**Level 3: VP Engineering** (Critical Incidents)
- Escalate if:
  - Incident duration > 1 hour
  - Downtime budget > 50% exhausted
  - Customer escalation
  - Security incident

**Level 4: CEO** (Company-Wide Impact)
- Escalate if:
  - Major customer impact
  - Reputational risk
  - Legal implications

### Contact Information

```
On-Call Rotation: PagerDuty
Team Lead: [Email] [Phone]
VP Engineering: [Email] [Phone]
CEO: [Email] [Phone]

Emergency Hotline: [Phone Number]
Slack: #incidents
Status Page: https://status.example.com
```

---

## Appendix

### Useful Commands

**Quick Diagnostics**:
```bash
# Check all services
kubectl get all -n production

# View recent logs
kubectl logs -n production -l app=mcp-server-langgraph --tail=100 --timestamps

# Describe pod for events
kubectl describe pod -n production <pod-name>

# Execute into pod
kubectl exec -it -n production <pod-name> -- /bin/bash

# Port forward for local debugging
kubectl port-forward -n production svc/mcp-server-langgraph 8000:8000
```

**Grafana API**:
```bash
# Get dashboard
curl -H "Authorization: Bearer $GRAFANA_API_KEY" \
  https://grafana.example.com/api/dashboards/uid/sla-monitoring

# Create annotation (incident marker)
curl -X POST -H "Authorization: Bearer $GRAFANA_API_KEY" \
  -H "Content-Type: application/json" \
  https://grafana.example.com/api/annotations \
  -d '{"text":"Incident: Uptime breach","tags":["incident","sla"]}'
```

---

**Runbook Version**: 1.0
**Last Updated**: 2025-10-13
**Next Review**: 2025-11-13
