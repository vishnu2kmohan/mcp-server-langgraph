# High Memory Alert Runbook

## Overview

This alert fires when memory utilization exceeds safe thresholds.

## Symptoms

- Increased garbage collection
- Risk of OOM kills
- Performance degradation

---

## HighMemoryUtilization

### Description
Memory utilization exceeds 85% of limits.

### Impact
**Warning** - Risk of OOM events affecting availability.

### Resolution
1. Check for memory leaks in recent releases
2. Review heap dumps if available
3. Scale horizontally if possible
4. Consider memory limit increases

### Escalation
Create ticket for memory optimization investigation.
