# LLM Streaming Alerts Runbook

## Overview

This runbook covers alerts related to LLM streaming performance metrics:
- Time To First Chunk (TTFC)
- Inter-chunk latency
- Streaming duration
- Streaming error rates

## Symptoms

When these alerts fire, you may observe:
- Long wait before first response chunk appears
- Choppy or stuttering streaming responses
- Incomplete streaming responses
- Connection drops during streaming
- High inter-chunk delays

---

## SLAStreamingTTFCBreach

### Alert Definition
```yaml
alert: SLAStreamingTTFCBreach
expr: histogram_quantile(0.95, sum(rate(llm_streaming_ttfc_seconds_bucket[5m])) by (le)) > 2.0
for: 5m
severity: critical
```

### Severity
**CRITICAL** - Response within 5 minutes

### Impact
- Users experience long wait before seeing any response
- Poor perceived performance even if total response time is acceptable
- May cause users to refresh or abandon requests
- SLA violation for streaming response initiation

### Diagnosis

1. **Check TTFC by provider**
   ```promql
   histogram_quantile(0.95, sum by (provider, le) (rate(llm_streaming_ttfc_seconds_bucket[5m])))
   ```

2. **Check TTFC by model**
   ```promql
   histogram_quantile(0.95, sum by (model, le) (rate(llm_streaming_ttfc_seconds_bucket[5m])))
   ```

3. **Compare with baseline**
   - View LLM Streaming dashboard
   - Check historical TTFC trends for anomalies

4. **Check LLM provider status**
   - OpenAI: https://status.openai.com/
   - Anthropic: https://status.anthropic.com/
   - Google AI: https://status.cloud.google.com/

5. **Check for overloaded condition**
   ```promql
   rate(llm_errors_total{error_type="overload"}[5m])
   ```

### Resolution

1. **If provider is slow**
   - Enable fallback model with faster TTFC
   - Route traffic to alternative provider
   - Communicate status to users

2. **If network latency is high**
   - Check network connectivity to provider
   - Verify DNS resolution times
   - Consider regional routing

3. **If prompt processing is slow**
   - Review prompt sizes
   - Check for excessive context
   - Consider prompt compression

4. **Enable streaming fallback**
   ```bash
   kubectl set env deployment/langgraph-agent FF_ENABLE_LLM_FACTORY_STREAMING_FALLBACK=true
   ```

### Escalation
- **On-call SRE**: For infrastructure issues
- **AI/ML Team**: For model configuration

---

## SLAStreamingTTFCAtRisk

### Alert Definition
```yaml
alert: SLAStreamingTTFCAtRisk
expr: histogram_quantile(0.95, sum(rate(llm_streaming_ttfc_seconds_bucket[5m])) by (le)) > 1.0 and <= 2.0
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- TTFC approaching SLA threshold
- Early warning before breach
- Opportunity for proactive mitigation

### Diagnosis

See [SLAStreamingTTFCBreach](#slastreamingttfcbreach) diagnosis steps.

### Resolution

1. **Monitor closely for escalation**
2. **Pre-emptively route to faster providers**
3. **Review recent changes that may have impacted TTFC**

---

## SLAStreamingTTFCByProvider

### Alert Definition
```yaml
alert: SLAStreamingTTFCByProvider
expr: histogram_quantile(0.95, sum(rate(llm_streaming_ttfc_seconds_bucket[5m])) by (le, provider)) > 3.0
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 15 minutes

### Impact
- Specific provider experiencing degraded TTFC
- May indicate provider-specific issue
- Opportunity to failover

### Diagnosis

1. **Identify affected provider**
   ```promql
   histogram_quantile(0.95, sum by (provider, le) (rate(llm_streaming_ttfc_seconds_bucket[5m]))) > 3
   ```

2. **Check provider health**
   - Check provider status page
   - Verify API quotas and rate limits

### Resolution

1. **Failover to alternative provider**
   - Update provider priority configuration
   - Route affected traffic to faster provider

2. **If persistent, contact provider support**

---

## SLAStreamingInterChunkLatencyHigh

