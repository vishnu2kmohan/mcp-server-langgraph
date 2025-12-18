"""
Backend implementations for observability query clients.

Each backend module provides implementations of the abstract interfaces
for a specific observability platform.

Implemented backends:
- tempo: Grafana Tempo (TraceQL) - Tracing
- loki: Grafana Loki (LogQL) - Logging
- prometheus: Prometheus/Mimir (PromQL) - Metrics
- grafana: Grafana Alerting (Unified Alerting) - Alerting
- cloudtrace: GCP Cloud Trace - Tracing
- cloudlogging: GCP Cloud Logging - Logging
- cloudmonitoring: GCP Cloud Monitoring - Metrics
- stub: In-memory stub for testing

Planned backends (not yet implemented):
- jaeger: Jaeger (Jaeger API)
- xray: AWS X-Ray
- appinsights: Azure Application Insights
- elasticsearch: Elasticsearch
- cloudwatch: AWS CloudWatch (Logs, Metrics, and Alarms)
- azuremonitor: Azure Monitor Alerts
- datadog: Datadog
"""
