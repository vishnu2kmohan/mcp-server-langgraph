# Alerting Fallback Chain Runbook

## Overview

This runbook covers alerts related to the alerting backend fallback chain (ADR-0098). The fallback chain provides resilience when the primary alerting backend (Grafana) is unavailable by falling back to Mimir, then to a stub backend.

**Fallback Chain Order**: Grafana → Mimir → Stub

## Symptoms

When these alerts fire, you may observe:
- DevTools AlertsTab showing stale or empty alert data
- Increased latency in alert queries
- Alert data served from fallback backends instead of primary
- Health check failures in observability logs

## Architecture Reference

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Alerting Fallback Chain                                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  DevTools AlertsTab → FallbackAlertingClient                           │
│                              ↓                                          │
│                    ┌─────────┴─────────┐                               │
│                    ↓         ↓         ↓                               │
│               Grafana    Mimir     Stub                                │
│              (primary)  (fallback) (last resort)                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Prometheus Metrics

| Metric | Description |
|--------|-------------|
| `alerting_fallback_activations_total` | Count of fallback activations |
| `alerting_backend_errors_total` | Count of backend errors |
| `alerting_health_checks_total` | Count of health checks by result |

## Grafana Dashboard

**Dashboard**: `Alerting Fallback Metrics` (`alerting-fallback-metrics`)

---

## AlertingFallbackActivated

### Alert Definition
```yaml
alert: AlertingFallbackActivated
expr: sum(rate(alerting_fallback_activations_total[5m])) > 0.1
for: 5m
severity: warning
```

### Severity
**WARNING** - Investigation required

### Impact
- Alert queries are being served by fallback backend
- Primary backend (Grafana) may be degraded
- Slight increase in query latency

### Diagnosis

1. **Check Grafana health**
   ```bash
   kubectl get pods -l app=grafana -n monitoring
   kubectl logs -l app=grafana -n monitoring --tail=100
   ```

2. **Check Mimir health**
   ```bash
   kubectl get pods -l app=mimir -n monitoring
   curl -s http://mimir:9009/ready
   ```

3. **Check fallback metrics**
   ```promql
   # Fallback rate
   rate(alerting_fallback_activations_total[5m])

   # Which operations are falling back
   sum by (operation) (rate(alerting_fallback_activations_total[5m]))
   ```

4. **Check application logs**
   ```bash
   kubectl logs -l app=mcp-server-langgraph --tail=100 | grep -i "fallback\|alerting"
   ```

### Resolution

1. **If Grafana is unhealthy**
   - Restart Grafana: `kubectl rollout restart deployment/grafana -n monitoring`
   - Check Grafana datasources are configured correctly
   - Verify Grafana can reach Mimir Alertmanager

2. **If network issues**
   - Check DNS resolution between services
   - Verify network policies allow traffic
   - Check service endpoints: `kubectl get endpoints grafana -n monitoring`

3. **If authentication issues**
   - Verify Grafana API keys are valid
   - Check RBAC permissions for alerting API

### Escalation
- **Platform Team**: After 15 minutes if unresolved

---

## AlertingFallbackSustained

### Alert Definition
```yaml
alert: AlertingFallbackSustained
expr: sum(increase(alerting_fallback_activations_total[15m])) > 10
for: 15m
severity: critical
```

### Severity
**CRITICAL** - Immediate response required

### Impact
- Primary alerting backend persistently failing
- Alert availability depends entirely on fallback backends
- Risk of complete alert unavailability if fallback also fails

### Diagnosis

1. **Verify sustained fallback pattern**
   ```promql
   sum(increase(alerting_fallback_activations_total[1h]))
   ```

2. **Check all backend health**
   ```promql
   # Health check success rate by backend
   sum by (backend) (rate(alerting_health_checks_total{result="healthy"}[5m]))
   /
   sum by (backend) (rate(alerting_health_checks_total[5m]))
   ```

3. **Check error patterns**
   ```promql
   sum by (backend, error_type) (rate(alerting_backend_errors_total[5m]))
   ```

### Resolution

1. **Prioritize primary backend recovery**
   - Follow Grafana troubleshooting procedures
   - Check Grafana Unified Alerting configuration