### Alert Definition
```yaml
alert: SLAStreamingInterChunkLatencyHigh
expr: histogram_quantile(0.95, sum(rate(llm_streaming_inter_chunk_latency_seconds_bucket[5m])) by (le)) > 0.25
for: 5m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Choppy streaming experience for users
- Text appears in bursts rather than smoothly
- Poor perceived performance
- May indicate throttling or network issues

### Diagnosis

1. **Check inter-chunk latency distribution**
   ```promql
   histogram_quantile(0.50, sum(rate(llm_streaming_inter_chunk_latency_seconds_bucket[5m])) by (le))
   histogram_quantile(0.95, sum(rate(llm_streaming_inter_chunk_latency_seconds_bucket[5m])) by (le))
   histogram_quantile(0.99, sum(rate(llm_streaming_inter_chunk_latency_seconds_bucket[5m])) by (le))
   ```

2. **Check by provider**
   ```promql
   histogram_quantile(0.95, sum by (provider, le) (rate(llm_streaming_inter_chunk_latency_seconds_bucket[5m])))
   ```

3. **Check network metrics**
   - Network latency to provider endpoints
   - Packet loss or retransmission rates

### Resolution

1. **If provider throttling**
   - Check rate limits
   - Reduce concurrent streams if possible
   - Contact provider for quota increase

2. **If network issues**
   - Check network connectivity
   - Review proxy/gateway configuration
   - Consider TCP tuning for streaming

---

## SLAStreamingErrorRateHigh

### Alert Definition
```yaml
alert: SLAStreamingErrorRateHigh
expr: (sum(rate(llm_streaming_duration_seconds_count{status=~"error|timeout"}[5m])) / sum(rate(llm_streaming_duration_seconds_count[5m])) * 100) > 5.0
for: 5m
severity: critical
```

### Severity
**CRITICAL** - Response within 5 minutes

### Impact
- High percentage of streaming responses failing
- Users not receiving complete responses
- Potential data loss mid-stream
- SLA violation

### Diagnosis

1. **Check error breakdown by status**
   ```promql
   sum by (status) (rate(llm_streaming_duration_seconds_count[5m]))
   ```

2. **Check errors by provider/model**
   ```promql
   sum by (provider, model, status) (rate(llm_streaming_duration_seconds_count{status=~"error|timeout"}[5m]))
   ```

3. **Check application logs for error details**
   ```bash
   kubectl logs -l app=langgraph-agent --since=5m | grep -i "streaming.*error"
   ```

### Resolution

1. **If timeout errors**
   - Increase streaming timeout configuration
   - Check for slow providers
   - Review network stability

2. **If connection errors**
   - Check provider connectivity
   - Review retry configuration
   - Verify circuit breaker is not tripped

3. **If provider errors**
   - Check provider status page
   - Enable fallback provider
   - Implement retry with exponential backoff

---

## SLAStreamingDurationHigh

### Alert Definition
```yaml
alert: SLAStreamingDurationHigh
expr: histogram_quantile(0.95, sum(rate(llm_streaming_duration_seconds_bucket[5m])) by (le)) > 60.0
for: 10m
severity: warning
```

### Severity
**WARNING** - Response within 30 minutes

### Impact
- Unusually long streaming sessions
- May indicate stuck connections
- Resource holding issues
- Potential memory leaks

### Diagnosis

1. **Check duration distribution**
   ```promql
   histogram_quantile(0.95, sum(rate(llm_streaming_duration_seconds_bucket[5m])) by (le))
   ```

2. **Check by model (larger models may stream longer)**
   ```promql
   histogram_quantile(0.95, sum by (model, le) (rate(llm_streaming_duration_seconds_bucket[5m])))
   ```

3. **Check chunk counts for long streams**
   ```promql
   rate(llm_streaming_chunks_total[5m])
   ```

### Resolution

1. **If due to large responses**
   - Review max_tokens configuration
   - Implement response length limits
   - Consider streaming chunking strategies

2. **If due to stuck connections**
   - Check connection pool configuration
   - Review timeout settings
   - Monitor for memory leaks

---

## Related Dashboards

- **LLM Streaming Dashboard**: `/d/llm-streaming/llm-streaming`
- **LLM Performance Dashboard**: `/d/llm-performance/llm-performance`
- **Overview Dashboard**: `/d/langgraph-agent-overview/langgraph-agent-overview`

## Related Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `llm_streaming_ttfc_seconds` | Histogram | Time To First Chunk |
| `llm_streaming_inter_chunk_latency_seconds` | Histogram | Latency between chunks |
| `llm_streaming_duration_seconds` | Histogram | Total streaming duration |
| `llm_streaming_chunks_total` | Counter | Total chunks emitted |

## Contact

- **On-call SRE**: For infrastructure issues
- **AI/ML Team**: For model configuration
- **Product Team**: For SLA discussions
