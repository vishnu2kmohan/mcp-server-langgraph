# High Latency Alert Runbook

## Overview

This alert fires when response latency exceeds acceptable thresholds.

## Symptoms

- Slow API responses
- User-reported delays
- Timeout errors

---

## HighLatency

### Description
P95 or P99 latency exceeds SLO targets.

### Impact
**Warning/Critical** - User experience degraded.

### Resolution
1. Check slow requests in distributed traces
2. Review LLM provider latency (often the bottleneck)
3. Check database query performance
4. Review resource utilization (CPU, memory)

### Escalation
Page on-call if latency doesn't improve within 5 minutes.
