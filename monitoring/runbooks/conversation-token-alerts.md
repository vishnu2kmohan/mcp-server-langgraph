# Conversation Token Usage Alerts Runbook

## Overview

This runbook covers alerts related to conversation token usage, message counts, and role distribution. These metrics are critical for monitoring context window utilization and ensuring optimal LLM performance.

**Dashboard**: [Conversation Token Usage](https://grafana/d/conversation-token-usage)

**Related ADRs**:
- Phase 4.1 Audit: Full Conversation in LangGraph State
- ADR-0094: KB Focus Mode

## Symptoms

When these alerts fire, you may observe:
- Conversations approaching context window limits
- Higher than expected token consumption
- Unusual message role distribution
- Context truncation issues
- Increased LLM costs

---

## ConversationTokenUsageHigh

### Alert Definition
```yaml
alert: ConversationTokenUsageHigh
expr: histogram_quantile(0.95, sum(rate(chat_conversation_token_estimate_bucket[5m])) by (le)) > 100000
for: 10m
severity: warning
```

### Severity
**WARNING** - Response within 1 hour

### Impact
- Context window approaching limits
- Potential for truncation in future messages
- Increased latency due to large context processing
- Higher LLM costs

### Diagnosis

1. **Check current token distribution**
   ```promql
   histogram_quantile(0.95, sum(rate(chat_conversation_token_estimate_bucket[5m])) by (le))
   ```

2. **Identify high-token conversations**
   ```promql
   topk(10, chat_conversation_token_estimate_sum / chat_conversation_token_estimate_count)
   ```

3. **Check message count correlation**
   ```promql
   histogram_quantile(0.95, sum(rate(chat_conversation_message_count_bucket[5m])) by (le))
   ```

4. **Review role distribution**
   ```promql
   sum(rate(chat_conversation_messages_by_role_total[5m])) by (role)
   ```

### Resolution

1. **Enable conversation compaction**
   ```bash
   # Check compaction settings
   kubectl get configmap langgraph-agent-config -o yaml | grep -i compaction

   # Enable if disabled
   kubectl set env deployment/langgraph-agent ENABLE_CONVERSATION_COMPACTION=true
   ```

2. **Review system prompt sizes**
   - Check dynamic context injection volume
   - Review STUDIO.md loading configuration
   - Audit KB focus mode settings

3. **Implement sliding window**
   ```bash
   # Set maximum conversation history
   kubectl set env deployment/langgraph-agent MAX_CONVERSATION_MESSAGES=50
   ```

4. **Monitor after changes**
   - Watch token estimate trend for 30 minutes
   - Verify no user impact from truncation

### Escalation
- **AI/ML Team**: For prompt optimization
- **Platform Team**: For infrastructure scaling

---

## ConversationTokenUsageCritical

### Alert Definition
```yaml
alert: ConversationTokenUsageCritical
expr: histogram_quantile(0.95, sum(rate(chat_conversation_token_estimate_bucket[5m])) by (le)) > 150000
for: 5m
severity: critical
```

### Severity
**CRITICAL** - Immediate response required

### Impact
- Conversations may exceed model context limits
- Truncation causing loss of context
- LLM errors or degraded responses
- Poor user experience

### Diagnosis

1. **Confirm alert is not a spike**
   ```promql
   histogram_quantile(0.95, sum(rate(chat_conversation_token_estimate_bucket[30m])) by (le))
   ```

2. **Check for stuck conversations**
   - Look for sessions with very high message counts
   - Check for automation patterns

3. **Review recent deployments**
   - System prompt changes
   - Context loading configuration changes

### Resolution

1. **Immediate: Enable aggressive compaction**
   ```bash
   kubectl set env deployment/langgraph-agent \
     ENABLE_CONVERSATION_COMPACTION=true \
     COMPACTION_THRESHOLD_TOKENS=80000 \
     COMPACTION_STRATEGY=summarize
   ```

2. **Force session resets for affected users**
   ```bash
   # Identify affected sessions (via logs or metrics)
   # Consider notifying users before reset
   ```

3. **Reduce system prompt size temporarily**
   ```bash
   kubectl set env deployment/langgraph-agent \
     FF_ENABLE_KB_FOCUS=false \
     FF_ENABLE_PROGRESSIVE_CONTEXT_DISCOVERY=false
   ```

4. **Enable model with larger context window**
   ```bash
   # If available, switch to model with 200K+ context
   kubectl set env deployment/langgraph-agent MODEL_NAME=claude-3-5-sonnet-20241022
   ```

### Escalation
- **On-call SRE**: Immediate
- **AI/ML Team**: For prompt optimization
- **Product Team**: For user communication if widespread

---

## ConversationMessageCountSpike

### Alert Definition
```yaml
alert: ConversationMessageCountSpike
expr: histogram_quantile(0.95, sum(rate(chat_conversation_message_count_bucket[5m])) by (le)) > 50
for: 15m
severity: warning
```

### Severity
**WARNING** - Response within 2 hours

### Impact
- Unusual usage patterns
- Potential automation or abuse
- Context window pressure

### Diagnosis

1. **Check if spike is organic**
   ```promql
   # Compare current vs historical
   histogram_quantile(0.95, sum(rate(chat_conversation_message_count_bucket[1h])) by (le))
   histogram_quantile(0.95, sum(rate(chat_conversation_message_count_bucket[1h] offset 1d)) by (le))
   ```

2. **Look for automation patterns**
   - Consistent inter-message timing
   - Repeated similar messages
   - Unusual session durations

3. **Check user distribution**
   - Is spike from single user or widespread?

### Resolution

1. **If automation/abuse detected**
   ```bash
   # Review rate limiting configuration
   kubectl get configmap langgraph-agent-config -o yaml | grep -i rate

   # Enable stricter limits
   kubectl set env deployment/langgraph-agent \
     MAX_MESSAGES_PER_MINUTE=30 \
     MAX_MESSAGES_PER_SESSION=100
   ```

2. **If organic high usage**
   - Consider this healthy engagement
   - Ensure compaction is working
   - Monitor token usage correlation

### Escalation
- **Security Team**: If abuse suspected
- **Product Team**: For UX improvements if organic

---

## ConversationSystemMessageRatioHigh

### Alert Definition
```yaml
alert: ConversationSystemMessageRatioHigh
expr: (sum(rate(chat_conversation_messages_by_role_total{role="system"}[15m])) / sum(rate(chat_conversation_messages_by_role_total[15m]))) > 0.25
for: 15m
severity: warning
```

### Severity
**WARNING** - Response within 2 hours

### Impact
- Inefficient token usage
- Potential misconfiguration
- Reduced conversation capacity

### Diagnosis

1. **Check system message rate over time**
   ```promql
   sum(rate(chat_conversation_messages_by_role_total{role="system"}[1h])) /
   sum(rate(chat_conversation_messages_by_role_total[1h]))
   ```

2. **Review dynamic context configuration**
   - Check KB focus mode settings
   - Review STUDIO.md injection
   - Audit progressive context loading

3. **Compare to baseline**
   - Normal system message ratio should be 5-15%

### Resolution

1. **Review dynamic context settings**
   ```bash
   kubectl get configmap langgraph-agent-config -o yaml | grep -i context
   ```

2. **Consolidate system prompts**
   - Merge multiple system messages if possible
   - Use tool definitions instead of system instructions

3. **Audit prompt templates**
   - Check for redundant system instructions
   - Review per-request system message injection

### Escalation
- **AI/ML Team**: For prompt architecture review

---

## ConversationRoleImbalance

### Alert Definition
```yaml
alert: ConversationRoleImbalance
expr: (sum(rate(chat_conversation_messages_by_role_total{role="user"}[15m])) / sum(rate(chat_conversation_messages_by_role_total{role="assistant"}[15m]))) > 3
for: 15m
severity: info
```

### Severity
**INFO** - Monitor, no immediate action required

### Impact
- Unusual conversation flow
- Potential incomplete responses
- User experience concerns

### Diagnosis

1. **Check if temporary spike**
   - May be caused by batch uploads or multi-message inputs

2. **Review assistant response patterns**
   - Are responses being generated?
   - Check for LLM errors

3. **User behavior analysis**
   - Users sending corrections before response
   - Multi-part messages

### Resolution

Usually no action needed. If persistent:

1. **Check LLM health**
   - Verify assistant responses are being generated
   - Review error rates

2. **Consider UX improvements**
   - Message queuing for rapid input
   - Visual feedback during response generation

---

## ConversationNoActivity

### Alert Definition
```yaml
alert: ConversationNoActivity
expr: sum(increase(chat_conversation_message_count_count[15m])) == 0
for: 15m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Potential service outage
- Users unable to chat
- Revenue impact

### Diagnosis

1. **Check service health**
   ```bash
   kubectl get pods -l app=langgraph-agent
   kubectl logs -l app=langgraph-agent --tail=100
   ```

2. **Check upstream dependencies**
   ```promql
   up{job="langgraph-agent"}
   ```

3. **Verify LLM connectivity**
   ```promql
   rate(llm_requests_total[5m])
   ```

4. **Check authentication**
   ```promql
   rate(http_requests_total{path=~"/api/v1/chat.*", status="401"}[5m])
   ```

### Resolution

1. **If pods not running**
   ```bash
   kubectl rollout restart deployment/langgraph-agent
   ```

2. **If LLM provider issue**
   - Check provider status page
   - Enable fallback model

3. **If authentication issue**
   - Check Keycloak connectivity
   - Verify JWT configuration

4. **If low traffic period**
   - Verify against expected traffic patterns
   - May be normal during off-hours

### Escalation
- **On-call SRE**: For infrastructure issues
- **Platform Team**: For service health

---

## Metrics Reference

| Metric | Type | Description |
|--------|------|-------------|
| `chat_conversation_message_count` | Histogram | Messages per conversation |
| `chat_conversation_token_estimate` | Histogram | Estimated tokens per conversation |
| `chat_conversation_messages_by_role_total` | Counter | Messages by role (user/assistant/system) |

## Related Dashboards

- [Conversation Token Usage](https://grafana/d/conversation-token-usage)
- [LLM Performance](https://grafana/d/llm-performance)
- [LLM Streaming](https://grafana/d/llm-streaming)

## Contact

- **Platform Team**: #platform-oncall
- **AI/ML Team**: #ai-ml-team
- **SRE**: #sre-oncall
