# Orchestrator Operations Runbook

**Reference**: ADR-0078, ADR-0090 - Multi-Agent Orchestrator Patterns
**Last Updated**: 2026-01-03

---

## Overview

This runbook covers operational procedures for monitoring, troubleshooting, and tuning the multi-agent orchestrators.

### Orchestrators Covered

| Orchestrator | Feature Flag | Purpose |
|--------------|--------------|---------|
| UXOrchestrator | `enable_orchestrated_ai_ux` | Parallel AI UX composite analysis |
| AlertOrchestrator | `enable_orchestrated_alert_analysis` | Parallel alert correlation & root cause |
| **RouterAgent** | `enable_router_agent` | Intelligent task classification and routing |
| **SwarmOrchestrator** | `enable_swarm_orchestrator` | Race/cascade/consensus execution patterns |
| **HierarchicalOrchestrator** | `enable_hierarchical_orchestrator` | Coordinator-worker pattern |

### Agent Orchestration Architecture (ADR-0090)

The new agent orchestration architecture adds:

| Component | Description |
|-----------|-------------|
| `RouterAgent` | Classifies tasks and routes to appropriate agents |
| `SwarmOrchestrator` | Executes with race/cascade/consensus strategies |
| `ExecutionPlan` | Approval workflow for high-risk operations |
| `PlanTemplate` | Reusable execution plan templates |

**Feature Flags for Phased Rollout**:

| Flag | Default | Purpose |
|------|---------|---------|
| `enable_router_agent` | `false` | Enable RouterAgent |
| `enable_swarm_orchestrator` | `false` | Enable SwarmOrchestrator |
| `enable_hierarchical_orchestrator` | `false` | Enable hierarchical pattern |
| `force_high_risk_review` | `true` | Require approval for high-risk |
| `default_critique_rounds` | `1` | Default critique iterations |
| `enable_plan_cache` | `true` | Redis caching for plans |
| `orchestration_compat_mode` | `true` | Backward compatibility mode |
| `max_thinking_budget` | `"medium"` | Cap thinking tokens |
| `router_cache_ttl_seconds` | `3600` | Router cache TTL |

### Key Metrics

| Metric | Description |
|--------|-------------|
| `agent.ux_orchestration.count` | UX orchestration executions |
| `agent.alert_orchestration.count` | Alert orchestration executions |
| `agent.orchestration.parallel_speedup` | Speedup ratio from parallel execution |
| `agent.orchestration.parallel_tasks` | Number of tasks per orchestration |
| `agent.orchestrator.feature_flag.check` | Feature flag check count |
| `agent.orchestration.cost.dollars` | Cost in dollars |
| `agent.orchestration.cost.alert` | Budget alert triggers |
| **`router_latency_seconds`** | Router classification latency |
| **`router_confidence`** | Router confidence scores |
| **`router_cache`** | Router cache hit/miss rate |
| **`swarm_branches`** | Swarm parallel branches |
| **`swarm_cost_usd`** | Swarm execution cost |
| **`critique_rounds`** | Critique loop iterations |
| **`approval_path`** | Plan approval/rejection rate |
| **`thinking_tokens`** | Extended thinking token usage |

---

## Grafana Dashboard

### Dashboard Location

`monitoring/grafana/dashboards/Application/orchestrator-metrics.json`

### Key Panels

#### 1. Orchestration Rate

```promql
# UX orchestration rate (5m window)
rate(agent_ux_orchestration_count_total[5m])

# Alert orchestration rate (5m window)
rate(agent_alert_orchestration_count_total[5m])
```

#### 2. Parallel Speedup Distribution

```promql
# P50 speedup
histogram_quantile(0.50, rate(agent_orchestration_parallel_speedup_bucket[5m]))

# P95 speedup
histogram_quantile(0.95, rate(agent_orchestration_parallel_speedup_bucket[5m]))

# P99 speedup
histogram_quantile(0.99, rate(agent_orchestration_parallel_speedup_bucket[5m]))
```

#### 3. Feature Flag Enablement

```promql
# Percentage of requests using orchestrator
agent_orchestrator_feature_flag_check_total{enabled="true"} /
  (agent_orchestrator_feature_flag_check_total{enabled="true"} +
   agent_orchestrator_feature_flag_check_total{enabled="false"}) * 100
```

