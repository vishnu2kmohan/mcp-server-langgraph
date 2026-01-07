# Session Errors Alert Runbook

## Overview

This alert fires when session management errors are occurring at high rate.

## Symptoms

- Users losing session state
- Unexpected logouts
- State inconsistencies

---

## SessionErrors

### Description
Session creation, retrieval, or update errors at high rate.

### Impact
**Warning** - User experience degraded with state loss.

### Resolution
1. Check Redis connectivity (session backend)
2. Review session serialization errors in logs
3. Verify session configuration
4. Check for session size limits

### Escalation
Page on-call if affecting many users.
