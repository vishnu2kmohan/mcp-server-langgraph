# Alert Remediation Operations Runbook

**Reference**: ADR-0026 - Comprehensive Client Resilience Patterns
**Last Updated**: 2025-12-20

---

## Overview

This runbook covers operational procedures for managing alerts through the Admin Dashboard,
using AI-powered recommendations for root cause analysis, and executing approved remediations.

### Alert Flow

```
Mimir/Alertmanager → Webhook → Admin Dashboard → AI Analysis → Human Approval → Execution
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Admin Dashboard | `/studio/admin` | Alert management UI |
| Alerts Tab | Admin Dashboard → "Alerts" | View and manage alerts |
| AI Recommendations | Alert Detail Panel | Root cause analysis |
| Remediation Dialog | Alert Detail → "Execute" | Approve/reject actions |

---

## Accessing the Alert Dashboard

### Prerequisites

1. **Admin Role**: User must have `admin` role in Keycloak
2. **Authentication**: Must be logged in via SSO
3. **Feature Flag**: `FF_CANVAS_HYBRID_SHELL=true` (enabled by default)

### Navigation

1. Log in to the Studio at `/studio`
2. Click on your profile icon → "Admin Dashboard"
3. Select the "Alerts" tab

### Alert Badge

The header shows an alert badge with the count of active critical + warning alerts:
- **Red badge**: Critical alerts present
- **Yellow badge**: Only warning alerts
- **No badge**: No active alerts

---

## Understanding Alert States

### Severity Levels

| Severity | Description | Sound | Pre-compute AI |
|----------|-------------|-------|----------------|
| **Critical** | Service degradation or outage | Yes | Yes (immediate) |
| **Warning** | Potential issues, needs attention | No | On demand |
| **Info** | Informational only | No | No |

### Alert States

| State | Description | UI Indicator |
|-------|-------------|--------------|
| **Firing** | Alert is active | Red dot |
| **Resolved** | Alert condition cleared | Green checkmark |
| **Silenced** | Manually suppressed | Gray icon |

---

## Using AI Recommendations

### Viewing Recommendations

1. Click on an alert in the AlertsPanel list
2. The AlertDetailPanel opens with alert metadata
3. Scroll to "AI Recommendation" section
4. View:
   - **Root Cause Analysis**: Explanation of what caused the alert
   - **Remediation Steps**: Ordered actions to resolve
   - **Risk Assessment**: Impact and urgency levels

### Recommendation Timing

| Alert Type | Recommendation Available |
|------------|-------------------------|
| Critical | Immediately (pre-computed) |
| Warning | ~2-5 seconds (on demand) |
| Regenerated | ~2-5 seconds |

### Regenerating Recommendations

If the recommendation seems stale or you want fresh analysis:
1. Click "Regenerate" button in AIRecommendationCard
2. Wait for new LLM response (~2-5 seconds)
3. Review updated analysis

---

## Remediation Approval Workflow

### Step 1: Review the Recommendation

Before approving any remediation:
- [ ] Read the full root cause analysis
- [ ] Understand each remediation step
- [ ] Check the risk level (low/medium/high)
- [ ] Verify the commands are appropriate

### Step 2: Initiate Approval

1. Click "Execute" button on a remediation step
2. RemediationApprovalDialog opens
3. Review the command to be executed

### Step 3: Approve or Reject

**To Approve**:
1. Optionally add approval notes
2. Click "Approve & Execute"
3. Monitor execution result in the dialog

**To Reject**:
1. Provide rejection reason (required)
2. Click "Reject"
3. The remediation is marked as rejected

### Step 4: Verify Execution

After approval:
1. Watch for execution result (success/failure)
2. Check stdout/stderr for command output
3. Verify the alert resolves (may take 1-5 minutes)

---

## Common Alert Scenarios

### 1. CircuitBreakerOpen (Critical)

**Symptoms**: Service unavailable, fast-fail responses

**AI Recommendation Pattern**:
```
Root Cause: [Service] has exceeded failure threshold (5 failures)
Remediation:
1. Check service logs: kubectl logs -l app=[service]
2. Verify service health: kubectl get pods -l app=[service]
3. If unhealthy: kubectl rollout restart deployment/[service]
```

**Manual Actions**:
```bash
# Check circuit breaker state
curl http://mcp-server:8000/health/ready | jq .resilience_stats.circuit_breakers

