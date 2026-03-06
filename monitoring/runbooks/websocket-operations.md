# WebSocket Operations Runbook

## Overview

This runbook covers alerts related to WebSocket protocol operations,
including version mismatches and protocol drift detection.

## Symptoms

When these alerts fire, you may observe:
- WebSocket protocol version mismatches between client and server
- Connection failures due to incompatible protocol versions
- Degraded real-time functionality in the frontend
- Increased reconnection attempts

---

## Protocol-Version-Mismatch

### Alert: WebSocketProtocolVersionMismatch

**Severity**: Warning

### Diagnosis

1. **Check protocol version metrics**
   ```bash
   curl -s localhost:8000/metrics | grep websocket_protocol_version
   ```

2. **Check client versions**
   ```bash
   kubectl logs -l app=langgraph-agent -n mcp-server --tail=100 | grep "protocol version"
   ```

### Resolution

1. Verify frontend deployment matches expected protocol version
2. Check for stale client connections using old protocol
3. If clients are outdated, coordinate frontend deployment
4. For gradual rollout issues, verify WebSocket upgrade headers

---

## Critical-Protocol-Version-Drift

### Alert: WebSocketProtocolVersionDriftCritical

**Severity**: Critical

### Resolution

1. Identify which clients are using incompatible versions
2. Force disconnect stale clients if necessary
3. Ensure frontend and backend are deployed in sync
   ```bash
   kubectl get deployments -n mcp-server -o wide
   ```

## Escalation

- **On-call SRE**: Slack #sre-oncall
- **Service Owner**: @langgraph-team
- **Critical alerts**: Page via PagerDuty