2. **Ensure fallback chain integrity**
   - Verify Mimir Alertmanager is operational
   - Check `MIMIR_URL` and `MIMIR_ORG_ID` configuration

3. **Consider temporary workarounds**
   - If Grafana recovery will take time, explicitly configure `OBSERVABILITY_ALERTING_BACKEND=mimir`

### Escalation
- **Platform Team**: Immediately
- **On-call SRE**: If primary cannot be restored within 30 minutes

---

## AlertingBackendsDown

### Alert Definition
```yaml
alert: AlertingBackendsDown
expr: |
  sum(rate(alerting_backend_errors_total[5m])) > 0
  and
  sum(rate(alerting_health_checks_total{result="healthy"}[5m])) == 0
for: 5m
severity: critical
```

### Severity
**CRITICAL** - Immediate response required

### Impact
- **COMPLETE ALERT UNAVAILABILITY**
- DevTools AlertsTab returns empty results
- No alert data available from any backend
- Only stub backend may be responding (returns empty)

### Diagnosis

1. **Check all LGTM components**
   ```bash
   kubectl get pods -n monitoring
   ```

2. **Verify network connectivity**
   ```bash
   # From application pod
   kubectl exec -it deploy/mcp-server-langgraph -- curl -s http://grafana:3000/api/health
   kubectl exec -it deploy/mcp-server-langgraph -- curl -s http://mimir:9009/ready
   ```

3. **Check infrastructure**
   ```bash
   # Check node health
   kubectl get nodes
   # Check for resource exhaustion
   kubectl top pods -n monitoring
   ```

### Resolution

1. **Immediate triage**
   - Identify which component is causing the cascade failure
   - Check for cluster-wide issues (networking, storage)

2. **Restore any backend**
   - Priority: Mimir > Grafana (Mimir has direct Alertmanager)
   - Restart affected services

3. **If cluster-wide issue**
   - Engage infrastructure team
   - Consider failover to DR cluster if available

### Escalation
- **Platform Team + SRE**: Immediately
- **Infrastructure Team**: If cluster-wide issue

---

## AlertingBackendErrorsHigh

### Alert Definition
```yaml
alert: AlertingBackendErrorsHigh
expr: sum(rate(alerting_backend_errors_total[5m])) > 0.5
for: 5m
severity: warning
```

### Severity
**WARNING** - Investigation required

### Impact
- Elevated error rate on alerting backends
- May indicate impending backend failure
- Fallback chain is handling errors gracefully

### Diagnosis

1. **Identify error types**
   ```promql
   sum by (backend, error_type) (rate(alerting_backend_errors_total[5m]))
   ```

2. **Check specific backend logs**
   ```bash
   # If Grafana errors
   kubectl logs -l app=grafana --tail=100 | grep -i error

   # If Mimir errors
   kubectl logs -l app=mimir --tail=100 | grep -i error
   ```

3. **Check for timeout patterns**
   ```promql
   # Timeout errors specifically
   sum(rate(alerting_backend_errors_total{error_type="TimeoutError"}[5m]))
   ```

### Resolution

1. **For connection errors**
   - Check network policies
   - Verify service DNS resolution
   - Check backend health endpoints

2. **For timeout errors**
   - Increase `ALERTING_HEALTH_CHECK_INTERVAL` if health checks are too aggressive
   - Check backend performance (CPU, memory)
   - Consider increasing timeout values

3. **For authentication errors**
   - Verify API credentials
   - Check token expiration

---

## AlertingHealthChecksFailing

### Alert Definition
```yaml
alert: AlertingHealthChecksFailing
expr: |
  sum(rate(alerting_health_checks_total{result!="healthy"}[5m]))
  /
  sum(rate(alerting_health_checks_total[5m]))
  > 0.3
for: 5m
severity: warning
```

### Severity
**WARNING** - Investigation required

### Impact
- More than 30% of health checks failing
- Backends may be marked unhealthy incorrectly
- Increased fallback activity expected

### Diagnosis

1. **Check health check results by backend**
   ```promql
   sum by (backend, result) (rate(alerting_health_checks_total[5m]))
   ```

