# LLM Provider Errors Alert Runbook

## Overview

This alert fires when LLM provider API calls are failing at high rate.

## Symptoms

- Failed agent responses
- Timeout errors from LLM providers
- Rate limiting responses

---

## LLMProviderErrors

### Description
LLM provider API error rate exceeds threshold.

### Impact
**Critical** - Agent functionality severely impacted.

### Resolution
1. Check LLM provider status pages (OpenAI, Anthropic, Google)
2. Review rate limit headers in responses
3. Check API key validity and quotas
4. Consider failover to alternative provider

### Escalation
Page on-call for high error rates. Notify AI team.
