# Resilience Patterns Operations Runbook

**Reference**: ADR-0026 - Comprehensive Client Resilience Patterns
**Last Updated**: 2025-12-20

---

## Overview

This runbook covers operational procedures for monitoring, troubleshooting, and tuning the resilience patterns implemented across all external service clients.

### Resilience Patterns Implemented

| Pattern | Purpose | Key Metrics |
|---------|---------|-------------|
| Circuit Breaker | Fail fast when service unavailable | `circuit_breaker.state`, `circuit_breaker.failures` |
| Retry with Backoff | Handle transient failures | `retry.attempts`, `retry.exhausted` |
| Timeout | Prevent hanging operations | `timeout.exceeded`, `timeout.duration` |
| Bulkhead | Limit concurrent requests | `bulkhead.rejections`, `bulkhead.active_operations` |
| Adaptive Bulkhead | Self-tuning concurrency | `adaptive_bulkhead.limit`, `adaptive_bulkhead.error_rate` |
| Rate Limiting | Prevent overwhelming services | `rate_limit.token_exhausted`, `rate_limit.wait_time` |
| Fallback | Graceful degradation | `fallback.used`, `fallback.cache_hits` |

---

## Grafana Dashboard Setup

### Key Panels

#### 1. Circuit Breaker Status

```promql
# Circuit breaker state (0=closed, 0.5=half-open, 1=open)
circuit_breaker_state{service=~"$service"}

# Failure rate by service
rate(circuit_breaker_failures_total{service=~"$service"}[5m])

# State change frequency
rate(circuit_breaker_state_changes_total{service=~"$service"}[5m])
```

#### 2. LLM Provider Health

```promql
# Adaptive bulkhead current limit by provider
adaptive_bulkhead_limit{provider=~"$provider"}

# Error rate triggering limit adjustments
adaptive_bulkhead_error_rate{provider=~"$provider"}

# Rate limit token availability
rate_limit_tokens_available{provider=~"$provider"}

# Rate limit wait time (p95)
histogram_quantile(0.95, rate(rate_limit_wait_time_bucket{provider=~"$provider"}[5m]))
```

#### 3. HTTP Connection Pool

```promql
# Pool utilization
http_pool_utilization

# Active connections
http_pool_active_connections

# Max capacity
http_pool_max_connections
```

#### 4. Retry and Timeout Health

```promql
# Retry exhaustion rate (indicates persistent issues)
rate(retry_exhausted_total{function=~"$function"}[5m])

# Timeout rate
rate(timeout_exceeded_total{operation_type=~"$type"}[5m])
```

### Alerting Rules

```yaml
groups:
  - name: resilience
    rules:
      # Circuit Breaker Open
      - alert: CircuitBreakerOpen
        expr: circuit_breaker_state{service!=""} == 1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Circuit breaker open for {{ $labels.service }}"
          description: "Circuit breaker has been open for 5 minutes, service is failing fast"
          runbook_url: "https://docs/runbooks/RESILIENCE_OPERATIONS.md#circuit-breaker-open"

      # High Retry Exhaustion
      - alert: HighRetryExhaustion
        expr: rate(retry_exhausted_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High retry exhaustion rate for {{ $labels.function }}"
          description: "Retries are being exhausted frequently, underlying service may be failing"

      # Adaptive Bulkhead at Floor
      - alert: AdaptiveBulkheadAtFloor
        expr: adaptive_bulkhead_limit <= 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Adaptive bulkhead at minimum for {{ $labels.provider }}"
          description: "LLM provider limit has decreased to floor due to errors"

      # Rate Limit Token Exhaustion
      - alert: RateLimitTokenExhaustion
        expr: rate(rate_limit_token_exhausted_total[5m]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Rate limit token exhaustion for {{ $labels.provider }}"
          description: "Requests are waiting for rate limit tokens"

      # HTTP Pool Near Capacity
      - alert: HTTPPoolNearCapacity
        expr: http_pool_utilization > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "HTTP connection pool at {{ $value | humanizePercentage }}"
          description: "Connection pool is near capacity, may need scaling"
```

---

## Troubleshooting Procedures

### Scenario 1: Circuit Breaker Open

**Symptoms**:
- Requests failing immediately with `CircuitBreakerError`
- `circuit_breaker.state = 1` in metrics
- Log entries: "Circuit breaker open for service X"

**Investigation Steps**:

1. **Check circuit breaker state**:
   ```bash
   # Via health endpoint
   curl -s http://localhost:8000/health/ready | jq '.circuit_breakers'
   ```

2. **Identify root cause**:
   ```promql
   # Recent failures that tripped the breaker
   circuit_breaker_failures_total{service="openfga"}
   ```

