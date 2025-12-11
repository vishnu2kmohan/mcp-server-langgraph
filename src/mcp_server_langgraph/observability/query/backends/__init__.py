"""
Backend implementations for observability query clients.

Each backend module provides implementations of the abstract interfaces
for a specific observability platform.

Implemented backends:
- tempo: Grafana Tempo (TraceQL)
- loki: Grafana Loki (LogQL)
- prometheus: Prometheus/Mimir (PromQL)
- stub: In-memory stub for testing

Planned backends (not yet implemented):
- jaeger: Jaeger (Jaeger API)
- xray: AWS X-Ray
- cloudtrace: GCP Cloud Trace
- appinsights: Azure Application Insights
- elasticsearch: Elasticsearch
- cloudwatch: AWS CloudWatch (Logs and Metrics)
- cloudlogging: GCP Cloud Logging
- cloudmonitoring: GCP Cloud Monitoring
- datadog: Datadog
"""
