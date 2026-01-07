# SLA/SLO Alert Runbook

This runbook provides troubleshooting guidance for SLA and SLO-related alerts in the MCP Server LangGraph system.

## Overview

SLA (Service Level Agreement) and SLO (Service Level Objective) alerts monitor system availability, performance, and error budgets. These alerts are critical for maintaining service quality commitments.

## Symptoms

When these alerts fire, you may observe:
- Degraded user experience (slow responses, errors)
- Error budget depletion
- Availability metrics below threshold
- Performance degradation

---

## SLOBudgetBurnCritical

### Description
Error budget is being consumed at a critical rate (>14.4x sustainable rate).

### Impact
**Critical** - At current rate, the entire 30-day budget will be exhausted rapidly.

### Resolution
1. Check recent deployments: `kubectl get deployments -n mcp-server`
2. Review error logs: `kubectl logs -l app=mcp-server-langgraph --tail=100`
3. Check dependency health (Redis, PostgreSQL, Keycloak)
4. Consider rollback if recent deployment is the cause

### Escalation
Page on-call SRE immediately. This is a P1 incident.

---

## SLOBudgetBurnHigh

### Description
Error budget is being consumed at an elevated rate (>6x sustainable rate).

### Impact
**Warning** - Budget will be exhausted faster than expected if not addressed.

### Resolution
1. Investigate recent error trends
2. Check for degraded dependencies
3. Review application metrics for anomalies

### Escalation
Notify on-call engineer during business hours.

---

## SLOLatencyP95Breach

### Description
P95 latency exceeds 500ms SLO target.

### Impact
**Critical** - User experience is degraded for a significant portion of requests.

### Resolution
1. Check LLM provider latency: review `llm_request_duration_seconds` metrics
2. Check database query performance
3. Review resource utilization (CPU, memory)
4. Check for network issues

### Escalation
Page on-call if latency doesn't improve within 5 minutes.

---

## SLOLatencyP99Breach

### Description
P99 latency exceeds 2000ms threshold.

### Impact
**Warning** - Tail latency is elevated, affecting worst-case user experience.

### Resolution
1. Identify slow requests in traces
2. Check for resource contention
3. Review complex query patterns

### Escalation
Create ticket for investigation during next business day.

---

## SLOErrorBudgetExhausted

### Description
30-day error budget has been fully consumed.

### Impact
**Critical** - Availability is below the 99.9% SLO target.

### Resolution
1. Consider freezing non-critical deployments
2. Focus all efforts on stability
3. Review and address top error sources

### Escalation
Immediate P1 escalation to engineering leadership.

---

## SLOErrorBudgetLow

### Description
Error budget is below 25% remaining.

### Impact
**Warning** - Limited budget for upcoming changes.

### Resolution
1. Implement risk-reduction measures
2. Increase testing rigor for upcoming changes
3. Consider delaying non-critical releases

### Escalation
Notify engineering manager.

---

## SLOCPUSaturation

### Description
CPU utilization exceeds 85% of limits.

### Impact
**Warning** - May cause latency degradation.

### Resolution
1. Scale horizontally: `kubectl scale deployment mcp-server-langgraph --replicas=N`
2. Identify CPU-intensive operations
3. Consider resource limit increases

### Escalation
Create capacity planning ticket.

---

## SLOMemorySaturation

### Description
Memory utilization exceeds 85% of limits.

### Impact
**Warning** - Risk of OOM events.

### Resolution
1. Check for memory leaks in recent releases
2. Scale horizontally if possible
3. Consider memory limit increases

### Escalation
Create ticket for memory optimization investigation.

---

## SLOConnectionPoolSaturation

### Description
Database connection pool is near saturation (>80%).

### Impact
**Warning** - New requests may be queued or fail.

### Resolution
1. Check for connection leaks
2. Increase pool size in configuration
3. Optimize query patterns to reduce connection hold time

### Escalation
Create database optimization ticket.

---

## SLOPushLatencyHigh

### Description
Push notification delivery P95 latency exceeds 2 seconds.

### Impact
**Warning** - Alert notifications may be delayed.

### Resolution
1. Check push service connectivity
2. Verify VAPID key configuration
3. Review push service provider status

### Escalation
Notify on-call during business hours.

---

## SLOCleanupJobFailures

### Description
Background cleanup job is failing frequently.

### Impact
**Warning** - Stale data may accumulate.

### Resolution
1. Check cleanup job logs
2. Verify database connectivity
3. Review job configuration

### Escalation
Create maintenance ticket.

---

## SLOAIRecommendationErrors

### Description
AI recommendation generation is failing at high rate.

### Impact
**Warning** - AI-assisted remediation is unavailable.

### Resolution
1. Check LLM provider connectivity
2. Verify API keys and quotas
3. Review rate limit status

### Escalation
Notify AI platform team.

---

## SLOAIRecommendationSlow

### Description
AI recommendation generation P95 latency exceeds 30 seconds.

### Impact
**Warning** - Remediation suggestions are delayed.

### Resolution
1. Check LLM provider latency
2. Review prompt complexity
3. Consider caching frequently used recommendations

### Escalation
Create AI performance optimization ticket.

---

## SLAUptimeBreach

### Description
System uptime has fallen below 99.9% SLA target.

### Impact
**Critical** - SLA violation in progress.

### Resolution
1. Identify and resolve the root cause of downtime
2. Document incident timeline
3. Prepare SLA breach report if customer-impacting

### Escalation
Immediate P1 escalation.

---

## SLAResponseTimeBreach

### Description
API P95 response time exceeds 500ms SLA target.

### Impact
**Critical** - SLA violation for response time.

### Resolution
1. Identify slow endpoints
2. Check downstream service latency
3. Review recent changes

### Escalation
Page on-call SRE.

---

## SLAErrorRateBreach

### Description
API error rate exceeds 1% SLA target.

### Impact
**Critical** - SLA violation for reliability.

### Resolution
1. Identify error sources
2. Check for deployment issues
3. Review dependency health

### Escalation
Page on-call SRE.

---

## SLAMonthlyUptimeBudgetExhausted

### Description
Monthly downtime budget for 99.9% SLA has been exhausted.

### Impact
**Critical** - No remaining downtime budget for the month.

### Resolution
1. Focus all efforts on stability
2. Delay risky changes
3. Implement additional redundancy

### Escalation
Escalate to VP Engineering.
