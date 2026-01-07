# SLA Uptime Alert Runbook

This runbook provides troubleshooting guidance for SLA uptime and compliance alerts.

## Overview

SLA uptime alerts monitor system availability, response time compliance, error rates, and resource utilization to ensure contractual SLA commitments are met.

## Symptoms

When these alerts fire, you may observe:
- Availability metrics falling below SLA thresholds
- Response times exceeding SLA targets
- Error rates approaching SLA limits
- Resource saturation affecting performance
- Projected SLA breach based on trends

---

## SLAUptimeAtRisk

### Description
System uptime is trending toward SLA breach threshold.

### Impact
**Warning** - SLA compliance at risk if trend continues.

### Resolution
1. Check current uptime metrics: review recent incidents
2. Identify sources of downtime (deployments, incidents)
3. Review incident management processes
4. Consider freezing risky changes

### Escalation
Notify engineering manager. Prepare SLA status report.

---

## SLAResponseTimeAtRisk

### Description
Response time metrics are approaching SLA breach threshold.

### Impact
**Warning** - Response time SLA at risk.

### Resolution
1. Check P95 latency trends
2. Identify slow endpoints from traces
3. Review LLM provider latency
4. Check database query performance

### Escalation
Notify on-call for performance investigation.

---

## SLAResponseTimeP99Breach

### Description
P99 response time has exceeded SLA threshold.

### Impact
**Warning** - Tail latency SLA violation.

### Resolution
1. Identify outlier requests causing P99 spikes
2. Check for resource contention
3. Review complex query patterns
4. Consider request timeout adjustments

### Escalation
Create performance optimization ticket.

---

## SLAErrorRateAtRisk

### Description
Error rate is approaching SLA threshold.

### Impact
**Warning** - Error rate SLA at risk.

### Resolution
1. Check error logs for patterns
2. Identify error sources by endpoint
3. Review recent deployments
4. Check dependency health

### Escalation
Notify on-call if error rate continues climbing.

---

## SLAThroughputDegraded

### Description
System throughput has dropped significantly.

### Impact
**Warning** - Capacity may be insufficient.

### Resolution
1. Check request rate trends
2. Verify autoscaling is working
3. Review resource limits
4. Check for bottlenecks (database, LLM providers)

### Escalation
Create capacity planning ticket.

---

## SLAComplianceScoreLow

### Description
Overall SLA compliance score is below target.

### Impact
**Warning** - Multiple SLA metrics contributing to low score.

### Resolution
1. Review individual SLA metrics
2. Identify top contributors to low score
3. Prioritize remediation by impact
4. Create action plan for improvement

### Escalation
Escalate to engineering leadership.

---

## SLAProjectedBreach

### Description
Current trends project SLA breach within reporting period.

### Impact
**Warning** - SLA breach likely without intervention.

### Resolution
1. Review projection methodology
2. Identify correctable issues
3. Implement immediate mitigations
4. Prepare communication plan

### Escalation
Immediate escalation to VP Engineering.

---

## SLADependencyDegraded

### Description
Critical dependency is degraded, affecting SLA.

### Impact
**Warning** - SLA at risk due to dependency issues.

### Resolution
1. Identify degraded dependency from metrics
2. Check dependency status pages
3. Consider fallback or failover options
4. Contact dependency vendor if external

### Escalation
Page on-call for critical dependency issues.

---

## SLAResourceCPUHigh

### Description
CPU utilization is high, potentially affecting SLA.

### Impact
**Warning** - Performance may be impacted.

### Resolution
1. Check CPU utilization by pod
2. Scale horizontally if possible
3. Identify CPU-intensive operations
4. Consider resource limit increases

### Escalation
Create capacity planning ticket.

---

## SLAResourceMemoryHigh

### Description
Memory utilization is high, potentially affecting SLA.

### Impact
**Warning** - Risk of OOM affecting availability.

### Resolution
1. Check memory utilization by pod
2. Look for memory leaks
3. Scale horizontally if possible
4. Consider memory limit increases

### Escalation
Create capacity planning ticket.
