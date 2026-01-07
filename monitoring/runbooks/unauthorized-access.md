# Unauthorized Access Alert Runbook

## Overview

This alert fires when unauthorized access attempts are detected.

## Symptoms

- 403 Forbidden responses
- Access denied to protected resources
- Permission check failures

---

## UnauthorizedAccess

### Description
High rate of unauthorized access attempts detected.

### Impact
**Warning/Critical** - May indicate attack or misconfiguration.

### Resolution
1. Review access logs for patterns
2. Check if legitimate users are affected
3. Verify authorization policies in OpenFGA
4. Review recent policy changes

### Escalation
Notify security team if attack suspected.
