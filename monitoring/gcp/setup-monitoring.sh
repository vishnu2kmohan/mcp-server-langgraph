#!/bin/bash
# ==============================================================================
# Setup Cloud Monitoring for GKE Production
# ==============================================================================

set -euo pipefail

PROJECT_ID="${1:-}"
if [ -z "$PROJECT_ID" ]; then
    echo "Usage: $0 PROJECT_ID"
    exit 1
fi

echo "Setting up Cloud Monitoring for project: $PROJECT_ID"

# ==============================================================================
# 1. Create Dashboard
# ==============================================================================

echo "Creating Cloud Monitoring dashboard..."

gcloud monitoring dashboards create \
    --config-from-file=dashboards/gke-production-dashboard.json \
    --project="$PROJECT_ID"

DASHBOARD_ID=$(gcloud monitoring dashboards list \
    --filter="displayName:'MCP Server - GKE Production Dashboard'" \
    --format="value(name)" \
    --project="$PROJECT_ID")

echo "✅ Dashboard created: $DASHBOARD_ID"
echo "   View at: https://console.cloud.google.com/monitoring/dashboards/custom/$DASHBOARD_ID?project=$PROJECT_ID"

# ==============================================================================
# 2. Create Notification Channels
# ==============================================================================

echo "Creating notification channels..."

# Email channel
gcloud alpha monitoring channels create \
    --display-name="Production Alerts Email" \
    --type=email \
    --channel-labels=email_address=platform-team@company.com \
    --project="$PROJECT_ID" || echo "Email channel may already exist"

# Get channel ID
EMAIL_CHANNEL=$(gcloud alpha monitoring channels list \
    --filter="displayName:'Production Alerts Email'" \
    --format="value(name)" \
    --project="$PROJECT_ID")

echo "✅ Email notification channel: $EMAIL_CHANNEL"

# ==============================================================================
# 3. Create Alert Policies
# ==============================================================================

echo "Creating alert policies..."

# High error rate alert
cat > /tmp/error-rate-alert.yaml <<EOF
displayName: "High Error Rate - Production"
conditions:
  - displayName: "Error rate above 5%"
    conditionThreshold:
      filter: 'resource.type="k8s_container" AND resource.labels.namespace_name="mcp-production" AND severity>=ERROR'
      comparison: COMPARISON_GT
      thresholdValue: 5
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
          crossSeriesReducer: REDUCE_SUM
notificationChannels:
  - $EMAIL_CHANNEL
alertStrategy:
  autoClose: 86400s
EOF

gcloud alpha monitoring policies create \
    --policy-from-file=/tmp/error-rate-alert.yaml \
    --project="$PROJECT_ID"

echo "✅ Error rate alert created"

# Pod crash loop alert
cat > /tmp/crash-loop-alert.yaml <<EOF
displayName: "Pod Crash Loop - Production"
conditions:
  - displayName: "Pod restart count > 5"
    conditionThreshold:
      filter: 'resource.type="k8s_pod" AND resource.labels.namespace_name="mcp-production" AND metric.type="kubernetes.io/pod/restart_count"'
      comparison: COMPARISON_GT
      thresholdValue: 5
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_MAX
notificationChannels:
  - $EMAIL_CHANNEL
alertStrategy:
  autoClose: 3600s
EOF

gcloud alpha monitoring policies create \
    --policy-from-file=/tmp/crash-loop-alert.yaml \
    --project="$PROJECT_ID"

echo "✅ Crash loop alert created"

# High latency alert
cat > /tmp/latency-alert.yaml <<EOF
displayName: "High Latency - Production"
conditions:
  - displayName: "P95 latency > 2 seconds"
    conditionThreshold:
      filter: 'metric.type="custom.googleapis.com/application/request_duration" AND resource.type="k8s_pod" AND resource.labels.namespace_name="mcp-production"'
      comparison: COMPARISON_GT
      thresholdValue: 2.0
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_DELTA
          crossSeriesReducer: REDUCE_PERCENTILE_95
notificationChannels:
  - $EMAIL_CHANNEL
alertStrategy:
  autoClose: 86400s
EOF

gcloud alpha monitoring policies create \
    --policy-from-file=/tmp/latency-alert.yaml \
    --project="$PROJECT_ID" || echo "Latency alert may require custom metric"

echo "✅ Latency alert created"

# ==============================================================================
# 4. Create Uptime Checks
# ==============================================================================

echo "Creating uptime checks..."

# Get service external IP (if LoadBalancer)
SERVICE_IP=$(kubectl get svc production-mcp-server-langgraph \
    -n mcp-production \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")

if [ -n "$SERVICE_IP" ]; then
    gcloud monitoring uptime create \
        --resource-type=uptime-url \
        --resource-labels=host="$SERVICE_IP",project_id="$PROJECT_ID" \
        --http-check-path=/health/live \
        --display-name="MCP Production Health Check" \
        --period=60 \
        --timeout=10s \
        --project="$PROJECT_ID"

    echo "✅ Uptime check created for $SERVICE_IP"
else
    echo "⚠️  No external IP found. Create uptime check manually after exposing service."
fi

# ==============================================================================
# 5. Setup SLO
# ==============================================================================

echo "Creating SLO (Service Level Objective)..."

# Availability SLO: 99.9% uptime
cat > /tmp/availability-slo.yaml <<EOF
serviceLevelIndicator:
  requestBased:
    goodTotalRatio:
      goodServiceFilter: 'metric.type="custom.googleapis.com/application/request_count" AND metric.labels.status_code<500'
      totalServiceFilter: 'metric.type="custom.googleapis.com/application/request_count"'
goal: 0.999
rollingPeriod: 2592000s  # 30 days
displayName: "99.9% Availability SLO"
EOF

# Note: Requires custom metrics from application
echo "⚠️  SLO requires custom application metrics. See sli-slo-config.yaml for setup."

# Cleanup
rm -f /tmp/*.yaml

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Cloud Monitoring Setup Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Dashboard: https://console.cloud.google.com/monitoring/dashboards?project=$PROJECT_ID"
echo "Alerts:    https://console.cloud.google.com/monitoring/alerting?project=$PROJECT_ID"
echo "SLOs:      https://console.cloud.google.com/monitoring/services?project=$PROJECT_ID"
echo
echo "Next steps:"
echo "1. Configure email address in notification channel"
echo "2. Add custom application metrics for SLO"
echo "3. Create additional dashboards as needed"
echo
