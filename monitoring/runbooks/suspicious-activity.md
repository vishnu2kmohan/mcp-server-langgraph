# Suspicious Activity Alert Runbook

## Overview

This alert fires when potentially malicious activity is detected.

## Symptoms

- Unusual access patterns
- Failed authentication attempts
- Unexpected API usage

---

## SuspiciousActivity

### Description
Security-related anomalies detected in request patterns.

### Impact
**Warning/Critical** - Potential security incident.

### Resolution
1. Review security logs for details
2. Identify source IP and user accounts involved
3. Check for known attack patterns
4. Consider temporary access restrictions

### Escalation
Notify security team immediately. Follow incident response procedures.
