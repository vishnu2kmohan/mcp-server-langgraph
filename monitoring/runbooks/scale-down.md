# Scale Down Alert Runbook

## Overview

This alert fires when the system is scaling down, often as an informational notice.

## Symptoms

- Reduced pod count
- Lower resource utilization
- Cost optimization in effect

---

## ScaleDown

### Description
Horizontal Pod Autoscaler is scaling down replicas.

### Impact
**Info** - Normal autoscaling behavior during low traffic.

### Resolution
1. Verify this is expected (low traffic period)
2. Check HPA metrics: `kubectl get hpa`
3. Review minimum replica settings
4. Ensure graceful shutdown is working

### Escalation
No escalation needed unless unexpected during peak hours.
