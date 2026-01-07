# Pod Restarts Alert Runbook

## Overview

This alert fires when pods are restarting frequently.

## Symptoms

- Application instability
- Lost in-progress work
- Intermittent failures

---

## HighPodRestarts

### Description
Pod restart count exceeds threshold in time window.

### Impact
**Warning** - Service instability affecting users.

### Resolution
1. Check pod events: `kubectl describe pod <pod-name>`
2. Review container logs for crash reasons
3. Check for OOMKilled status
4. Review liveness/readiness probe configuration

### Escalation
Page on-call if restarts are continuous.
