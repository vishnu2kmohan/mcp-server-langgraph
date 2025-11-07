# OpenTelemetry Collector Configuration

This directory contains OpenTelemetry Collector configuration files for various observability backends. The OTEL collector provides a vendor-agnostic way to receive, process, and export telemetry data (metrics, traces, and logs).

## Contents

### Collector Configurations

Each YAML file configures the OTEL collector to export telemetry data to a specific backend:

- **`otel-collector.yaml`** - Base configuration with common pipelines
- **`gcp-cloud-logging.yaml`** - Export to Google Cloud Logging & Monitoring
- **`aws-cloudwatch.yaml`** - Export to AWS CloudWatch
- **`azure-monitor.yaml`** - Export to Azure Monitor
- **`datadog.yaml`** - Export to Datadog
- **`elasticsearch.yaml`** - Export to Elasticsearch/OpenSearch
- **`splunk.yaml`** - Export to Splunk

## Architecture

```
┌─────────────────┐
│  MCP Server     │
│  (Instrumented) │
└────────┬────────┘
         │ OTLP (gRPC/HTTP)
         ▼
┌─────────────────┐
│ OTEL Collector  │
│  - Receivers    │
│  - Processors   │
│  - Exporters    │
└────────┬────────┘
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
     ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐
     │ GCP │   │ AWS │   │Splunk│  │ ... │
     └─────┘   └─────┘   └─────┘   └─────┘
```

## Usage

### Selecting a Configuration

Choose the configuration file that matches your observability backend:

```bash
# For GCP deployment
kubectl apply -f otel-collector.yaml
kubectl apply -f gcp-cloud-logging.yaml

# For AWS deployment
kubectl apply -f otel-collector.yaml
kubectl apply -f aws-cloudwatch.yaml

# For multi-cloud/hybrid
kubectl apply -f otel-collector.yaml
kubectl apply -f gcp-cloud-logging.yaml
kubectl apply -f aws-cloudwatch.yaml
```

### Deployment Options

#### Kubernetes (Recommended)

```bash
# Deploy as DaemonSet (one per node)
kubectl apply -f otel-collector.yaml

# Deploy as Deployment (centralized)
kubectl apply -f deployments/base/otel-deployment.yaml
```

#### Docker Compose

```yaml
# docker-compose.yml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/otel-collector.yaml"]
    volumes:
      - ./monitoring/otel-collector/otel-collector.yaml:/etc/otel-collector.yaml
    ports:
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
      - "8888:8888"  # Prometheus metrics
      - "13133:13133" # Health check
```

#### Standalone Binary

```bash
# Download OTEL collector
wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.91.0/otelcol-contrib_0.91.0_linux_amd64.tar.gz

# Extract and run
tar -xvf otelcol-contrib_0.91.0_linux_amd64.tar.gz
./otelcol-contrib --config=otel-collector.yaml
```

## Configuration Details

### Base Configuration (`otel-collector.yaml`)

**Receivers:**
- OTLP (gRPC: 4317, HTTP: 4318)
- Prometheus (scrape endpoint: 8888)
- Jaeger (legacy support)

**Processors:**
- Batch processor (optimize export performance)
- Resource detection (auto-detect cloud metadata)
- Memory limiter (prevent OOM)
- Sampling (for high-volume traces)

**Exporters:**
- Logging (stdout for debugging)
- OTLP (forward to other collectors)
- Prometheus (expose metrics)

### Cloud-Specific Configurations

Each cloud provider config includes:
- Authentication setup
- Resource attributes mapping
- Retry and queue configuration
- Compression settings

**Example: GCP Cloud Logging**
```yaml
exporters:
  googlecloud:
    project: ${GCP_PROJECT_ID}
    compression: gzip
    retry_on_failure:
      enabled: true
    sending_queue:
      enabled: true
      num_consumers: 10
```

## Application Configuration

Configure your MCP Server to send telemetry to the OTEL collector:

```python
# src/mcp_server_langgraph/observability/telemetry.py
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider

# Export to OTEL collector
otlp_exporter = OTLPSpanExporter(
    endpoint="http://otel-collector:4317",
    insecure=True  # Use TLS in production
)

tracer_provider = TracerProvider()
tracer_provider.add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)
```

