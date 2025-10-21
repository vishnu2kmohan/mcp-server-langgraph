# ADR-0030: Resilience Patterns for Production Systems

**Status**: Accepted
**Date**: 2025-10-20
**Deciders**: Engineering Team
**Related**: [ADR-0017: Error Handling Strategy](0017-error-handling-strategy.md), [ADR-0023: Anthropic Tool Design Best Practices](0023-anthropic-tool-design-best-practices.md)

## Context

The MCP server integrates with multiple external services that can fail or become unavailable:
- LLM APIs (Anthropic, OpenAI, Google Gemini) - network failures, rate limits, timeouts
- OpenFGA authorization service - network partitions, slow responses
- Redis session store - connection failures, evictions
- Keycloak SSO - authentication timeouts, certificate issues
- Prometheus metrics - query timeouts, service unavailable

Without proper resilience patterns, a failure in one service can cascade throughout the system, leading to:
- Complete system unavailability (99.99% uptime SLA violation)
- User-facing errors for unrelated operations
- Resource exhaustion (connection pools, memory)
- Difficult debugging and incident response

**Current State**:
- Basic error handling with try-catch blocks
- Some retry logic in `alerting.py` but not standardized
- No circuit breakers or bulkhead isolation
- No request timeout enforcement
- Failures in external services cause immediate user-facing errors

**Target SLA**: 99.99% uptime (< 0.01% error rate, < 52.6 minutes downtime/year)

## Decision

Implement a **comprehensive resilience layer** using the following patterns:

### 1. Circuit Breaker Pattern

**Implementation**: Use `pybreaker` library for production-ready circuit breaker.

**Configuration**:
```python
# Default circuit breaker settings (per service)
CIRCUIT_BREAKER_FAIL_MAX = 5          # Open after 5 failures
CIRCUIT_BREAKER_TIMEOUT_DURATION = 60  # Stay open for 60 seconds
CIRCUIT_BREAKER_EXPECTED_EXCEPTION = Exception
CIRCUIT_BREAKER_LISTENERS = [CircuitBreakerMetricsListener]
```

**Services Protected**:
- LLM API calls (`llm/factory.py`)
- OpenFGA authorization (`auth/openfga.py`)
- Redis operations (`auth/session.py`)
- Keycloak authentication (`auth/keycloak.py`)
- Prometheus queries (`monitoring/prometheus_client.py`)

**Behavior**:
- **Closed** (normal): All requests pass through
- **Open** (failing): Fail fast, return cached/default response
- **Half-Open** (testing): Allow one test request after timeout

### 2. Retry Logic with Exponential Backoff

**Implementation**: Use `tenacity` library for declarative retry policies.

**Configuration**:
```python
# Retry settings by operation type
RETRY_STOP_AFTER_ATTEMPT = 3
RETRY_WAIT_EXPONENTIAL_MULTIPLIER = 1  # 1s, 2s, 4s
RETRY_WAIT_EXPONENTIAL_MAX = 10        # Cap at 10 seconds
RETRY_RERAISE = True                   # Reraise after exhausting retries
```

**Retry Policies**:
- **Idempotent reads**: Retry up to 3 times (GET requests, queries)
- **Idempotent writes**: Retry with idempotency key (POST with dedupe)
- **Non-idempotent writes**: No retries, fail immediately
- **Network errors**: Always retry (transient failures)
- **Client errors (4xx)**: Never retry (permanent failures)
- **Server errors (5xx)**: Retry (temporary failures)

### 3. Request Timeout Enforcement

**Implementation**: Use `asyncio.timeout()` context manager (Python 3.11+) or `asyncio.wait_for()`.

**Configuration**:
```python
# Timeout hierarchy (cascading)
DEFAULT_TIMEOUT = 30           # Global default
LLM_TIMEOUT = 60              # LLM generation can be slow
AUTH_TIMEOUT = 5              # Auth should be fast
DB_TIMEOUT = 10               # Database queries
HTTP_TIMEOUT = 15             # External HTTP calls
```

**Enforcement**:
- All async operations wrapped in timeout context
- Timeouts propagate to OpenTelemetry spans
- Timeout violations logged with full context

### 4. Bulkhead Isolation

**Implementation**: Use `asyncio.Semaphore` for resource pool limits.

**Configuration**:
```python
# Concurrent operation limits (per resource type)
LLM_CONCURRENCY_LIMIT = 10      # Max 10 concurrent LLM calls
OPENFGA_CONCURRENCY_LIMIT = 50  # Max 50 concurrent auth checks
REDIS_CONCURRENCY_LIMIT = 100   # Max 100 concurrent Redis ops
DB_CONCURRENCY_LIMIT = 20       # Max 20 concurrent DB queries
```