#### 4. Cost Tracking

```promql
# Cost per hour
rate(agent_orchestration_cost_dollars_total[1h]) * 3600

# Budget alerts by severity
agent_orchestration_cost_alert_total{severity="warning"}
agent_orchestration_cost_alert_total{severity="critical"}
```

#### 5. Error Rates

```promql
# Failed analyses by type
rate(agent_orchestration_failed_total{analysis_type=~".*"}[5m])

# Success rate
1 - (rate(agent_orchestration_failed_total[5m]) /
     rate(agent_orchestration_total[5m]))
```

---

## Alerting Rules

### Recommended Alerts

```yaml
groups:
  - name: orchestrator
    rules:
      # Low Parallel Speedup
      - alert: OrchestratorLowSpeedup
        expr: histogram_quantile(0.50, rate(agent_orchestration_parallel_speedup_bucket[15m])) < 1.5
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Orchestrator parallel speedup below 1.5x"
          description: "Median speedup {{ $value }}x - expected 3-4x. Possible causes: LLM latency spikes, task dependencies."
          runbook_url: "docs-internal/runbooks/ORCHESTRATOR_OPERATIONS.md#low-parallel-speedup"

      # High Failure Rate
      - alert: OrchestratorHighFailureRate
        expr: rate(agent_orchestration_failed_total[5m]) / rate(agent_orchestration_total[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Orchestrator failure rate exceeds 10%"
          description: "{{ $value | humanizePercentage }} of orchestrations failing. Check LLM availability and service health."
          runbook_url: "docs-internal/runbooks/ORCHESTRATOR_OPERATIONS.md#high-failure-rate"

      # Cost Budget Warning
      - alert: OrchestratorCostBudgetWarning
        expr: rate(agent_orchestration_cost_alert_total{severity="warning"}[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Orchestrator cost approaching budget limit"
          description: "Cost budget warnings triggered. Review session costs and consider throttling."
          runbook_url: "docs-internal/runbooks/ORCHESTRATOR_OPERATIONS.md#cost-budget-exceeded"

      # Cost Budget Critical
      - alert: OrchestratorCostBudgetCritical
        expr: rate(agent_orchestration_cost_alert_total{severity="critical"}[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Orchestrator cost budget exceeded"
          description: "Cost budget critical alerts triggered. Immediate action required."
          runbook_url: "docs-internal/runbooks/ORCHESTRATOR_OPERATIONS.md#cost-budget-exceeded"

      # Feature Flag Rollout Incomplete
      - alert: OrchestratorRolloutIncomplete
        expr: |
          agent_orchestrator_feature_flag_check_total{enabled="false"} > 0 and
          agent_orchestrator_feature_flag_check_total{enabled="true"} > 0
        for: 1h
        labels:
          severity: info
        annotations:
          summary: "Orchestrator in partial rollout state"
          description: "Both enabled and disabled paths being used. Expected during rollout, investigate if unexpected."

      # Orchestrator Completely Disabled
      - alert: OrchestratorDisabled
        expr: |
          increase(agent_orchestrator_feature_flag_check_total{enabled="true"}[1h]) == 0 and
          increase(agent_orchestrator_feature_flag_check_total{enabled="false"}[1h]) > 0
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Orchestrator completely disabled"
          description: "No orchestrated executions in the last hour. All requests using sequential fallback."
```

---

## Troubleshooting Procedures

### Scenario 1: Low Parallel Speedup

**Symptoms**:
- `parallel_speedup` P50 < 1.5x (expected 3-4x)
- Individual analysis tasks taking longer than expected
- Similar latency to sequential execution

**Investigation Steps**:

1. **Check task duration distribution**:
   ```promql
   # Task duration by type
   histogram_quantile(0.95, rate(agent_orchestration_task_duration_bucket{task_type=~".*"}[5m]))
   ```

2. **Identify bottleneck tasks**:
   ```bash
   # Check logs for slow tasks
   kubectl logs -l app=mcp-server -c mcp-server | grep "task_duration" | sort -t= -k2 -rn | head -20
   ```

3. **Verify LLM provider latency**:
   ```promql
   # LLM response time by provider
   histogram_quantile(0.95, rate(llm_request_duration_bucket{provider=~".*"}[5m]))
   ```