3. **Check underlying service**:
   ```bash
   # Test service connectivity
   curl -s http://openfga:8080/health
   ```

4. **Review logs for error details**:
   ```bash
   # Search for circuit breaker events
   grep "circuit_breaker" /var/log/mcp-server/*.log | tail -50
   ```

**Resolution**:

1. **If service recovered**:
   - Wait for automatic recovery (30s timeout default)
   - Circuit moves to HALF_OPEN, then CLOSED on success

2. **If service still failing**:
   - Check service health
   - Review service logs
   - Consider manual restart if necessary

3. **Manual reset (use sparingly)**:
   ```python
   from mcp_server_langgraph.resilience.circuit_breaker import reset_circuit_breaker
   reset_circuit_breaker("openfga")
   ```

---

### Scenario 2: LLM Rate Limit Errors (429/529)

**Symptoms**:
- `LLMRateLimitError` or `LLMOverloadError` in logs
- Adaptive bulkhead limit decreasing
- High `rate_limit.token_exhausted` counter

**Investigation Steps**:

1. **Check adaptive bulkhead state**:
   ```promql
   adaptive_bulkhead_limit{provider="anthropic"}
   adaptive_bulkhead_error_rate{provider="anthropic"}
   ```

2. **Check rate limit wait times**:
   ```promql
   histogram_quantile(0.95, rate(rate_limit_wait_time_bucket{provider="anthropic"}[5m]))
   ```

3. **Review request volume**:
   ```promql
   rate(llm_requests_total{provider="anthropic"}[5m])
   ```

**Resolution**:

1. **Short-term**:
   - System will self-heal via adaptive bulkhead (AIMD algorithm)
   - Limit decreases by 25% on error, increases by 1 after 10 successes

2. **Long-term**:
   - Review rate limit configuration:
     ```bash
     # Environment variables
     echo $RATE_LIMIT_ANTHROPIC_RPM
     ```
   - Consider increasing quota with provider
   - Implement request batching/caching

3. **Tune rate limits**:
   ```bash
   # Set new rate limit (requests per minute)
   export RATE_LIMIT_ANTHROPIC_RPM=100
   ```

---

### Scenario 3: High Retry Exhaustion

**Symptoms**:
- `retry.exhausted` counter increasing
- Operations failing after multiple retries
- Increased latency due to retry delays

**Investigation Steps**:

1. **Identify failing operations**:
   ```promql
   topk(5, rate(retry_exhausted_total[5m]))
   ```

2. **Check retry attempts**:
   ```promql
   rate(retry_attempts_total{function="call_openfga"}[5m])
   ```

3. **Correlate with service health**:
   - Check if circuit breaker should have opened
   - Review error types causing retries

**Resolution**:

1. **If transient**:
   - Monitor for self-recovery
   - Check for deployment in progress

2. **If persistent**:
   - Investigate underlying service
   - Consider reducing retry attempts temporarily
   - Enable fallback if available

---

### Scenario 4: HTTP Connection Pool Exhaustion

**Symptoms**:
- `http_pool.utilization > 0.9`
- Request timeouts
- Log entries: "Connection pool exhausted"

**Investigation Steps**:

1. **Check pool metrics**:
   ```promql
   http_pool_active_connections
   http_pool_max_connections
   http_pool_utilization
   ```

2. **Identify slow consumers**:
   - Check which services are holding connections
   - Review timeout configurations

**Resolution**:

1. **Increase pool size**:
   ```python
   # In http_client.py configuration
   limits = httpx.Limits(
       max_keepalive_connections=200,  # Increase from 100
       max_connections=400,             # Increase from 200
   )
   ```

2. **Reduce connection hold time**:
   - Lower keepalive expiry
   - Add timeouts to slow operations

3. **Scale horizontally**:
   - Add more replicas to distribute load

---

## Tuning Parameters

### Circuit Breaker Defaults

| Parameter | Default | Description |
|-----------|---------|-------------|
| `fail_max` | 5 | Failures before opening |
| `timeout` | 30s | Recovery window |

### Retry Defaults

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_attempts` | 3 | Maximum retry attempts |
| `backoff_base` | 1.0s | Base delay |
| `backoff_multiplier` | 2.0 | Exponential growth factor |
| `backoff_max` | 10.0s | Maximum delay cap |

### Adaptive Bulkhead Defaults

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_limit` | 25% of base | Floor for concurrency |
| `max_limit` | 200% of base | Ceiling for concurrency |
| `error_threshold` | 10% | Error rate triggering decrease |
| `decrease_factor` | 0.75 | Multiplicative decrease (25% reduction) |
| `increase_amount` | 1 | Additive increase per streak |
| `success_streak_threshold` | 10 | Successes before increase |

### Rate Limit Defaults (per provider)

