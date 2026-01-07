# High Error Rate Alert Runbook

## Overview

This alert fires when the application error rate exceeds acceptable thresholds.

## Symptoms

- Increased 5xx responses
- User-facing errors
- Error budget consumption

---

## HighErrorRate

### Description
Error rate exceeds threshold (typically >1%).

### Impact
**Critical** - User experience degraded, SLO at risk.

### Resolution
1. Check error logs: `kubectl logs -l app=mcp-server-langgraph --tail=200`
2. Review recent deployments for regressions
3. Check dependency health (database, Redis, LLM providers)
4. Consider rollback if deployment-related

### Escalation
Page on-call immediately for >5% error rate.
