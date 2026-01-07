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

---

## CircuitBreakerRecovering

### Alert Definition
```yaml
alert: CircuitBreakerRecovering
expr: circuit_breaker_state == 0.5
for: 2m
severity: info
```

### Severity
**INFO** - Awareness, no immediate action required

### Impact
- Circuit breaker is in HALF-OPEN state, testing if service has recovered
- Limited traffic being sent to the protected service
- System is attempting automatic recovery

### Diagnosis

1. **Check which circuit breaker is recovering**
   ```promql
   circuit_breaker_state{} == 0.5
   ```

2. **Review recent state transitions**
   ```promql
   rate(circuit_breaker_state_changes_total[10m])
   ```

3. **Check underlying service health**
   - Review logs for the affected service
   - Check error rates before circuit opened

### Resolution

1. **If recovery is successful**
   - No action needed, circuit will close automatically
   - Monitor for stability

2. **If recovery fails repeatedly**
   - Investigate underlying service issues
   - Consider manual intervention
   - Review circuit breaker thresholds

### Escalation
Create ticket for investigation if recovery takes >10 minutes.

---

## TransientErrorsElevated

### Alert Definition
```yaml
alert: TransientErrorsElevated
expr: rate(retry_success_after_retry_total[5m]) > 0.5
for: 10m
severity: info
```

### Severity
**INFO** - Working as expected but indicates underlying instability

### Impact
- Retries are succeeding, so user experience is maintained
- Additional latency from retry attempts
- Increased load on downstream services

### Diagnosis

1. **Identify affected functions**
   ```promql
   rate(retry_success_after_retry_total[5m]) > 0
   ```

2. **Check retry attempt distribution**
   ```promql
   histogram_quantile(0.95, rate(retry_attempts_bucket[5m]))
   ```

3. **Review downstream service health**
   - Check for intermittent network issues
   - Review service logs for transient errors

### Resolution

1. **Short-term**
   - Monitor for escalation to retry exhaustion
   - Retries are working, no immediate action needed

2. **Long-term**
   - Investigate root cause of transient failures
   - Consider adjusting retry policies if too aggressive
   - Review network stability

### Escalation
Create ticket for root cause analysis.

---

## BulkheadQueueDeepening

