# Session TTL Alert Runbook

## Overview

This alert fires when session TTL (time-to-live) issues are detected.

## Symptoms

- Sessions expiring unexpectedly
- Users needing to re-authenticate frequently
- Inconsistent session lifetimes

---

## SessionTTLIssues

### Description
Session TTL configuration or behavior issues detected.

### Impact
**Warning** - User experience affected by frequent re-authentication.

### Resolution
1. Review session TTL configuration
2. Check Redis EXPIRE commands
3. Verify client-side session handling
4. Review activity-based TTL extension logic

### Escalation
Create ticket for session management review.