4. **Check for sequential dependencies**:
   - Review task configuration
   - Ensure tasks are truly independent

**Resolution**:

1. **LLM latency spikes**:
   - Switch to fallback provider if adaptive bulkhead triggered
   - Wait for provider recovery

2. **Unbalanced task distribution**:
   - Consider splitting long-running tasks
   - Exclude slow analysis types if not critical

3. **Network issues**:
   - Check connectivity to LLM providers
   - Review rate limit status

---

### Scenario 2: High Failure Rate

**Symptoms**:
- `failed_analyses` in response
- Error rate > 10%
- Degraded user experience

**Investigation Steps**:

1. **Identify failing analysis types**:
   ```promql
   # Failures by analysis type
   topk(5, rate(agent_orchestration_failed_total[5m]))
   ```

2. **Check error details**:
   ```bash
   # Search for orchestration errors
   kubectl logs -l app=mcp-server | grep -E "Error executing|orchestration failed" | tail -50
   ```

3. **Verify LLM availability**:
   ```promql
   # LLM error rate
   rate(llm_request_errors_total[5m]) / rate(llm_requests_total[5m])
   ```

4. **Check circuit breaker state**:
   ```bash
   curl -s http://localhost:8000/health/ready | jq '.circuit_breakers'
   ```

**Resolution**:

1. **LLM provider issues**:
   - Check adaptive bulkhead state
   - Switch to fallback provider
   - Wait for provider recovery

2. **Service dependency failures**:
   - Verify AI UX Service is healthy
   - Check correlation engine availability
   - Restart affected pods if necessary

3. **Configuration issues**:
   - Verify feature flags are correctly set
   - Check orchestrator injection is working
   - Review task configuration

---

### Scenario 3: Cost Budget Exceeded

**Symptoms**:
- `cost.alert` metric triggered
- Budget warnings/critical alerts
- Cost tracking showing high spend

**Investigation Steps**:

1. **Check current cost**:
   ```bash
   # Via API (if exposed)
   curl -s http://localhost:8000/api/v1/orchestrator/cost | jq
   ```

2. **Identify high-cost sessions**:
   ```promql
   # Cost by session
   topk(10, sum(agent_orchestration_cost_dollars_total) by (session_id))
   ```

3. **Analyze orchestration patterns**:
   ```promql
   # Tasks per orchestration
   histogram_quantile(0.95, rate(agent_orchestration_parallel_tasks_bucket[5m]))
   ```

**Resolution**:

1. **Reduce task count**:
   - Disable optional analyses (e.g., pattern_detection)
   - Cache results for repeated queries

2. **Adjust cost limits**:
   ```python
   # Update cost tracker configuration
   CostTracker(
       per_orchestration_limit=1.00,  # Increase if needed
       session_limit=10.00,
   )
   ```

3. **Implement rate limiting**:
   - Limit orchestrations per session
   - Add cooldown between orchestrations

4. **Emergency: Disable orchestrator**:
   ```bash
   kubectl set env deployment/mcp-server ENABLE_ORCHESTRATED_AI_UX=false
   ```

---

### Scenario 4: Feature Flag Rollout Issues

**Symptoms**:
- Mixed enabled/disabled state unexpectedly
- Inconsistent behavior across pods
- Feature flag not propagating

**Investigation Steps**:

1. **Check feature flag status per pod**:
   ```bash
   for pod in $(kubectl get pods -l app=mcp-server -o name); do
     echo "=== $pod ==="
     kubectl exec $pod -- printenv | grep ENABLE_ORCHESTRATED
   done
   ```

2. **Verify ConfigMap**:
   ```bash
   kubectl get configmap mcp-server-config -o yaml | grep enable_orchestrated
   ```

3. **Check feature flag sync**:
   ```promql
   # Feature flag checks by pod
   agent_orchestrator_feature_flag_check_total by (pod, enabled)
   ```

**Resolution**:

1. **ConfigMap not propagated**:
   ```bash
   # Restart pods to pick up new config
   kubectl rollout restart deployment/mcp-server
   ```

2. **Environment variable override**:
   ```bash
   # Check for env var overrides
   kubectl describe deployment mcp-server | grep -A5 "Environment"
   ```