### Alert Definition
```yaml
alert: BulkheadQueueDeepening
expr: bulkhead_queue_depth > 10
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Requests are queueing, indicating capacity constraints
- Increased latency for queued requests
- Risk of queue overflow and rejected requests

### Diagnosis

1. **Check queue depth by resource type**
   ```promql
   bulkhead_queue_depth
   ```

2. **Check bulkhead utilization**
   ```promql
   bulkhead_active_calls / bulkhead_max_concurrent
   ```

3. **Identify bottleneck**
   - Review which resource type is constrained
   - Check for slow downstream operations

### Resolution

1. **If temporary spike**
   - Queue will drain naturally
   - Monitor for stabilization

2. **If sustained**
   - Consider increasing bulkhead limits
   - Scale affected service horizontally
   - Optimize slow operations

3. **Emergency**
   - Implement load shedding
   - Enable graceful degradation

### Escalation
Page on-call if queue depth exceeds 50 or request rejections begin.

---

## AdaptiveBulkheadUnstable

### Alert Definition
```yaml
alert: AdaptiveBulkheadUnstable
expr: rate(adaptive_bulkhead_adjustments_total[5m]) > 0.1
for: 10m
severity: info
```

### Severity
**INFO** - System is auto-tuning, monitoring recommended

### Impact
- Concurrency limits are changing frequently
- May indicate unstable backend performance
- System is attempting to find optimal limits

### Diagnosis

1. **Check adjustment patterns**
   ```promql
   rate(adaptive_bulkhead_adjustments_total[5m]) by (provider, direction)
   ```

2. **Review current limits**
   ```promql
   adaptive_bulkhead_current_limit
   ```

3. **Check backend latency variability**
   - High latency variance causes frequent adjustments
   - Review provider performance metrics

### Resolution

1. **If backend is unstable**
   - Investigate provider issues
   - Consider switching to static limits temporarily

2. **If tuning is aggressive**
   - Adjust adaptive algorithm parameters
   - Increase stabilization window

3. **If provider is degraded**
   - Enable fallback to alternative provider
   - Notify AI platform team

### Escalation
Create ticket if instability persists >30 minutes.

---

## RateLimitWaitTimeHigh

### Alert Definition
```yaml
alert: RateLimitWaitTimeHigh
expr: histogram_quantile(0.95, rate(rate_limit_wait_time_bucket[5m])) > 5000
for: 5m
severity: warning
```

### Severity
**WARNING** - User experience may be impacted

### Impact
- Requests waiting >5 seconds for rate limit tokens
- Increased latency visible to users
- May indicate rate limit exhaustion

### Diagnosis

1. **Check wait time by provider**
   ```promql
   histogram_quantile(0.95, rate(rate_limit_wait_time_bucket[5m])) by (provider)
   ```

2. **Check token availability**
   ```promql
   rate_limit_tokens_available
   ```

3. **Review request rate**
   - Compare current rate to limit
   - Check for traffic spikes

### Resolution

1. **Short-term**
   - Reduce request rate if possible
   - Enable request queuing with backpressure

2. **Long-term**
   - Request quota increase from provider
   - Implement request batching
   - Consider multi-provider load balancing

3. **If provider issue**
   - Check provider status page
   - Failover to alternative provider

### Escalation
Page on-call if wait times exceed 30 seconds.

---

## FallbackActivated

### Alert Definition
```yaml
alert: FallbackActivated
expr: rate(fallback_used_total[5m]) > 0
for: 1m
severity: info
```

### Severity
**INFO** - Graceful degradation working

### Impact
- Primary service unavailable
- Fallback providing degraded functionality
- User experience maintained with limitations

### Diagnosis

1. **Check fallback usage**
   ```promql
   rate(fallback_used_total[5m]) by (function, fallback_type, exception_type)
   ```

2. **Identify failure reason**
   - Check exception_type label
   - Review primary service logs

3. **Verify fallback behavior**
   - Confirm fallback is providing expected response
   - Check for any fallback errors

### Resolution

1. **Immediate**
   - Fallback is working, no urgent action needed
   - Monitor for escalation

2. **Root cause**
   - Investigate primary service failure
   - Review error patterns

3. **Recovery**
   - Verify primary service recovery
   - Monitor for automatic failback

### Escalation
Create ticket for primary service investigation.

---

## FallbackUsageSustained

### Alert Definition
```yaml
alert: FallbackUsageSustained
expr: rate(fallback_used_total[5m]) > 0.1
for: 15m
severity: warning
```

### Severity
**WARNING** - Prolonged primary service outage

### Impact
- Primary service down for extended period
- Fallback handling significant traffic
- Degraded functionality for 15+ minutes

### Diagnosis

1. **Check duration and scope**
   ```promql
   rate(fallback_used_total[5m]) by (function)
   ```

2. **Review primary service status**
   - Check circuit breaker state
   - Review service health endpoints

3. **Assess fallback capacity**
   - Verify fallback can sustain load
   - Check for fallback degradation

### Resolution

1. **Priority: Restore primary**
   - Focus on primary service recovery
   - Check for deployment issues
   - Review dependencies

2. **If primary unrecoverable short-term**
   - Ensure fallback is stable
   - Communicate degraded status
   - Prepare incident report

3. **Post-recovery**
   - Monitor failback to primary
   - Conduct incident review

### Escalation
Page on-call SRE for primary service investigation.

---

## ResilienceMetricsCardinalityGrowth

### Alert Definition
```yaml
alert: ResilienceMetricsCardinalityGrowth
expr: count({__name__=~"circuit_breaker.*|retry.*|..."}) growth > 1000
for: 30m
severity: info
```

### Severity
**INFO** - Monitoring health concern

### Impact
- Rapid growth in time series count
- May impact Prometheus/Mimir performance
- Could indicate label explosion

### Diagnosis

1. **Check cardinality by metric type**
   ```promql
   count by (__name__) ({__name__=~"circuit_breaker.*|retry.*|timeout.*|bulkhead.*"})
   ```

2. **Identify high-cardinality labels**
   - Look for dynamic values in labels
   - Check for request ID or trace ID in labels

3. **Review recent changes**
   - New services or endpoints
   - Configuration changes

### Resolution

1. **Identify culprit metrics**
   - Find metrics with highest cardinality growth
   - Review label values

2. **Fix label explosion**
   - Remove high-cardinality labels
   - Aggregate dynamic values
   - Use recording rules for aggregation

3. **Prevent recurrence**
   - Add cardinality limits
   - Review metric naming conventions
   - Implement metric allow/deny lists

### Escalation
Create ticket for observability team.
