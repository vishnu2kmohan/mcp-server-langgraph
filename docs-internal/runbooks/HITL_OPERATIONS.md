# Human-in-the-Loop (HITL) Operations Runbook

**Reference**: Plan - Confidence-Based HITL for Multi-Agent Orchestrator
**Last Updated**: 2025-12-21

---

## Overview

This runbook covers operational procedures for monitoring, troubleshooting, and tuning the Human-in-the-Loop (HITL) system that enables agents to pause for human approval when confidence drops below configurable thresholds.

### HITL Components

| Component | Purpose | Key Metrics |
|-----------|---------|-------------|
| Confidence Tracking | Measure agent decision confidence | `agent.hitl.trigger.confidence` |
| Approval Requests | Pause agents for human review | `agent.hitl.request.count` |
| Decision Recording | Track approval/rejection outcomes | `agent.hitl.decision.count` |
| Response Latency | Measure time to human response | `agent.hitl.response.latency` |
| Pending Queue | Track waiting approvals | `agent.hitl.pending.count` |

### Dashboard

**Grafana Dashboard**: [HITL Metrics](https://grafana/d/hitl-metrics)

---

## Alert Response Procedures

### HITLInterventionRateHigh

**Severity**: Warning
**Threshold**: >30% of tasks require human intervention for 10+ minutes

#### Symptoms
- High volume of approval requests
- Agents frequently pausing for human review
- Reduced automation efficiency

#### Diagnosis

```promql
# Intervention rate by agent
sum by (agent_name) (rate(agent_hitl_request_count_total[5m]))
/
sum by (agent_name) (rate(agent_task_total[5m]))

# Trigger reason breakdown
sum by (trigger_reason) (rate(agent_hitl_request_count_total[5m]))

# Confidence distribution (median)
histogram_quantile(0.50, sum by (le, agent_name) (rate(agent_hitl_trigger_confidence_bucket[5m])))
```

#### Resolution

1. **Identify affected agents**:
   ```bash
   # Check agent-specific intervention rates
   curl -s "http://prometheus:9090/api/v1/query?query=sum%20by%20(agent_name)%20(rate(agent_hitl_request_count_total[1h]))" | jq
   ```

2. **Review trigger reasons**:
   - `low_confidence`: Consider adjusting confidence threshold
   - `destructive_action`: Expected for high-risk operations
   - `external_api`: Review which APIs require approval
   - `policy_required`: Check organizational policies

3. **Tune thresholds**:
   ```python
   # Adjust per-agent threshold via feature flags
   FF_AGENT_HITL_CONFIDENCE_THRESHOLD=0.6  # Lower threshold = fewer approvals
   ```

4. **Review agent prompts**:
   - Check if agent prompts are clear and specific
   - Improve context provided to agents
   - Add examples for ambiguous scenarios

---

### HITLInterventionRateCritical

**Severity**: Critical
**Threshold**: >50% of tasks require human intervention for 5+ minutes

#### Immediate Actions

1. **Consider temporary disabling**:
   ```bash
   # Disable HITL for specific agent
   kubectl set env deployment/mcp-server FF_AGENT_HITL=false
   ```

2. **Check for recent changes**:
   - Agent configuration changes
   - Model updates
   - Data quality issues in inputs

3. **Escalate** to the agent development team if root cause unclear

---

### HITLResponseTimeSlow

**Severity**: Warning
**Threshold**: p95 response time >5 minutes for 15+ minutes

#### Symptoms
- Users not responding to approval requests promptly
- Agents blocked waiting for decisions
- Workflow completion times increasing

#### Diagnosis

```promql
# Response latency percentiles
histogram_quantile(0.50, sum(rate(agent_hitl_response_latency_bucket[15m])) by (le))
histogram_quantile(0.95, sum(rate(agent_hitl_response_latency_bucket[15m])) by (le))
histogram_quantile(0.99, sum(rate(agent_hitl_response_latency_bucket[15m])) by (le))

# Pending queue depth
agent_hitl_pending_count

# Timeout rate
sum(rate(agent_hitl_decision_count_total{decision="timeout"}[1h]))
/
sum(rate(agent_hitl_decision_count_total[1h]))
```

#### Resolution

1. **Check notification delivery**:
   ```bash
   # Check push notification metrics
   curl -s "http://prometheus:9090/api/v1/query?query=push_notification_sent_total" | jq

   # Check WebSocket connection status
   curl -s "http://prometheus:9090/api/v1/query?query=ws_connections_active" | jq
   ```

2. **Review user activity patterns**:
   - Check if alerts occur during off-hours
   - Consider timezone-aware escalation

3. **Adjust auto-approve thresholds**:
   ```python
   # Auto-approve high-confidence requests
   FF_HITL_AUTO_APPROVE_THRESHOLD=0.85  # Auto-approve above 85%
   ```

4. **Configure escalation**:
   - Set up secondary approvers
   - Configure timeout escalation rules

---

### HITLResponseTimeVerySlow

**Severity**: Critical
**Threshold**: p95 response time >30 minutes for 10+ minutes

#### Immediate Actions

1. **Check for stuck requests**:
   ```bash
   # List oldest pending requests via API
   curl -s "http://localhost:8080/api/v1/agents/approvals/pending?sort=created_at" | jq
   ```

2. **Verify notification systems**:
   - Push notification service health
   - WebSocket server health
   - Email notification delivery (if configured)

3. **Consider force-timeout**:
   ```bash
   # Timeout stale requests (older than 1 hour)
   curl -X POST "http://localhost:8080/api/v1/agents/approvals/timeout-stale?max_age_minutes=60"
   ```

4. **Notify on-call personnel** for manual intervention

---

### HITLQueueBacklog

**Severity**: Warning
**Threshold**: >10 pending requests for 5+ minutes

#### Diagnosis

```promql
# Pending by request type
agent_hitl_pending_count

# Request rate vs decision rate
sum(rate(agent_hitl_request_count_total[5m])) - sum(rate(agent_hitl_decision_count_total[5m]))
```

#### Resolution

1. **Enable batch approvals** if supported
2. **Review if HITL is required** for all current request types
3. **Increase approver capacity** or add secondary approvers

---

### HITLQueueBacklogCritical

**Severity**: Critical
**Threshold**: >25 pending requests for 2+ minutes

#### Immediate Actions

1. **Identify blocked agents**:
   ```bash
   # Check agent states
   curl -s "http://localhost:8080/api/v1/agents/status" | jq '.[] | select(.status == "awaiting_approval")'
   ```

2. **Consider auto-timeout with default action**:
   ```python
   # Configure timeout with default behavior
   FF_HITL_TIMEOUT_SECONDS=1800  # 30 min timeout
   FF_HITL_TIMEOUT_ACTION="approve"  # Default to approve on timeout
   ```

3. **Escalate immediately** to operations team

---

### HITLLowConfidenceTrend

**Severity**: Info
**Threshold**: Median trigger confidence <50% for 30+ minutes

#### Diagnosis

```promql
# Confidence trend over time
histogram_quantile(0.50, sum by (le, agent_name) (rate(agent_hitl_trigger_confidence_bucket[1h])))

# Confidence by trigger reason
histogram_quantile(0.50, sum by (le, trigger_reason) (rate(agent_hitl_trigger_confidence_bucket[1h])))
```

#### Possible Causes

1. **Input data quality degradation**
   - Check input validation metrics
   - Review recent data source changes

2. **Task type drift**
   - Agent receiving unfamiliar task types
   - Distribution shift in inputs

3. **Model performance degradation**
   - Check LLM provider latency and error rates
   - Review model version changes

#### Resolution

1. **Review agent configuration** and prompts
2. **Check for data quality issues** in inputs
3. **Consider retraining** or prompt refinement
4. **Temporarily lower threshold** if confidence is consistently low but decisions are accurate

---

### HITLHighRejectionRate

**Severity**: Warning
**Threshold**: >40% of HITL requests rejected for 30+ minutes

#### Diagnosis

```promql
# Rejection rate by agent
sum by (agent_name) (rate(agent_hitl_decision_count_total{decision="rejected"}[1h]))
/
sum by (agent_name) (rate(agent_hitl_decision_count_total[1h]))

# Rejection reasons (from logs)
# Query Loki for rejection reasons
{app="mcp-server-langgraph"} |= "hitl_decision_received" | json | decision="rejected"
```

#### Resolution

1. **Analyze rejection patterns**:
   - Are rejections concentrated on specific agents?
   - Specific task types?
   - Specific users?

2. **Review agent decision quality**:
   - Agents may be making poor suggestions
   - Consider raising confidence threshold (more conservative)

3. **User training**:
   - Ensure users understand approval criteria
   - Review if rejections are warranted

---

### HITLHighTimeoutRate

**Severity**: Warning
**Threshold**: >20% of HITL requests timeout for 1+ hour

#### Diagnosis

```promql
# Timeout rate by request type
sum by (request_type) (rate(agent_hitl_decision_count_total{decision="timeout"}[1h]))
/
sum by (request_type) (rate(agent_hitl_decision_count_total[1h]))

# Correlation with time of day
sum by (hour) (increase(agent_hitl_decision_count_total{decision="timeout"}[1h]))
```

#### Resolution

1. **Check notification delivery** (push, email, WebSocket)
2. **Extend timeout duration** if too short
3. **Analyze timeout patterns**:
   - Time of day (off-hours?)
   - Specific users (availability issues?)
   - Request types (being ignored intentionally?)

4. **Configure escalation** for timeout-prone scenarios

---

## Operational Procedures

### Adjusting HITL Thresholds

#### Global Threshold

```bash
# Set global confidence threshold via environment variable
kubectl set env deployment/mcp-server FF_AGENT_HITL_CONFIDENCE_THRESHOLD=0.65

# Or via config update
kubectl patch configmap mcp-server-config --patch '{"data":{"FF_AGENT_HITL_CONFIDENCE_THRESHOLD":"0.65"}}'
```

#### Per-Agent Threshold

```python
# In agent configuration
agent_config = {
    "name": "Research Assistant",
    "hitl_threshold": 0.6,  # Override global threshold
    "hitl_required_actions": ["external_api", "file_write"],
}
```

### Monitoring HITL Health

#### Key Metrics to Watch

| Metric | Healthy Range | Alert Threshold |
|--------|---------------|-----------------|
| Intervention Rate | <20% | >30% |
| Approval Rate | >60% | <50% |
| Median Response Time | <60s | >300s |
| Pending Queue | <5 | >10 |
| Timeout Rate | <10% | >20% |
| Median Confidence | >0.6 | <0.5 |

#### Health Check Query

```promql
# Overall HITL health score (0-1)
(
  # Intervention rate contribution (lower is better)
  (1 - clamp_max(
    sum(rate(agent_hitl_request_count_total[5m])) / sum(rate(agent_task_total[5m])),
    0.5
  ) * 2) * 0.25
  +
  # Approval rate contribution (higher is better)
  sum(rate(agent_hitl_decision_count_total{decision="approved"}[5m])) / sum(rate(agent_hitl_decision_count_total[5m])) * 0.25
  +
  # Response time contribution (lower is better)
  (1 - clamp_max(
    histogram_quantile(0.50, sum(rate(agent_hitl_response_latency_bucket[5m])) by (le)) / 300,
    1
  )) * 0.25
  +
  # Queue depth contribution (lower is better)
  (1 - clamp_max(agent_hitl_pending_count / 10, 1)) * 0.25
)
```

### Debugging HITL Issues

#### Trace Lookup

```bash
# Find HITL traces in Tempo
curl -s "http://tempo:3200/api/search?tags=hitl.request_type=approval" | jq

# Get specific trace
curl -s "http://tempo:3200/api/traces/{trace_id}" | jq
```

#### Log Analysis

```logql
# All HITL events
{app="mcp-server-langgraph"} |= "hitl_"

# Low confidence approvals
{app="mcp-server-langgraph"} | json | event="hitl_request_created" | confidence < 0.5

# Rejections with reasons
{app="mcp-server-langgraph"} | json | event="hitl_decision_received" | decision="rejected"

# Slow responses
{app="mcp-server-langgraph"} | json | event="hitl_decision_received" | latency_seconds > 300
```

### Capacity Planning

#### Estimating HITL Load

```promql
# Average approval requests per hour
sum(increase(agent_hitl_request_count_total[1h]))

# Average time to clear queue
avg(agent_hitl_pending_count) * avg(histogram_quantile(0.50, sum(rate(agent_hitl_response_latency_bucket[1h])) by (le)))
```

#### Scaling Considerations

1. **WebSocket connections**: Each user session requires a WebSocket connection
2. **Push notification throughput**: Check VAPID provider limits
3. **Approval queue storage**: Redis memory for pending approvals

---

## Troubleshooting Flowchart

```
High Intervention Rate?
    │
    ├─> Check trigger reasons
    │       │
    │       ├─> "low_confidence" dominant
    │       │       └─> Lower threshold OR improve agent prompts
    │       │
    │       ├─> "destructive_action" dominant
    │       │       └─> Expected behavior, no action needed
    │       │
    │       └─> "policy_required" dominant
    │               └─> Review organizational policies
    │
    └─> Check specific agents
            │
            ├─> Single agent affected
            │       └─> Agent-specific issue, review config
            │
            └─> All agents affected
                    └─> Systemic issue, check inputs/models

Slow Response Times?
    │
    ├─> Check notification delivery
    │       │
    │       ├─> Push notifications failing
    │       │       └─> Check VAPID keys, push service health
    │       │
    │       └─> WebSocket disconnections
    │               └─> Check connection health, reconnection logic
    │
    └─> Check user availability
            │
            ├─> Off-hours
            │       └─> Configure escalation or auto-timeout
            │
            └─> Users overwhelmed
                    └─> Reduce intervention rate, add approvers

High Rejection Rate?
    │
    ├─> Check rejection reasons (from logs)
    │       │
    │       ├─> Poor agent decisions
    │       │       └─> Raise confidence threshold
    │       │
    │       └─> User confusion
    │               └─> Improve approval UI, add context
    │
    └─> Check specific agents
            └─> Agent-specific issues may need prompt tuning
```

---

## Related Documentation

- [Alerting Rules](../../../deployments/monitoring/alerting-rules/hitl-alerts.yaml)
- [Grafana Dashboard](../../../monitoring/grafana/dashboards/Application/hitl-metrics.json)
- [Feature Flags](../../src/mcp_server_langgraph/core/feature_flags.py)
- [HITL Metrics Implementation](../../src/mcp_server_langgraph/agents/metrics.py)