2. **Verify backend /ready endpoints**
   ```bash
   curl -s http://grafana:3000/api/health | jq .
   curl -s http://mimir:9009/ready
   ```

3. **Check for transient failures**
   ```promql
   # Unhealthy vs error rate
   sum(rate(alerting_health_checks_total{result="unhealthy"}[5m]))
   sum(rate(alerting_health_checks_total{result="error"}[5m]))
   ```

### Resolution

1. **If transient network issues**
   - Increase `ALERTING_HEALTH_CHECK_INTERVAL` to reduce check frequency
   - Current default: 30 seconds

2. **If persistent failures**
   - Investigate underlying backend health
   - Follow backend-specific runbooks

---

## GrafanaAlertingDown

### Alert Definition
```yaml
alert: GrafanaAlertingDown
expr: |
  sum(rate(alerting_health_checks_total{backend="GrafanaAlertingClient", result!="healthy"}[5m]))
  /
  sum(rate(alerting_health_checks_total{backend="GrafanaAlertingClient"}[5m]))
  > 0.5
for: 5m
severity: warning
```

### Severity
**WARNING** - Primary backend degraded

### Impact
- Grafana (primary) alerting backend failing
- Fallback to Mimir should be active
- Alert data still available via Mimir

### Diagnosis

1. **Check Grafana Unified Alerting status**
   ```bash
   curl -s http://grafana:3000/api/alertmanager/grafana/api/v2/status | jq .
   ```

2. **Check Grafana logs for alerting errors**
   ```bash
   kubectl logs -l app=grafana --tail=100 | grep -i "alerting\|alertmanager"
   ```

### Resolution

1. **Restart Grafana**
   ```bash
   kubectl rollout restart deployment/grafana -n monitoring
   ```

2. **Check Grafana configuration**
   - Verify Unified Alerting is enabled
   - Check alertmanager datasource configuration

---

## MimirAlertingDown

### Alert Definition
```yaml
alert: MimirAlertingDown
expr: |
  sum(rate(alerting_health_checks_total{backend="MimirAlertingClient", result!="healthy"}[5m]))
  /
  sum(rate(alerting_health_checks_total{backend="MimirAlertingClient"}[5m]))
  > 0.5
for: 5m
severity: warning
```

### Severity
**WARNING** - Fallback backend degraded

### Impact
- Mimir (fallback) alerting backend failing
- Only stub backend remains as last resort
- Stub returns empty results (no alert data)

### Diagnosis

1. **Check Mimir Alertmanager status**
   ```bash
   curl -s http://mimir:9009/alertmanager/api/v2/status | jq .
   ```

2. **Check Mimir health**
   ```bash
   curl -s http://mimir:9009/ready
   kubectl logs -l app=mimir --tail=100 | grep -i alertmanager
   ```

3. **Verify multi-tenancy configuration**
   ```bash
   # Check X-Scope-OrgID header is correct
   curl -H "X-Scope-OrgID: anonymous" http://mimir:9009/alertmanager/api/v2/alerts
   ```

### Resolution

1. **Restart Mimir**
   ```bash
   kubectl rollout restart deployment/mimir -n monitoring
   ```

2. **Check Mimir configuration**
   - Verify Alertmanager is enabled in Mimir config
   - Check `MIMIR_ORG_ID` matches tenant configuration

---

## Configuration Reference

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ALERTING_FALLBACK_ENABLED` | `false` | Enable fallback chain |
| `ALERTING_HEALTH_CHECK_INTERVAL` | `30` | Health check cache TTL (seconds) |
| `MIMIR_URL` | `http://mimir:9009` | Mimir server URL |
| `MIMIR_ORG_ID` | `anonymous` | Mimir tenant ID |
| `OBSERVABILITY_ALERTING_BACKEND` | `grafana` | Direct backend selection |

## Related Documentation

- [ADR-0098: Mimir Alerting Fallback](../adr/adr-0098-mimir-alerting-fallback.md)
- [Environment Variables Reference](../docs/reference/environment-variables.mdx)
- [LGTM Stack Health Runbook](./infrastructure-alerts.md)
