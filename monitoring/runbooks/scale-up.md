# Scale Up Alert Runbook

## Overview

This alert fires when the system is scaling up due to increased load.

## Symptoms

- Increased pod count
- Higher resource utilization
- Traffic spike detected

---

## ScaleUp

### Description
Horizontal Pod Autoscaler is scaling up replicas.

### Impact
**Info** - Normal autoscaling behavior during high traffic.

### Resolution
1. Verify this is expected (traffic increase)
2. Check HPA metrics: `kubectl get hpa`
3. Monitor resource availability on nodes
4. Verify new pods are healthy

### Escalation
No escalation unless scaling is failing or unexpected.
