# Slow LLM Alert Runbook

## Overview

This alert fires when LLM provider response times are elevated.

## Symptoms

- Slow agent responses
- Timeout errors
- User-perceived delays

---

## SlowLLMResponses

### Description
LLM provider latency exceeds acceptable thresholds.

### Impact
**Warning** - User experience degraded with slow responses.

### Resolution
1. Check LLM provider status pages
2. Review request complexity (prompt size, token count)
3. Consider using faster models for simple tasks
4. Check for provider rate limiting

### Escalation
Notify AI team if persistent. Consider provider failover.
