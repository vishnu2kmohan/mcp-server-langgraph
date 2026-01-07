# Low Disk Space Alert Runbook

## Overview

This alert fires when disk space utilization is approaching capacity.

## Symptoms

- Application write failures
- Log rotation issues
- Database storage problems

---

## LowDiskSpace

### Description
Disk utilization exceeds warning threshold (typically 80%).

### Impact
**Warning** - Risk of service disruption when disk fills.

### Resolution
1. Identify large files/directories: `du -sh /*`
2. Clean up old logs and temporary files
3. Expand PVC if on Kubernetes
4. Review log retention policies

### Escalation
Create infrastructure ticket for disk expansion.