3. **Force consistent state**:
   ```bash
   # Ensure all pods have same config
   kubectl set env deployment/mcp-server ENABLE_ORCHESTRATED_AI_UX=true
   ```

---

## Tuning Parameters

### Cost Tracker Defaults

| Parameter | Default | Description |
|-----------|---------|-------------|
| `per_orchestration_limit` | $0.50 | Max cost per single orchestration |
| `session_limit` | $5.00 | Max cost per session |
| `alert_thresholds` | [0.5, 0.75, 0.9] | Percentage thresholds for alerts |

### Performance Tuning

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_parallel_tasks` | Unlimited | Maximum concurrent tasks |
| `task_timeout` | 30s | Individual task timeout |
| `orchestration_timeout` | 120s | Total orchestration timeout |

### Environment Variables

```bash
# Feature flags
ENABLE_ORCHESTRATED_AI_UX=true
ENABLE_ORCHESTRATED_ALERT_ANALYSIS=true

# Cost limits
ORCHESTRATOR_PER_ORCHESTRATION_LIMIT=0.50
ORCHESTRATOR_SESSION_LIMIT=5.00

# Timeouts
ORCHESTRATOR_TASK_TIMEOUT=30
ORCHESTRATOR_TOTAL_TIMEOUT=120
```

---

## Health Check Integration

### Readiness Probe

The `/health/ready` endpoint includes orchestrator status:

```bash
curl -s http://localhost:8000/health/ready | jq
```

Response when healthy:
```json
{
  "status": "healthy",
  "orchestrators": {
    "ux_orchestrator": "enabled",
    "alert_orchestrator": "enabled"
  }
}
```

Response when degraded:
```json
{
  "status": "degraded",
  "orchestrators": {
    "ux_orchestrator": "disabled",
    "alert_orchestrator": "enabled"
  },
  "reason": "UX orchestrator disabled due to high failure rate"
}
```

---

## Emergency Procedures

### Disable All Orchestrators

**Use when**: Orchestrators causing system-wide issues

```bash
# Via environment variable
kubectl set env deployment/mcp-server \
  ENABLE_ORCHESTRATED_AI_UX=false \
  ENABLE_ORCHESTRATED_ALERT_ANALYSIS=false

# Verify
kubectl rollout status deployment/mcp-server
```

### Reset Cost Tracking

**Use when**: Cost tracking state is corrupted

```python
from mcp_server_langgraph.agents.cost_tracker import reset_cost_tracker

# Reset all session costs
reset_cost_tracker()  # Testing only!
```

### Force Sequential Fallback

**Use when**: Need to compare orchestrated vs sequential behavior

```bash
# Temporarily disable feature flag
kubectl set env deployment/mcp-server ENABLE_ORCHESTRATED_AI_UX=false

# Run comparison tests

# Re-enable
kubectl set env deployment/mcp-server ENABLE_ORCHESTRATED_AI_UX=true
```

---

## Rollout Checklist

### Pre-Rollout

- [ ] Review ADR-0078 for architecture understanding
- [ ] Verify orchestrator tests pass locally
- [ ] Check Grafana dashboard is deployed
- [ ] Confirm alerting rules are active
- [ ] Set conservative cost limits

### During Rollout

- [ ] Enable feature flag in staging
- [ ] Monitor parallel_speedup metric (expect 3-4x)
- [ ] Verify no increase in error rate
- [ ] Check cost tracking is accurate
- [ ] Test graceful degradation (disable/enable)

### Post-Rollout

- [ ] Enable in production (start 10%)
- [ ] Monitor for 1 hour at each increment
- [ ] Increase to 50%, then 100%
- [ ] Document any tuning adjustments
- [ ] Update runbook with learnings

---

## Related Documentation

- [ADR-0078: Multi-Agent Orchestrator Patterns](../../adr/adr-0078-multi-agent-orchestrator-patterns.md)
- [Multi-Agent Orchestrators Guide](../../docs/guides/multi-agent-orchestrators.mdx)
- [Resilience Operations Runbook](./RESILIENCE_OPERATIONS.md)
- [Alert Remediation Runbook](./ALERT_REMEDIATION.md)
- [Grafana Dashboard: Orchestrator Metrics](../../monitoring/grafana/dashboards/Application/orchestrator-metrics.json)