# Force reset (if needed - will recover automatically in 30s)
# Restart the MCP server to reset all circuit breakers
kubectl rollout restart deployment/mcp-server-langgraph
```

### 2. HTTPPoolExhausted (Critical)

**Symptoms**: Connection timeouts, request queueing

**AI Recommendation Pattern**:
```
Root Cause: HTTP connection pool at 100% capacity
Remediation:
1. Scale horizontally: kubectl scale deployment/mcp-server --replicas=3
2. Check for connection leaks in recent deploys
3. Increase pool size: HTTP_POOL_MAX_CONNECTIONS=200
```

**Manual Actions**:
```bash
# Check pool metrics
curl http://mcp-server:8000/health/ready | jq .resilience_stats

# Scale deployment
kubectl scale deployment/mcp-server-langgraph --replicas=3
```

### 3. AdaptiveBulkheadAtFloor (Warning)

**Symptoms**: LLM requests throttled, slow AI responses

**AI Recommendation Pattern**:
```
Root Cause: Provider [name] error rate triggered AIMD floor
Remediation:
1. Check provider status: https://status.[provider].com
2. Switch to fallback provider temporarily
3. Wait for error rate recovery (automatic)
```

**Manual Actions**:
```bash
# Check current bulkhead limits
curl http://mcp-server:8000/health/ready | jq .resilience_stats.adaptive_bulkheads

# If one provider is at floor, requests will use fallback automatically
```

### 4. RateLimitTokenExhaustion (Warning)

**Symptoms**: Delayed LLM requests, wait time increasing

**AI Recommendation Pattern**:
```
Root Cause: Provider [name] rate limit bucket exhausted
Remediation:
1. Wait for token replenishment (automatic)
2. Distribute load across providers
3. Consider increasing rate limit quota with provider
```

**Manual Actions**:
```bash
# Check rate limit status
curl http://mcp-server:8000/metrics | grep rate_limit

# Adjust rate limit (requires restart)
export RATE_LIMIT_OPENAI_RPM=1000
kubectl rollout restart deployment/mcp-server-langgraph
```

### 5. RetryExhaustionHigh (Warning)

**Symptoms**: Persistent failures, degraded experience

**AI Recommendation Pattern**:
```
Root Cause: Transient errors not recovering after retries
Remediation:
1. Check service dependency health
2. Review network connectivity
3. Check for configuration changes
```

---

## Sound Notifications

### Enabling/Disabling

1. Navigate to Admin Dashboard → Alerts tab
2. Click the speaker icon in the panel header
3. Toggle enables/disables sound for critical alerts

### Sound Behavior

- **Trigger**: New critical alert arrives via WebSocket
- **Audio**: 440Hz beep (0.3 seconds)
- **Persistence**: Preference saved in localStorage
- **Default**: Disabled

---

## Troubleshooting

### No Alerts Appearing

1. **Check WebSocket connection**: Look for "Connected" indicator
2. **Verify Mimir webhook**: Check Mimir logs for webhook delivery
3. **Check permissions**: User must have admin role

```bash
# Check webhook delivery
kubectl logs -l app=mimir | grep webhook

# Test webhook manually
curl -X POST http://mcp-server:8000/api/v1/webhooks/alertmanager \
  -H "Content-Type: application/json" \
  -d '{"alerts": [{"status": "firing", "labels": {"alertname": "Test", "severity": "warning"}}]}'
