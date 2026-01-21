# Native Tool Alerts Runbook

This runbook covers alerts related to native LLM provider tools (Anthropic web_search, code_execution; Google grounded search).

## Overview

Native tools provide direct access to LLM provider capabilities, offering better integration and potentially lower latency compared to builtin equivalents. The system includes:

- **Fallback Chain**: Automatic fallback from native to builtin tools on failure
- **Circuit Breaker**: Per-provider protection against cascading failures
- **Metrics**: Latency, error rate, and fallback tracking

---

## Platform Limitations

### Vertex AI Anthropic Models

**Critical**: Anthropic code execution (`code_execution_20250825`) is **NOT supported** when using Claude models via Vertex AI. Only web search works.

| Capability | Direct API | Vertex AI | Bedrock |
|------------|:----------:|:---------:|:-------:|
| Web Search | ✅ | ✅ | ✅ |
| Code Execution | ✅ | ❌ | ✅ |

**Impact**:
- Requests for code execution on Vertex AI Anthropic models will automatically fall back to the builtin `execute_python` tool
- The system logs a warning: "Native-only mode but no native tools available, using builtins"
- Users won't see an error, but will use the builtin implementation

**Detection**:
```promql
# High fallback rate specifically for code_execution on Anthropic
sum(rate(native_tool_fallback_count_total{
  tool_name="code_execution",
  from_provider="anthropic"
}[5m])) by (reason)
```

**Resolution**:
1. This is expected behavior - not a bug
2. If code execution is critical, use:
   - Direct Anthropic API
   - AWS Bedrock Anthropic
   - OpenAI with code_interpreter
3. Document this limitation for users selecting Vertex AI Claude models
4. The builtin `execute_python` with sandbox provides equivalent functionality

### Google Native Tools

Google models only support `googleSearch` for web search. Code execution is not available.

**Resolution**:
- Use builtin `execute_python` for code execution on Google models
- This is handled automatically when tool_preference = "auto"

---

## Alerts

### NativeToolCircuitBreakerOpen

**Severity**: Warning
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- Native tools from a specific provider are disabled
- All requests falling back to builtin tools
- Circuit breaker state = 1 (OPEN)

#### Investigation Steps

1. **Check provider status**
   ```bash
   # Check recent errors for the provider
   kubectl logs -l app=mcp-server-langgraph --tail=100 | grep -i "native.*{provider}"
   ```

2. **Review error types**
   ```promql
   # Query for error breakdown
   sum(rate(native_tool_errors_count_total{provider="{provider}"}[5m])) by (error_type)
   ```

3. **Check provider API status**
   - Anthropic: https://status.anthropic.com/
   - Google: https://status.cloud.google.com/

#### Resolution

1. **Wait for automatic recovery**: Circuit breaker has a 60-second reset timeout
2. **Check API keys**: Verify provider credentials are valid
3. **Temporarily disable native tools**:
   ```bash
   export FF_NATIVE_TOOLS_ENABLED=false
   # or
   export FF_ANTHROPIC_NATIVE_WEB_SEARCH_ENABLED=false
   ```

---

### NativeToolCircuitBreakerFlapping

**Severity**: Warning
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- Circuit breaker state changing frequently
- Intermittent native tool availability
- User experience inconsistency

#### Investigation Steps

1. **Check state change rate**
   ```promql
   rate(native_tool_circuit_breaker_state_changes_total{provider="{provider}"}[10m])
   ```

2. **Identify patterns**
   - Time-based issues (rate limiting at peak hours?)
   - Request-volume correlation
   - Network intermittency

#### Resolution

1. **Increase circuit breaker threshold**:
   Adjust `failure_threshold` in `NativeToolCircuitBreaker` (default: 5)

2. **Extend reset timeout**:
   Increase `reset_timeout_seconds` (default: 60)

3. **Consider disabling native tools for this provider** until stability improves

---

### NativeToolFallbackRateHigh

**Severity**: Warning
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- More than 30% of native tool calls falling back to builtins
- Inconsistent performance characteristics
- Mixed latency distribution

#### Investigation Steps

1. **Identify affected tools**
   ```promql
   sum(rate(native_tool_fallback_count_total[5m])) by (tool_name, reason)
   ```

2. **Check fallback reasons**
   - `timeout`: Provider too slow
   - `rate_limit`: API quota exceeded
   - `auth_error`: Credential issues
   - `network_error`: Connectivity problems

#### Resolution

1. **For timeouts**: Increase timeout thresholds or prefer builtins
2. **For rate limits**: Reduce native tool usage or upgrade API tier
3. **For auth errors**: Rotate API credentials
4. **For network errors**: Check network configuration

---

### NativeToolFallbackSpiked

**Severity**: Warning
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- Sudden increase in fallback events (50+ in 5 minutes)
- Usually indicates provider outage

#### Investigation Steps

1. **Check provider status pages**
2. **Review error logs**:
   ```bash
   kubectl logs -l app=mcp-server-langgraph --since=5m | grep -i "native.*failed"
   ```

#### Resolution

1. **Wait for provider recovery**
2. **Circuit breaker will protect against cascading failures**
3. **If persistent, disable native tools via feature flags**

---

### NativeToolErrorRateHigh

**Severity**: Warning
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- High error rate for specific provider/error type combination
- Error rate > 0.5/second for 5+ minutes

