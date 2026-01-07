# Insufficient Replicas Alert Runbook

## Overview

This alert fires when the number of running replicas is below the desired count.

## Symptoms

- Reduced capacity
- Increased latency due to fewer pods
- Risk of complete outage

---

## InsufficientReplicas

### Description
Running replicas are fewer than desired replica count.

### Impact
**Warning** - Reduced capacity may affect performance.

### Resolution
1. Check pod status: `kubectl get pods -l app=mcp-server-langgraph`
2. Review pod events: `kubectl describe pod <pod-name>`
3. Check for node resource issues
4. Review HPA settings if autoscaling enabled

### Escalation
Page on-call if replicas remain below minimum.