```

### AI Recommendation Not Loading

1. **Check LLM configuration**: Verify `LITELLM_*` environment variables
2. **Check rate limits**: May be throttled by provider
3. **Check logs**: Look for LLM errors

```bash
# Check LLM configuration
kubectl get deployment/mcp-server-langgraph -o jsonpath='{.spec.template.spec.containers[0].env[*]}' | grep -i llm

# Check recommendation service logs
kubectl logs -l app=mcp-server-langgraph | grep -i recommendation
```

### Remediation Execution Failed

1. **Check command validation**: May be blocked by security rules
2. **Check permissions**: Service account may lack RBAC
3. **Check timeout**: Command may have exceeded 5-minute limit

```bash
# Check executor logs
kubectl logs -l app=mcp-server-langgraph | grep -i executor

# Verify RBAC for remediation commands
kubectl auth can-i delete pods --as=system:serviceaccount:default:mcp-server
```

---

## API Reference

### List Alerts

```bash
curl http://mcp-server:8000/api/v1/alerts?severity=critical,warning
```

### Get Recommendation

```bash
curl http://mcp-server:8000/api/v1/alerts/{alert_id}/recommendation
```

### Regenerate Recommendation

```bash
curl -X POST http://mcp-server:8000/api/v1/alerts/{alert_id}/recommendation/regenerate
```

### List Pending Remediations

```bash
curl http://mcp-server:8000/api/v1/remediations/pending
```

### Approve Remediation

```bash
curl -X POST http://mcp-server:8000/api/v1/remediations/{id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved_by": "admin@example.com", "notes": "Approved per incident #123"}'
```

### Reject Remediation

```bash
curl -X POST http://mcp-server:8000/api/v1/remediations/{id}/reject \
  -H "Content-Type: application/json" \
  -d '{"rejected_by": "admin@example.com", "reason": "Needs manual review first"}'
```

---

## Security Considerations

### Command Validation

All remediation commands are validated before execution:

**Allowed Command Prefixes**:
- `kubectl` - Kubernetes operations
- `helm` - Helm chart management
- `docker` - Container operations
- `aws` - AWS CLI
- `gcloud` - Google Cloud CLI
- `az` - Azure CLI
- `echo` - Testing/debugging

**Blocked Patterns**:
- `rm -rf` - Destructive operations
- `sudo rm` - Elevated destructive operations
- `| bash` / `| sh` - Piped script execution
- `mkfs` - Filesystem formatting
- `dd if=` - Raw disk operations
- `chmod 777` / `chmod -R 777` - Insecure permissions
- `iptables -F` - Firewall flush

### Audit Trail

All remediation actions are logged:
- Who approved/rejected
- When the action was taken
- What command was executed
- Execution result (success/failure)

Access audit logs:
```bash
kubectl logs -l app=mcp-server-langgraph | grep -i "remediation"
```

---

## Escalation Procedures

### When to Escalate

1. **Critical alert persists > 15 minutes** after remediation
2. **Multiple critical alerts** firing simultaneously
3. **AI recommendation fails** repeatedly
4. **Remediation execution** repeatedly fails

### Escalation Path

1. **L1 - On-call Engineer**: Initial response, execute approved remediations
2. **L2 - Platform Team**: Complex troubleshooting, infrastructure issues
3. **L3 - Engineering Lead**: Architectural issues, code changes required

### Incident Bridge

For critical escalations:
1. Create incident in PagerDuty/OpsGenie
2. Start incident bridge call
3. Document actions in incident timeline
4. Post-incident: Update runbook with learnings

---

## Related Documentation

- [ADR-0026: Comprehensive Client Resilience Patterns](../ADR-0026-RESILIENCE-PATTERNS.md)
- [Resilience Operations Runbook](./RESILIENCE_OPERATIONS.md)
- [Grafana Dashboard](../dashboards/resilience-patterns.json)
- [Alerting Rules](../../deployments/monitoring/alerting-rules/resilience-alerts.yaml)
