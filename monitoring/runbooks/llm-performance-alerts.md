# LLM Performance Alerts Runbook

## Overview

This runbook covers alerts related to LLM (Large Language Model) performance and availability.

---

## SlowLLMResponses

### Alert Definition
```yaml
alert: SlowLLMResponses
expr: histogram_quantile(0.95, rate(llm_request_duration_seconds_bucket[5m])) > 10
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Poor user experience
- Conversation timeouts
- Potential cascade to response time SLA breach

### Diagnosis

1. **Check LLM latency by provider**
   ```promql
   histogram_quantile(0.95, sum by (provider, le) (rate(llm_request_duration_seconds_bucket[5m])))
   ```

2. **Check LLM provider status pages**
   - OpenAI: https://status.openai.com/
   - Anthropic: https://status.anthropic.com/
   - Google AI: https://status.cloud.google.com/

3. **Check request patterns**
   - Large prompts causing slow responses
   - High token counts
   - Complex tool use scenarios

4. **Check for rate limiting**
   ```promql
   rate(llm_errors_total{error_type="rate_limit"}[5m])
   ```

### Resolution

1. **If provider is experiencing issues**
   - Enable fallback model if configured
   - Communicate status to users
   - Monitor provider status page

2. **If rate limited**
   - Review rate limit configuration
   - Consider request queuing
   - Upgrade API tier if persistent

3. **If prompt is too large**
   - Review conversation truncation settings
   - Implement prompt compression
   - Consider chunking for large documents

4. **Enable fallback model**
   ```bash
   # If using feature flags
   kubectl set env deployment/langgraph-agent LLM_FALLBACK_ENABLED=true
   ```

### Escalation
- **On-call SRE**: For infrastructure issues
- **AI/ML Team**: For model configuration

---

## LLMHighErrorRate

### Alert Definition
```yaml
alert: LLMHighErrorRate
expr: rate(llm_errors_total[5m]) / rate(llm_requests_total[5m]) > 0.1
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 15 minutes

### Impact
- Agent conversations failing
- Tool calls not executing
- User experience degraded

### Diagnosis

1. **Check error types**
   ```promql
   sum by (error_type, provider) (rate(llm_errors_total[5m]))
   ```

2. **Common error types:**
   - `rate_limit` - API rate limits exceeded
   - `auth_error` - Invalid API key
   - `timeout` - Request timeout
   - `invalid_request` - Malformed request
   - `server_error` - Provider server error

3. **Check API key validity**
   - Verify keys are not expired
   - Check quota remaining on provider dashboard

### Resolution

1. **If `rate_limit` errors**
   - Implement request throttling
   - Enable request queuing
   - Consider upgrading API tier

2. **If `auth_error`**
   - Rotate API keys
   - Verify key is correctly mounted as secret
   ```bash
   kubectl get secret llm-api-keys -o yaml | grep -v "^data:" | head -20
   ```

3. **If `timeout` errors**
   - Increase request timeout
   - Check for network issues
   - Reduce prompt complexity

4. **If `server_error`**
   - Provider issue - check status page
   - Enable fallback model
   - Implement retry logic

### Escalation
- **On-call SRE**: For infrastructure issues
- **Finance/Ops**: For billing issues

---

## LLMBudgetWarning

### Alert Definition
```yaml
alert: LLMBudgetWarning
expr: sum(increase(llm_cost_usd_total[24h])) > (monthly_budget_usd / 30 * 1.2)
for: 1h
severity: warning
```

### Severity
**WARNING** - Response within 1 hour

### Impact
- Risk of exceeding monthly LLM budget
- Potential service interruption if hard limits configured
- Financial impact

### Diagnosis

1. **Check current spend**
   - View LLM Cost Monitoring dashboard
   ```promql
   sum(increase(llm_cost_usd_total[24h]))
   ```

2. **Identify high-cost operations**
   ```promql
   sum by (model, operation) (increase(llm_cost_usd_total[24h]))
   ```

3. **Check for abuse or misconfiguration**
   - Unusually high token counts
   - Repeated failed operations
   - Runaway loops

### Resolution

1. **If unexpected high usage**
   - Identify source (user, operation, model)
   - Check for infinite loops in agent logic
   - Review conversation history limits

2. **If legitimate traffic increase**
   - Adjust budget allocation
   - Consider more cost-effective models
   - Implement caching for repeated queries

3. **If abuse detected**
   - Rate limit specific users
   - Review access controls
   - Implement usage quotas per user

### Escalation
- **On-call SRE**: For technical issues
- **Finance/Ops**: For budget approval
- **Product Team**: For feature changes

---

## LLMTokensHigh

### Alert Definition
```yaml
alert: LLMTokensHigh
expr: rate(llm_tokens_total[5m]) > 1000000
for: 10m
severity: info
```

### Severity
**INFO** - Proactive monitoring

### Impact
- Higher than normal token usage
- Increased costs
- May indicate new usage patterns

### Diagnosis

1. **Check token breakdown**
   ```promql
   sum by (token_type) (rate(llm_tokens_total[5m]))
   ```
   - `prompt` tokens - input tokens
   - `completion` tokens - output tokens

2. **Check by model**
   ```promql
   sum by (model) (rate(llm_tokens_total[5m]))
   ```

3. **Identify heavy users or operations**

### Resolution

1. **If prompt tokens high**
   - Review context window management
   - Implement conversation summarization
   - Reduce system prompt size

2. **If completion tokens high**
   - Review max_tokens settings
   - Check for verbose output generation
   - Consider streaming for large outputs

### Escalation
- **Product Team**: For optimization strategies