| Provider | RPM | Burst Capacity |
|----------|-----|----------------|
| Anthropic | 50 | ~8 requests |
| OpenAI | 500 | ~83 requests |
| Vertex AI | 600 | ~150 requests |
| Vertex AI Anthropic | 1000 | ~167 requests |
| Bedrock | 50 | ~8 requests |
| Ollama | 1000 | ~500 requests |

---

## Health Check Integration

### Readiness Probe

The `/health/ready` endpoint includes circuit breaker state:

```bash
curl -s http://localhost:8000/health/ready | jq
```

Response when healthy:
```json
{
  "status": "healthy",
  "circuit_breakers": {
    "redis": "CLOSED",
    "keycloak": "CLOSED",
    "openfga": "CLOSED",
    "llm": "CLOSED"
  }
}
```

Response when degraded:
```json
{
  "status": "unhealthy",
  "reason": "openfga circuit breaker open",
  "circuit_breakers": {
    "openfga": "OPEN"
  }
}
```

### Critical vs Warning Circuit Breakers

| Category | Services | Impact |
|----------|----------|--------|
| **Critical** | redis, keycloak, openfga, postgres | OPEN → 503 Not Ready |
| **Warning** | prometheus, tempo, loki | OPEN → 200 with warning |

---

## Emergency Procedures

### Manual Circuit Breaker Reset

**Warning**: Only use when service has recovered but breaker is stuck.

```python
from mcp_server_langgraph.resilience.circuit_breaker import reset_circuit_breaker

# Reset specific breaker
reset_circuit_breaker("openfga")

# Reset all breakers (testing only!)
from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers
reset_all_circuit_breakers()  # DO NOT use in production
```

### Manual Adaptive Bulkhead Reset

```python
from mcp_server_langgraph.resilience.adaptive import reset_all_adaptive_bulkheads

# Reset all bulkheads (resets limits to default)
reset_all_adaptive_bulkheads()  # Testing only!
```

### Disable Resilience Patterns

**Warning**: Only for emergency debugging.

```bash
# Disable retry (set max_attempts=1)
export RESILIENCE_MAX_ATTEMPTS=1

# Disable circuit breaker (set high threshold)
export RESILIENCE_CIRCUIT_BREAKER_FAIL_MAX=1000

# Disable rate limiting (set high RPM)
export RATE_LIMIT_ANTHROPIC_RPM=10000
```

---

## Appendix: Metric Reference

### OpenTelemetry Metric Names

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `circuit_breaker.state` | Gauge | service | 0=closed, 0.5=half-open, 1=open |
| `circuit_breaker.failures` | Counter | service, exception_type | Failure count |
| `circuit_breaker.successes` | Counter | service | Success count |
| `circuit_breaker.state_changes` | Counter | service | State transition count |
| `retry.attempts` | Counter | function, attempt_number | Retry attempt count |
| `retry.exhausted` | Counter | function, exception_type | Exhaustion count |
| `retry.success_after_retry` | Counter | function | Successes after retry |
| `timeout.exceeded` | Counter | function, operation_type | Timeout count |
| `timeout.duration` | Histogram | function | Timeout duration |
| `bulkhead.rejections` | Counter | resource_type | Rejection count |
| `bulkhead.active_operations` | Gauge | resource_type | Active operations |
| `bulkhead.queue_depth` | Gauge | resource_type | Queue depth |
| `rate_limit.token_exhausted` | Counter | provider | Token exhaustion |
| `rate_limit.wait_time` | Histogram | provider | Wait time (ms) |
| `rate_limit.tokens_available` | Gauge | provider | Available tokens |
| `adaptive_bulkhead.limit` | Gauge | provider | Current limit |
| `adaptive_bulkhead.error_rate` | Gauge | provider | Error rate (0-1) |
| `adaptive_bulkhead.adjustments` | Counter | provider, direction | Limit adjustments |
| `http_pool.active_connections` | Gauge | - | Active HTTP connections |
| `http_pool.max_connections` | Gauge | - | Max connections configured |
| `http_pool.utilization` | Gauge | - | Pool utilization (0-1) |
| `fallback.used` | Counter | function, exception_type | Fallback invocations |
| `fallback.cache_hits` | Counter | function | Cache fallback hits |

---

## Automated Remediation

The system includes automated remediation for common resilience scenarios. Alerts trigger remediation actions via Alertmanager webhooks before notifying humans.

### Automated Remediation Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│  Mimir Alerts   │───▶│   Alertmanager   │───▶│ Remediation Webhook │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                                         │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       ▼                                 ▼                                 ▼
              ┌────────────────┐              ┌───────────────────┐              ┌─────────────────┐
              │ Restart Pods   │              │ Scale Deployment  │              │ Switch Provider │
              │ (Circuit Breaker)│             │ (Pool Exhaustion) │              │ (LLM Throttling)│
              └────────────────┘              └───────────────────┘              └─────────────────┘
