# Resilience Pattern Alert Runbook

This runbook provides troubleshooting guidance for resilience pattern alerts.

## Overview

Resilience alerts monitor circuit breakers, retry patterns, bulkheads, and connection pools. These patterns protect the system from cascading failures.

## Symptoms

When these alerts fire, you may observe:
- Circuit breakers in OPEN state
- Retry exhaustion errors
- Connection pool saturation
- Degraded LLM provider performance

---

## SLOResilienceHealthDegraded

### Description
Overall resilience health score has dropped below 70%.

### Impact
**Warning** - Multiple resilience patterns indicating stress.

### Resolution
1. Check circuit breaker states: `circuit_breaker_state{} == 1`
2. Review retry exhaustion rates
3. Monitor connection pool utilization
4. Check LLM provider adaptive bulkhead status

### Escalation
Notify on-call for comprehensive review.

---

## SLOResilienceCircuitBreakerImpact

### Description
One or more circuit breakers are in OPEN state.

### Impact
**Critical** - Requests to affected services failing fast.

### Resolution
1. Identify open circuit breakers from metrics
2. Check underlying service health
3. Review error patterns that triggered the breaker
4. Wait for half-open transition or manual reset

### Escalation
Page on-call immediately for critical services.

---

## SLOResilienceRetryExhaustion

### Description
High rate of operations failing after all retry attempts.

### Impact
**Warning** - Persistent issues causing complete failures.

### Resolution
1. Identify which operations are exhausting retries
2. Check downstream service health
3. Review retry configuration (max attempts, backoff)
4. Consider circuit breaker activation

### Escalation
Notify on-call for investigation.

---

## SLOResilienceHTTPPoolSaturation

### Description
HTTP connection pool utilization exceeds 85%.

### Impact
**Warning** - Request queueing may increase latency.

### Resolution
1. Check for connection leaks
2. Review connection timeout settings
3. Consider increasing pool size
4. Identify slow downstream services

### Escalation
Create capacity planning ticket.

---

## SLOResilienceLLMProviderDegraded

### Description
LLM provider adaptive bulkheads at minimum capacity.

### Impact
**Warning** - LLM providers experiencing rate limiting or errors.

### Resolution
1. Check LLM provider status pages
2. Review rate limit headers in responses
3. Consider fallback to alternative providers
4. Reduce request rate if possible

### Escalation
Notify AI team and consider provider failover.