**Benefits**:
- Prevent resource exhaustion under load
- Isolate failures (LLM slowdown doesn't block auth)
- Fair resource allocation across operations

### 5. Graceful Degradation Strategies

**Fallback Behaviors**:

| Service | Primary | Fallback | Degraded Mode |
|---------|---------|----------|---------------|
| **OpenFGA** | Check permission | Allow (fail-open) | Auth disabled warning |
| **Redis Sessions** | Distributed cache | In-memory cache | Single-instance only |
| **LLM API** | Primary model | Fallback model | Cached responses |
| **Prometheus** | Real-time metrics | Cached metrics | Stale data warning |
| **Keycloak** | SSO authentication | JWT validation | Limited features |

**Decision Logic**:
```python
if circuit_breaker.is_open():
    return fallback_response()
elif operation_timeout():
    return cached_response()
else:
    return primary_response()
```

## Architecture

### New Module: `src/mcp_server_langgraph/resilience/`

```
resilience/
├── __init__.py                    # Public API
├── circuit_breaker.py             # Circuit breaker decorators
├── retry.py                       # Retry policy decorators
├── timeout.py                     # Timeout enforcement
├── bulkhead.py                    # Concurrency limits
├── fallback.py                    # Fallback strategies
├── metrics.py                     # Resilience metrics
└── config.py                      # Resilience configuration
```

### Decorator-Based API (Developer-Friendly)

```python
from mcp_server_langgraph.resilience import (
    circuit_breaker,
    retry_with_backoff,
    with_timeout,
    with_bulkhead
)

@circuit_breaker(name="openfga", fail_max=5, timeout=60)
@retry_with_backoff(max_attempts=3, exponential_base=2)
@with_timeout(seconds=5)
@with_bulkhead(limit=50)
async def check_permission(user: str, resource: str) -> bool:
    """Check OpenFGA permission with full resilience"""
    async with httpx.AsyncClient() as client:
        response = await client.post(...)
        return response.json()["allowed"]
```

### Metrics & Observability

**New Metrics** (30+ resilience-specific):
```python
# Circuit breaker metrics
circuit_breaker_state{service, state=open|closed|half_open}
circuit_breaker_failures_total{service, error_type}
circuit_breaker_success_total{service}

# Retry metrics
retry_attempts_total{service, attempt_number}
retry_exhausted_total{service}
retry_success_after_retry_total{service}

# Timeout metrics
timeout_violations_total{service, operation}
timeout_duration_seconds{service, operation}

# Bulkhead metrics
bulkhead_rejections_total{service}
bulkhead_queue_depth{service}
bulkhead_active_operations{service}
```

**Observability**:
- All resilience events logged with trace context
- Circuit breaker state changes → alerts
- Retry exhaustion → error logs with full context
- Timeout violations → distributed traces
- Grafana dashboard: `monitoring/grafana/dashboards/resilience.json`

## Consequences

### Positive

1. **Improved Availability**
   - Achieve 99.99% uptime SLA (< 52.6 min downtime/year)
   - Graceful degradation instead of complete failures
   - Isolated failures prevent cascading issues

2. **Better User Experience**
   - Fast failures with circuit breakers (no hanging requests)
   - Cached responses during outages
   - Clear error messages about degraded services

3. **Operational Excellence**
   - Clear metrics for debugging incidents
   - Automated recovery (circuit breaker half-open state)
   - Reduced MTTR (Mean Time To Recovery)

4. **Cost Optimization**
   - Fewer wasted API calls (circuit breaker fail-fast)
   - Reduced resource consumption (bulkhead limits)
   - Lower cloud infrastructure costs

5. **Developer Experience**
   - Simple decorator-based API
   - Standardized resilience across codebase
   - Clear configuration and documentation

### Negative

1. **Complexity**
   - New module to maintain (`resilience/`)
   - More configuration parameters
   - Debugging is harder (need to trace through resilience layer)

2. **Configuration Overhead**
   - Need to tune per-service parameters (fail_max, timeout, etc.)
   - Risk of misconfiguration (fail-open vs fail-closed)
   - Requires load testing to find optimal values

3. **Performance Overhead**
   - Circuit breaker state checks add latency (~1-2ms)
   - Retry logic increases total request time
   - Metrics collection overhead (~1% CPU)

4. **False Positives**
   - Circuit breaker may open during legitimate load spikes
   - Aggressive timeouts may kill slow but valid requests
   - Bulkhead limits may reject valid traffic

### Mitigations

1. **Start Conservative**: Use lenient defaults, tighten based on metrics
2. **A/B Testing**: Roll out resilience patterns incrementally (10% → 50% → 100%)
3. **Feature Flags**: Enable/disable resilience per service
4. **Monitoring**: Alert on circuit breaker state changes
5. **Documentation**: Comprehensive troubleshooting guide

## Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Create `resilience/` module structure
- [ ] Implement circuit breaker with `pybreaker`
- [ ] Implement retry logic with `tenacity`
- [ ] Add timeout enforcement with `asyncio.timeout()`
- [ ] Add bulkhead isolation with `asyncio.Semaphore`
- [ ] Create configuration schema in `config.py`
- [ ] Write 50+ unit tests for resilience patterns

### Phase 2: Integration (Week 2)
- [ ] Apply resilience decorators to `llm/factory.py`
- [ ] Apply resilience decorators to `auth/openfga.py`
- [ ] Apply resilience decorators to `auth/session.py`
- [ ] Apply resilience decorators to `auth/keycloak.py`
- [ ] Apply resilience decorators to `monitoring/prometheus_client.py`
- [ ] Update all HTTP clients with default timeouts

### Phase 3: Observability (Week 3)
- [ ] Implement resilience metrics in `resilience/metrics.py`
- [ ] Create Grafana dashboard `resilience.json`
- [ ] Add circuit breaker state change alerts
- [ ] Integrate with OpenTelemetry tracing
- [ ] Write integration tests with failure injection

### Phase 4: Validation (Week 4)
- [ ] Chaos testing: Kill Redis, verify graceful degradation
- [ ] Load testing: 1000 req/s, verify no cascade failures
- [ ] Circuit breaker testing: Force failures, verify auto-recovery
- [ ] Timeout testing: Inject slow responses, verify fail-fast
- [ ] Performance testing: Measure overhead (target < 2%)

### Phase 5: Documentation & Rollout (Week 5)
- [ ] Update developer guide with resilience examples
- [ ] Create runbook for circuit breaker incidents
- [ ] Add configuration reference to docs
- [ ] Roll out to production (10% → 50% → 100%)
- [ ] Monitor for 2 weeks, tune configuration

## Alternatives Considered

### Alternative 1: Use Istio Service Mesh
- **Pros**: Resilience at infrastructure level, language-agnostic
- **Cons**: Requires Kubernetes, complex setup, not available locally
- **Decision**: Keep as option for production, implement application-level first

### Alternative 2: Use AWS App Mesh / Google Traffic Director
- **Pros**: Cloud-native, managed service
- **Cons**: Vendor lock-in, only works in specific clouds
- **Decision**: Application-level resilience is cloud-agnostic

### Alternative 3: No Resilience (Current State)
- **Pros**: Simple, no overhead
- **Cons**: Cannot achieve 99.99% SLA, poor user experience
- **Decision**: Unacceptable for production

### Alternative 4: Use NGINX/HAProxy for Retry/Timeout
- **Pros**: Battle-tested, high performance
- **Cons**: Only covers HTTP, not Redis/DB, limited customization
- **Decision**: Combine with application-level for full coverage

## References

- **Circuit Breaker Pattern**: https://martinfowler.com/bliki/CircuitBreaker.html
- **Release It! (Nygard)**: https://pragprog.com/titles/mnee2/release-it-second-edition/
- **pybreaker Library**: https://github.com/danielfm/pybreaker
- **tenacity Library**: https://github.com/jd/tenacity
- **Google SRE Book - Handling Overload**: https://sre.google/sre-book/handling-overload/
- **AWS Well-Architected - Reliability Pillar**: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/
- **ADR-0017: Error Handling Strategy**: ./0017-error-handling-strategy.md
- **ADR-0023: Anthropic Tool Design Best Practices**: ./0023-anthropic-tool-design-best-practices.md

## Success Metrics

### Availability
- **Target**: 99.99% uptime (< 52.6 min downtime/year)
- **Measurement**: Prometheus `up` metric, SLA dashboard

### Performance
- **Target**: P95 latency < 500ms (even with failures)
- **Measurement**: Histogram `http_request_duration_seconds{quantile="0.95"}`

### Error Rate
- **Target**: < 0.01% error rate under normal load
- **Measurement**: `http_requests_total{status=~"5.."} / http_requests_total`

### Recovery Time
- **Target**: MTTR < 5 minutes (circuit breaker auto-recovery)
- **Measurement**: Time from circuit open → half-open → closed

### Overhead
- **Target**: < 2% CPU overhead from resilience layer
- **Measurement**: CPU profiling before/after resilience implementation

## Migration Path

### Backward Compatibility
- All resilience patterns are **opt-in via decorators**
- Existing code continues to work without changes
- Feature flag: `FF_ENABLE_RESILIENCE_PATTERNS=true`

### Rollout Strategy
1. **Development**: Enable for all services, test thoroughly
2. **Staging**: A/B test (50% traffic with resilience)
3. **Production**: Gradual rollout (10% → 25% → 50% → 100% over 4 weeks)
4. **Monitoring**: Watch for regressions, roll back if needed

### Rollback Plan
- Disable feature flag: `FF_ENABLE_RESILIENCE_PATTERNS=false`
- Remove decorators if causing issues
- Fall back to basic error handling

---

**Last Updated**: 2025-10-20
**Next Review**: 2025-11-20 (after 1 month in production)