```

### Remediation Triggers

| Alert | Remediation Action | Script |
|-------|-------------------|--------|
| `CircuitBreakerOpen` | Restart unhealthy pods of dependent service | `restart-circuit-breaker-pods.sh` |
| `HTTPPoolExhausted` | Scale deployment horizontally (+50%) | `scale-deployment.sh` |
| `AdaptiveBulkheadAtFloor` | Switch to fallback LLM provider | `switch-llm-provider.sh` |
| `RetryExhausted` | Restart affected service | `restart-circuit-breaker-pods.sh` |

### Safety Guards

1. **Cooldown Period**: Minimum 5 minutes between remediations for the same service
2. **Max Replicas**: Scaling capped at configurable maximum (default: 10)
3. **Dry Run Mode**: Test remediation logic without executing
4. **Audit Logging**: All remediations logged to stdout and Kubernetes events
5. **Manual Override**: Annotation `remediation.skip=true` prevents auto-remediation

### Manual Remediation Commands

#### Restart Pods (Circuit Breaker)

```bash
# Restart pods when circuit breaker is open
./deployments/remediation/scripts/restart-circuit-breaker-pods.sh redis

# With namespace and dry-run
DRY_RUN=true ./deployments/remediation/scripts/restart-circuit-breaker-pods.sh keycloak production
```

#### Scale Deployment (HTTP Pool)

```bash
# Scale deployment (auto-calculates +50%)
./deployments/remediation/scripts/scale-deployment.sh mcp-server-langgraph

# Scale to specific replica count
./deployments/remediation/scripts/scale-deployment.sh mcp-server-langgraph 5 production
```

#### Switch LLM Provider

```bash
# Switch to fallback provider
./deployments/remediation/scripts/switch-llm-provider.sh ollama

# Switch to specific provider
./deployments/remediation/scripts/switch-llm-provider.sh anthropic production
```

#### Reset Circuit Breaker

```bash
# Force circuit breaker reset via health endpoint or rolling restart
./deployments/remediation/scripts/reset-circuit-breaker.sh redis
```

### Kubernetes Jobs

Remediation can also be triggered via Kubernetes Jobs:

```bash
# Create one-off remediation job from CronJob template
kubectl create job cb-restart-redis --from=cronjob/circuit-breaker-remediation

# Override environment variables
kubectl set env cronjob/circuit-breaker-remediation SERVICE=keycloak
kubectl create job cb-restart-keycloak --from=cronjob/circuit-breaker-remediation

# Scale remediation
kubectl create job scale-remediation --from=cronjob/scale-on-saturation

# LLM provider failover
kubectl set env cronjob/provider-failover TARGET_PROVIDER=anthropic
kubectl create job llm-failover-anthropic --from=cronjob/provider-failover
```

### Disabling Automated Remediation

To temporarily disable automated remediation for a deployment:

```bash
# Add skip annotation
kubectl annotate deployment mcp-server-langgraph remediation.skip=true

# Remove skip annotation
kubectl annotate deployment mcp-server-langgraph remediation.skip-
```

For LLM provider switching specifically:

```bash
kubectl annotate deployment mcp-server-langgraph remediation.llm-switch.skip=true
```

### Monitoring Remediation

```promql
# Remediations triggered
remediation_actions_total{action="restart", status="success"}

# Remediations skipped (cooldown or annotation)
remediation_skipped_total{reason="cooldown"}

# Remediation duration
histogram_quantile(0.95, rate(remediation_duration_seconds_bucket[1h]))
```

### Troubleshooting Automated Remediation

1. **Remediation not triggering**:
   - Check webhook handler logs: `kubectl logs -l app=remediation-webhook`
   - Verify Alertmanager webhook config: `curl http://alertmanager:9093/api/v2/status`
   - Check for skip annotation: `kubectl get deployment -o yaml | grep remediation.skip`

2. **Remediation failing**:
   - Check RBAC permissions for remediation-webhook service account
   - Verify namespace is correct
   - Review Kubernetes events: `kubectl get events --sort-by='.lastTimestamp'`

3. **Too frequent remediations**:
   - Increase cooldown period: `COOLDOWN_SECONDS=600`
   - Add skip annotation temporarily
   - Investigate root cause of recurring alerts

---

## Related Documentation

- [ADR-0026: Comprehensive Client Resilience Patterns](../ADR-0026-RESILIENCE-PATTERNS.md)
- [OpenTelemetry Instrumentation Guide](../../docs/guides/observability.mdx)
- [Grafana Dashboard Templates](../dashboards/)
- [Remediation Automation](../../deployments/remediation/README.md)