### Environment Variables

```bash
# OTEL collector endpoint
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"

# Optional: specific protocol
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"  # or "http/protobuf"

# Service name and version
export OTEL_SERVICE_NAME="mcp-server-langgraph"
export OTEL_SERVICE_VERSION="2.8.0"
```

## Monitoring the Collector

### Health Checks

```bash
# Basic health check
curl http://localhost:13133/

# Detailed metrics
curl http://localhost:8888/metrics

# Check OTLP receiver
grpcurl -plaintext localhost:4317 list
```

### Collector Metrics

Key metrics to monitor:
- `otelcol_receiver_accepted_spans` - Incoming spans
- `otelcol_exporter_sent_spans` - Exported spans
- `otelcol_processor_batch_batch_send_size` - Batch sizes
- `otelcol_exporter_send_failed_spans` - Export failures

### Logging

```bash
# View collector logs (Kubernetes)
kubectl logs -f deployment/otel-collector

# View with follow (Docker)
docker logs -f otel-collector

# Check for errors
kubectl logs deployment/otel-collector | grep -i error
```

## Troubleshooting

### Data Not Appearing in Backend

1. **Check collector health:**
   ```bash
   curl http://localhost:13133/
   ```

2. **Verify receiver is accepting data:**
   ```bash
   curl http://localhost:8888/metrics | grep receiver_accepted
   ```

3. **Check exporter configuration:**
   - Verify credentials are correct
   - Check network connectivity to backend
   - Review exporter logs for errors

### High Memory Usage

Adjust memory limiter in configuration:

```yaml
processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512  # Adjust based on available memory
    spike_limit_mib: 128
```

### Dropped Data

Increase batch size or queue size:

```yaml
processors:
  batch:
    send_batch_size: 1024
    timeout: 10s

exporters:
  googlecloud:
    sending_queue:
      queue_size: 5000
```

## Performance Tuning

### High Throughput

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        max_concurrent_streams: 100
      http:
        max_request_body_size: 4194304  # 4MB

processors:
  batch:
    send_batch_size: 2048
    send_batch_max_size: 4096
```

### Resource Limits (Kubernetes)

```yaml
resources:
  limits:
    cpu: "2"
    memory: 2Gi
  requests:
    cpu: "1"
    memory: 1Gi
```

## Security

### TLS Configuration

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        tls:
          cert_file: /certs/server.crt
          key_file: /certs/server.key
```

### Authentication

For cloud exporters, use:
- **GCP**: Workload Identity or service account key
- **AWS**: IAM roles or access keys
- **Azure**: Managed Identity or service principal

## Multi-Backend Setup

Export to multiple backends simultaneously:

```yaml
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, memory_limiter]
      exporters: [googlecloud, datadog, logging]

    metrics:
      receivers: [otlp, prometheus]
      processors: [batch]
      exporters: [googlecloud, prometheus]
```

## Related Documentation

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OTEL Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [Observability Guide](/docs/guides/observability.mdx)
- [GCP Monitoring Setup](../gcp/README.md)
- [Prometheus Configuration](../prometheus/)

## Maintenance

### Updating Collector Version

```bash
# Update image version in deployment
kubectl set image deployment/otel-collector \
  otel-collector=otel/opentelemetry-collector-contrib:0.92.0

# Verify rollout
kubectl rollout status deployment/otel-collector
```

### Configuration Changes

```bash
# Update ConfigMap
kubectl create configmap otel-collector-config \
  --from-file=otel-collector.yaml \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart collector
kubectl rollout restart deployment/otel-collector
```

## Cost Considerations

OTEL collector itself is free and open-source. Costs are associated with:
- Cloud provider ingestion fees
- Storage costs for traces/logs/metrics
- Network egress (multi-region/cloud)

**Optimization tips:**
- Use sampling for traces (e.g., 10% sampling in production)
- Set appropriate retention policies
- Use batch processing to reduce API calls
- Compress data in transit
