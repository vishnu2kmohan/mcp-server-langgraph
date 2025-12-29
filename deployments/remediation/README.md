# Resilience Remediation Automation

Automated remediation scripts and Kubernetes jobs for handling resilience alerts.

**Reference**: ADR-0026 - Comprehensive Client Resilience Patterns

---

## Overview

This directory contains automation for common resilience scenarios:

| Scenario | Trigger | Remediation |
|----------|---------|-------------|
| Circuit Breaker Open (Extended) | CB open > 10 min | Restart dependent pods |
| HTTP Pool Exhaustion | Utilization > 95% | Scale horizontally |
| LLM Provider Throttled | Adaptive bulkhead at floor | Switch to fallback provider |
| High Retry Exhaustion | Rate > 1/s for 5 min | Restart affected service |

---

## Components

### 1. Remediation Scripts (`scripts/`)

Shell scripts for manual or automated remediation:

```bash
# Restart pods with open circuit breakers
./scripts/restart-circuit-breaker-pods.sh keycloak

# Scale deployment horizontally
./scripts/scale-deployment.sh mcp-server-langgraph 5

# Force circuit breaker reset (via health endpoint)
./scripts/reset-circuit-breaker.sh redis
```

### 2. Kubernetes Jobs (`kubernetes/`)

Kubernetes Job manifests for automated remediation:

- `circuit-breaker-remediation-job.yaml` - Restarts pods when CB is open
- `scale-on-saturation-job.yaml` - Scales deployment on pool saturation
- `provider-failover-job.yaml` - Switches LLM provider on throttling

### 3. Alert Webhook Handler (`webhook/`)

A lightweight FastAPI service that receives Alertmanager webhooks and triggers remediation:

```yaml
# Example alert payload
{
  "alerts": [{
    "labels": {
      "alertname": "CircuitBreakerOpen",
      "service": "redis",
      "severity": "critical"
    },
    "status": "firing"
  }]
}
```

---

## Deployment

### Prerequisites

- Kubernetes RBAC permissions for pod management
- Alertmanager configured to send webhooks
- Service account with appropriate permissions

### Quick Start

```bash
# Deploy the webhook handler
kubectl apply -f kubernetes/webhook-handler-deployment.yaml

# Configure Alertmanager to send alerts to webhook
# (See alertmanager/alertmanager-config.yaml)

# Verify webhook is receiving alerts
kubectl logs -l app=remediation-webhook -f
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NAMESPACE` | Kubernetes namespace | `default` |
| `DRY_RUN` | Log actions without executing | `false` |
| `COOLDOWN_SECONDS` | Min time between remediations | `300` |
| `MAX_SCALE_REPLICAS` | Maximum replicas for scaling | `10` |
| `FALLBACK_PROVIDER` | LLM provider to fail over to | `ollama` |

### Safety Guards

1. **Cooldown Period**: Minimum 5 minutes between remediations for the same service
2. **Max Replicas**: Scaling capped at configurable maximum
3. **Dry Run Mode**: Test remediation logic without executing
4. **Audit Logging**: All remediations logged to stdout and Kubernetes events
5. **Manual Override**: Annotation `remediation.skip=true` prevents auto-remediation

---

## Remediation Procedures

### Circuit Breaker Open (Extended)

**Trigger**: `CircuitBreakerOpen` alert firing for > 10 minutes

**Automated Action**:
1. Check if dependent service pods are healthy
2. If unhealthy, trigger rolling restart
3. If healthy, log and wait for CB to close naturally

**Manual Override**:
```bash
kubectl annotate deployment mcp-server-langgraph remediation.skip=true
```

### HTTP Pool Exhaustion

**Trigger**: `HTTPPoolExhausted` alert (utilization >= 95%)

**Automated Action**:
1. Check current replica count
2. If below max, scale up by 50%
3. Log scaling event to Kubernetes events

**Manual Override**:
```bash
kubectl scale deployment mcp-server-langgraph --replicas=10
```

### LLM Provider Throttled

**Trigger**: `AdaptiveBulkheadAtFloor` for > 15 minutes

**Automated Action**:
1. Update ConfigMap with fallback provider
2. Trigger rolling restart to pick up new config
3. Alert on-call that provider was switched

**Manual Override**:
```bash
kubectl set env deployment/mcp-server-langgraph LLM_PROVIDER=ollama
```

---

## Monitoring

### Remediation Metrics

```promql
# Remediations triggered
remediation_actions_total{action="restart", service="redis"}

# Remediations skipped (cooldown or annotation)
remediation_skipped_total{reason="cooldown"}

# Remediation duration
remediation_duration_seconds{action="scale"}
```

### Grafana Dashboard

Import `remediation-dashboard.json` for:
- Remediation history timeline
- Success/failure rates
- Cooldown status per service

---

## Troubleshooting

### Remediation Not Triggering

1. Check webhook handler logs: `kubectl logs -l app=remediation-webhook`
2. Verify Alertmanager webhook config
3. Check for `remediation.skip=true` annotation
4. Verify cooldown hasn't been triggered recently

### Remediation Failing

1. Check RBAC permissions for the service account
2. Verify namespace is correct
3. Check pod/deployment names match expectations
4. Review Kubernetes events for errors

---

## Related Documentation

- [Resilience Operations Runbook](../../docs-internal/runbooks/RESILIENCE_OPERATIONS.md)
- [Internal: Resilience Patterns](../../docs-internal/INTERNAL-0026-RESILIENCE-PATTERNS.md)
- [Alertmanager Configuration](../monitoring/alertmanager/alertmanager-config.yaml)
