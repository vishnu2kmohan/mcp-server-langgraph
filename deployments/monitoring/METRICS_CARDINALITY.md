# Resilience Metrics Cardinality Analysis

**Reference**: ADR-0026 - Comprehensive Client Resilience Patterns
**Last Updated**: 2025-12-20

---

## Overview

This document analyzes the cardinality of resilience metrics to ensure Prometheus doesn't suffer from label explosion. High cardinality can cause memory issues and slow queries.

---

## Label Cardinality Summary

| Label | Used By | Expected Values | Cardinality | Risk |
|-------|---------|-----------------|-------------|------|
| `service` | circuit_breaker | llm, openfga, redis, postgres, keycloak, prometheus, tempo, loki | **8** | Low |
| `provider` | rate_limit, adaptive_bulkhead | anthropic, openai, vertex_ai, vertex_ai_anthropic, bedrock, ollama | **6** | Low |
| `operation_type` | timeout | llm, auth, db, http, default | **5** | Low |
| `resource_type` | bulkhead | llm, openfga, redis, db | **4** | Low |
| `direction` | adaptive_bulkhead | increase, decrease | **2** | Low |
| `fallback_type` | fallback | default, function, strategy, cache | **4** | Low |
| `attempt_number` | retry | 1, 2, 3 (up to max_attempts) | **3-5** | Low |
| `function` | retry, timeout, fallback | Dynamic - function names | **20-50** | Medium |
| `exception_type` | circuit_breaker, retry, fallback | Dynamic - exception class names | **10-20** | Medium |
| `timeout_seconds` | timeout | Various timeout values | **5-10** | Low |

---

## Metric Cardinality Estimates

### Circuit Breaker Metrics
```
circuit_breaker.state{service}           = 8 time series
circuit_breaker.failures{service,exception_type} = 8 × 20 = 160 time series
circuit_breaker.successes{service}       = 8 time series
circuit_breaker.state_changes{service}   = 8 time series
```
**Subtotal**: ~184 time series

### Retry Metrics
```
retry.attempts{function,attempt_number}  = 50 × 5 = 250 time series
retry.exhausted{function,exception_type} = 50 × 20 = 1,000 time series
retry.success_after_retry{function}      = 50 time series
```
**Subtotal**: ~1,300 time series (worst case)

### Timeout Metrics
```
timeout.exceeded{function,operation_type,timeout_seconds} = 50 × 5 × 10 = 2,500 time series
timeout.duration{function,operation_type,timeout_seconds} = 50 × 5 × 10 = 2,500 time series (histogram buckets add ~10x)
```
**Subtotal**: ~5,000 time series (worst case)

### Bulkhead Metrics
```
bulkhead.rejections{resource_type}       = 4 time series
bulkhead.active_operations{resource_type} = 4 time series
bulkhead.queue_depth{resource_type}      = 4 time series
```
**Subtotal**: ~12 time series

### Rate Limit Metrics
```
rate_limit.token_exhausted{provider}     = 6 time series
rate_limit.wait_time{provider}           = 6 time series (histogram buckets add ~10x)
rate_limit.tokens_available{provider}    = 6 time series
```
**Subtotal**: ~78 time series

### Adaptive Bulkhead Metrics
```
adaptive_bulkhead.limit{provider}        = 6 time series
adaptive_bulkhead.error_rate{provider}   = 6 time series
adaptive_bulkhead.adjustments{provider,direction,new_limit} = 6 × 2 × 10 = 120 time series
```
**Subtotal**: ~132 time series

### Fallback Metrics
```
fallback.used{function,exception_type,fallback_type} = 50 × 20 × 4 = 4,000 time series
fallback.cache_hits{function,exception_type,fallback_type} = 50 × 20 × 4 = 4,000 time series
```
**Subtotal**: ~8,000 time series (worst case)

### HTTP Pool Metrics
```
http_pool.active_connections             = 1 time series
http_pool.max_connections                = 1 time series
http_pool.utilization                    = 1 time series
```
**Subtotal**: ~3 time series

---

## Total Cardinality Estimate

| Scenario | Time Series | Assessment |
|----------|-------------|------------|
| **Best Case** (minimal functions/exceptions) | ~500 | Excellent |
| **Typical** (moderate function variety) | ~3,000 | Good |
| **Worst Case** (all permutations) | ~15,000 | Acceptable |

**Prometheus Rule of Thumb**: < 100,000 time series per instance is generally safe.

---

## Recommendations

### 1. Function Name Normalization

