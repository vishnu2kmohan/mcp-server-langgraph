# GCP Monitoring Configuration

This directory contains Google Cloud Platform (GCP) monitoring configuration for the MCP Server LangGraph project.

## Contents

### Monitoring Setup

- **`setup-monitoring.sh`** - Automated script to set up GCP monitoring infrastructure
  - Creates monitoring workspace
  - Configures Cloud Monitoring dashboards
  - Sets up alerting policies
  - Configures log-based metrics

### SLI/SLO Configuration

- **`sli-slo-config.yaml`** - Service Level Indicator and Service Level Objective definitions
  - API availability SLIs
  - Latency percentile SLOs
  - Error rate thresholds
  - Custom business metrics

### Dashboards

- **`dashboards/`** - Pre-configured Cloud Monitoring dashboards
  - System health overview
  - API performance metrics
  - Resource utilization
  - Error tracking

## Usage

### Initial Setup

```bash
# Run the setup script to configure GCP monitoring
./setup-monitoring.sh

# This will:
# 1. Create a monitoring workspace
# 2. Deploy dashboards
# 3. Configure SLIs/SLOs
# 4. Set up alerting policies
```

### Prerequisites

- GCP project with Cloud Monitoring API enabled
- Service account with monitoring.admin role
- gcloud CLI configured and authenticated

### Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export MONITORING_WORKSPACE_NAME="mcp-server-monitoring"
```

### Viewing Metrics

1. **Cloud Console**: Navigate to Cloud Monitoring > Dashboards
2. **CLI**: Use `gcloud monitoring` commands
3. **API**: Query via Cloud Monitoring API

### Alerting

Alerts are configured based on SLO violations:
- API error rate > 1% for 5 minutes
- P95 latency > 500ms for 10 minutes
- Service availability < 99.9% over 30 minutes

Notifications are sent to configured channels (email, PagerDuty, Slack).

## Integration with OpenTelemetry

This monitoring setup integrates with the OpenTelemetry collector configuration in `../otel-collector/`. Metrics are exported to both Cloud Monitoring and the OTEL collector.

## Related Documentation

- [Deployment: GCP Configuration](/docs/deployment/gcp-configuration.mdx)
- [Monitoring Guide](/docs/guides/observability.mdx)
- [Prometheus Configuration](../prometheus/)
- [Grafana Dashboards](../grafana/dashboards/)

## Maintenance

### Updating Dashboards

1. Export dashboard from Cloud Console
2. Save JSON to `dashboards/`
3. Update dashboard IDs in `setup-monitoring.sh`
4. Test deployment in staging

### Modifying SLIs/SLOs

1. Edit `sli-slo-config.yaml`
2. Run `./setup-monitoring.sh --update-slos`
3. Verify in Cloud Console

## Troubleshooting

### Dashboard Not Showing Data

```bash
# Check if metrics are being exported
gcloud monitoring time-series list \
  --filter='metric.type="custom.googleapis.com/mcp-server/*"' \
  --limit=10

# Verify OTEL collector is running
kubectl get pods -n observability | grep otel-collector
```

### SLO Alerts Not Firing

```bash
# Check alerting policy status
gcloud alpha monitoring policies list

# View recent alert incidents
gcloud alpha monitoring incidents list
```

## Cost Optimization

- Metrics retention: 30 days (configurable)
- Log ingestion: Sampled at 10% for high-volume endpoints
- Dashboard refresh: 60 seconds (adjustable)

Estimated cost: $50-100/month depending on traffic volume.
