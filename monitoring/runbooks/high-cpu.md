# High CPU Alert Runbook

## Overview

This alert fires when CPU utilization exceeds safe thresholds.

## Symptoms

- Increased response latency
- Throttled pod performance
- Potential pod eviction

---

## HighCPUUtilization

### Description
CPU utilization exceeds 85% of limits.

### Impact
**Warning** - May cause latency degradation and throttling.

### Resolution
1. Check CPU-intensive operations in traces
2. Scale horizontally: `kubectl scale deployment mcp-server-langgraph --replicas=N`
3. Review recent code changes for inefficiencies
4. Consider resource limit increases

### Escalation
Create capacity planning ticket if recurring.
