# Orchestrator Operations Runbook

## Overview

This runbook covers alerts related to the orchestrator status broadcasting subsystem,
including queue depth monitoring, failure rates, and subscriber connectivity.

## Symptoms

When these alerts fire, you may observe:
- High queue depth in the orchestrator status broadcaster
- Delayed or missed status updates in the frontend
- WebSocket subscriber disconnections
- Increased error rates in orchestrator operations

---

## High-Queue-Depth

### Alert: OrchestratorQueueDepthHigh

**Severity**: Warning

### Diagnosis

1. **Check broadcaster queue metrics**
   ```bash
   curl -s localhost:8000/metrics | grep orchestrator_queue
   ```

2. **Check subscriber count**
   ```bash
   curl -s localhost:8000/metrics | grep orchestrator_subscriber
   ```

3. **Check pod resource usage**
   ```bash
   kubectl top pods -l app=langgraph-agent -n mcp-server
   ```

### Resolution

1. Check for slow consumers causing backpressure
2. Verify WebSocket connections are healthy
3. If queue continues to grow, restart the affected pod
   ```bash
   kubectl rollout restart deployment/langgraph-agent -n mcp-server
   ```

---

## Critical-Queue-Depth

### Alert: OrchestratorQueueDepthCritical

**Severity**: Critical

### Resolution

1. Immediate: Scale up replicas to handle load
   ```bash
   kubectl scale deployment/langgraph-agent -n mcp-server --replicas=3
   ```
2. Investigate root cause of queue buildup

---

## High-Failure-Rate

### Alert: OrchestratorFailureRateHigh

**Severity**: Warning

### Resolution

1. Check application logs for error patterns
   ```bash
   kubectl logs -l app=langgraph-agent -n mcp-server --tail=200 | grep ERROR
   ```
2. Verify downstream dependencies are healthy
3. Check for resource exhaustion

---

## Subscriber-Disconnect

### Alert: OrchestratorSubscriberDisconnect

**Severity**: Warning

### Resolution

1. Check WebSocket connection health
2. Verify network policies allow WebSocket connections
3. Check for client-side connection issues

## Escalation

- **On-call SRE**: Slack #sre-oncall
- **Service Owner**: @langgraph-team
- **Critical alerts**: Page via PagerDuty
