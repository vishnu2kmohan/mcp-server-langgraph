# Authorization Spike Alert Runbook

## Overview

This alert fires when there's an unusual spike in authorization check failures, indicating potential access control issues.

## Symptoms

- Sudden increase in authorization failures
- Users reporting access denied errors
- High load on OpenFGA authorization service

---

## AuthorizationSpike

### Description
Authorization failure rate has increased significantly.

### Impact
**Warning** - Users may be unable to access resources.

### Resolution
1. Check OpenFGA logs: `kubectl logs -l app=openfga --tail=200`
2. Review recent authorization policy changes
3. Check for user/group membership issues
4. Verify relationship tuple consistency

### Escalation
If widespread access issues, page on-call immediately.