To control `function` label cardinality, normalize function names:

```python
# GOOD: Use module-level names
"function": "openfga.check_permission"
"function": "llm.generate"
"function": "cache.get"

# BAD: Include dynamic data
"function": f"check_permission_user_{user_id}"  # Creates unbounded cardinality!
```

### 2. Exception Type Grouping

Group similar exceptions to reduce `exception_type` cardinality:

```python
# GOOD: Use base exception classes
"exception_type": "ConnectionError"
"exception_type": "TimeoutError"
"exception_type": "RateLimitError"

# BAD: Use specific subclasses
"exception_type": "httpx.ConnectTimeout"
"exception_type": "httpx.ReadTimeout"
"exception_type": "httpx.WriteTimeout"  # Creates 3x cardinality
```

### 3. Recording Rules for High-Cardinality Metrics

Use Prometheus recording rules to pre-aggregate high-cardinality metrics:

```yaml
# prometheus-recording-rules.yaml
groups:
  - name: resilience_aggregations
    interval: 30s
    rules:
      # Aggregate retry metrics by function (drop attempt_number)
      - record: retry:attempts:rate5m
        expr: sum by (function) (rate(retry_attempts_total[5m]))

      # Aggregate timeout metrics by operation_type (drop function, timeout_seconds)
      - record: timeout:exceeded:rate5m
        expr: sum by (operation_type) (rate(timeout_exceeded_total[5m]))

      # Aggregate fallback metrics by exception_type (drop function, fallback_type)
      - record: fallback:used:rate5m
        expr: sum by (exception_type) (rate(fallback_used_total[5m]))
```

### 4. Retention Policy

Configure different retention for different metrics:

```yaml
# prometheus.yml
storage:
  tsdb:
    retention.time: 15d  # Default retention

# Use remote_write with relabeling to keep high-cardinality metrics for shorter periods
```

### 5. Alerting on Cardinality Growth

Add an alert for cardinality explosion:

```yaml
# Already included in resilience-alerts.yaml
- alert: ResilienceMetricsCardinalityHigh
  expr: count(count by (__name__, function) ({__name__=~"retry.*|timeout.*|fallback.*"})) > 5000
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "High cardinality detected in resilience metrics"
    description: "More than 5000 unique time series detected. Review function label usage."
```

---

## Monitoring Cardinality

### PromQL Queries

```promql
# Count total time series for resilience metrics
count({__name__=~"circuit_breaker.*|retry.*|timeout.*|bulkhead.*|rate_limit.*|adaptive_bulkhead.*|fallback.*|http_pool.*"})

# Count by metric name
count by (__name__) ({__name__=~"circuit_breaker.*|retry.*|timeout.*|bulkhead.*|rate_limit.*|adaptive_bulkhead.*|fallback.*"})

# Identify high-cardinality labels
topk(10, count by (function) ({__name__=~"retry.*"}))
topk(10, count by (exception_type) ({__name__=~"fallback.*"}))
```

### Grafana Dashboard Panel

Add a cardinality monitoring panel to the Resilience Patterns dashboard:

```json
{
  "title": "Resilience Metrics Cardinality",
  "type": "stat",
  "targets": [
    {
      "expr": "count({__name__=~\"circuit_breaker.*|retry.*|timeout.*|bulkhead.*|rate_limit.*|adaptive_bulkhead.*|fallback.*\"})",
      "legendFormat": "Total Time Series"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "thresholds": {
        "steps": [
          {"color": "green", "value": 0},
          {"color": "yellow", "value": 5000},
          {"color": "red", "value": 15000}
        ]
      }
    }
  }
}
```

---

## Conclusion

The resilience metrics have **acceptable cardinality** with proper usage patterns:

| Risk Level | Metrics | Mitigation |
|------------|---------|------------|
| **Low** | circuit_breaker, bulkhead, rate_limit, adaptive_bulkhead, http_pool | Fixed labels, no action needed |
| **Medium** | retry, timeout, fallback | Use function name normalization, recording rules |

**Key Actions**:
1. Normalize function names to module-level granularity
2. Group exception types to base classes
3. Add recording rules for pre-aggregation
4. Monitor cardinality with the provided PromQL queries

---

## Related Documents

- [Internal: Resilience Patterns](../docs-internal/INTERNAL-0026-RESILIENCE-PATTERNS.md)
- [Alerting Rules](alerting-rules/resilience-alerts.yaml)
- [Operations Runbook](../docs-internal/runbooks/RESILIENCE_OPERATIONS.md)