#### Investigation Steps

1. **Identify error type**:
   ```promql
   sum(rate(native_tool_errors_count_total[5m])) by (provider, error_type)
   ```

2. **Check provider-specific logs**

#### Resolution by Error Type

| Error Type | Resolution |
|------------|------------|
| `timeout` | Increase timeouts or prefer builtins |
| `rate_limit` | Reduce usage or upgrade API tier |
| `auth_error` | Rotate credentials |
| `network_error` | Check connectivity |
| `quota_exceeded` | Wait for quota reset or upgrade |

---

### NativeToolTimeoutRateHigh

**Severity**: Warning
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- Native tool timeouts occurring at > 0.2/second
- Slow user experiences when native tools are attempted

#### Resolution

1. **Increase timeout thresholds**:
   Configure longer timeouts in provider settings

2. **Prefer builtins for this tool**:
   ```python
   # Set tool preference to "builtin" for affected tools
   tool_preference = "builtin"
   ```

3. **Check provider latency**:
   ```promql
   histogram_quantile(0.99, sum(rate(native_tool_execution_duration_bucket{provider="{provider}"}[5m])) by (le))
   ```

---

### NativeToolRateLimitHit

**Severity**: Warning
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- Rate limit errors accumulating (10+ in 5 minutes)
- Provider rejecting requests with 429 status

#### Resolution

1. **Reduce native tool usage**:
   - Implement request batching
   - Add caching where applicable
   - Prefer builtins for high-volume operations

2. **Upgrade API tier**:
   Contact provider for higher rate limits

3. **Distribute load**:
   Use multiple API keys with load balancing

---

### NativeToolLatencyHigh

**Severity**: Warning
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- p95 latency > 5 seconds
- Slow user experiences

#### Resolution

1. **Check provider performance**:
   Compare with provider's published latency SLAs

2. **Prefer builtins for latency-sensitive operations**:
   ```python
   tool_preference = "builtin"
   ```

3. **Consider regional routing**:
   Use provider regions closer to your infrastructure

---

### NativeToolSlowerThanBuiltin

**Severity**: Info
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- Native tool is 2x+ slower than builtin equivalent
- May indicate suboptimal tool preference

#### Resolution

This is informational. Consider:
1. Reviewing tool preference settings
2. Whether native tool benefits outweigh latency cost
3. Updating auto-selection logic

---

### NoNativeToolUsage

**Severity**: Info
**Dashboard**: [Native Tool Metrics](../grafana/dashboards/Application/native-tool-metrics.json)

#### Symptoms
- No native tools used despite builtin usage
- May indicate configuration issues

#### Investigation Steps

1. **Check feature flags**:
   ```bash
   # Verify native tools are enabled
   echo $FF_NATIVE_TOOLS_ENABLED
   echo $FF_ANTHROPIC_NATIVE_WEB_SEARCH_ENABLED
   ```

2. **Check circuit breaker state**:
   ```promql
   native_tool_circuit_breaker_state
   ```

3. **Review model capabilities**:
   Ensure current model supports native tools

---

## Feature Flags

| Flag | Description |
|------|-------------|
| `FF_NATIVE_TOOLS_ENABLED` | Master switch for all native tools |
| `FF_ANTHROPIC_NATIVE_WEB_SEARCH_ENABLED` | Enable Anthropic web_search_20250305 |
| `FF_GOOGLE_NATIVE_SEARCH_ENABLED` | Enable Google googleSearch |
| `FF_ANTHROPIC_NATIVE_CODE_EXECUTION_ENABLED` | Enable Anthropic code_execution_20250825 |
| `FF_OPENAI_NATIVE_WEB_SEARCH_ENABLED` | Enable OpenAI web_search via Responses API* |
| `FF_OPENAI_NATIVE_CODE_INTERPRETER_ENABLED` | Enable OpenAI code_interpreter via Responses API* |
| `FF_USE_RESPONSES_API_FOR_OPENAI` | Enable OpenAI Responses API (required for OpenAI native tools) |

\* OpenAI native tools require `FF_USE_RESPONSES_API_FOR_OPENAI=true`

---

## Metrics Reference

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `native_tool_selection_count_total` | Counter | tool_name, provider, preference | Native tool selections |
| `tool_source_selection_count_total` | Counter | tool_name, source, model | Tool selections by source |
| `native_tool_execution_duration` | Histogram | tool_name, provider, success | Native tool latency |
| `native_tool_errors_count_total` | Counter | tool_name, provider, error_type | Native tool errors |
| `native_tool_fallback_count_total` | Counter | tool_name, from_provider, to_source, reason | Fallback events |
| `native_tool_circuit_breaker_state` | Gauge | provider | Circuit breaker state |
| `native_tool_circuit_breaker_state_changes_total` | Counter | provider, from_state, to_state | State changes |
| `builtin_tool_execution_duration` | Histogram | tool_name | Builtin tool latency |

---

## Related Documentation

- [ADR-0102: Native LLM Provider Tools Integration](../../adr/adr-0102-native-llm-provider-tools.md)
- [Native Tools User Guide](../../docs/guides/native-tools.mdx)
- [Native Tool Metrics Dashboard](../grafana/dashboards/Application/native-tool-metrics.json)
- [Resilience Patterns Runbook](./resilience-alerts.md)
