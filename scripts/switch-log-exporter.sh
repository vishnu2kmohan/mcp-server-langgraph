#!/bin/bash
# Switch OTLP Collector Configuration
#
# Usage: ./scripts/switch-log-exporter.sh <platform>
# Platforms: base, aws, gcp, azure, elasticsearch, datadog, splunk

set -e

PLATFORM="${1:-base}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COLLECTOR_DIR="$PROJECT_ROOT/monitoring/otel-collector"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.yml"

# Validate platform
VALID_PLATFORMS=("base" "aws" "gcp" "azure" "elasticsearch" "datadog" "splunk")
if [[ ! " ${VALID_PLATFORMS[*]} " =~ \ ${PLATFORM}\  ]]; then
    echo "❌ Error: Invalid platform '$PLATFORM'"
    echo ""
    echo "Usage: $0 <platform>"
    echo ""
    echo "Valid platforms:"
    echo "  base          - Base OTLP collector (Jaeger + Prometheus + File)"
    echo "  aws           - AWS CloudWatch Logs + Metrics (EMF) + X-Ray"
    echo "  gcp           - GCP Cloud Logging + Monitoring + Trace"
    echo "  azure         - Azure Application Insights"
    echo "  elasticsearch - Elasticsearch/ELK Stack"
    echo "  datadog       - Datadog (Logs + Metrics + APM)"
    echo "  splunk        - Splunk Enterprise or Observability Cloud"
    exit 1
fi

# Determine config file
if [ "$PLATFORM" = "base" ]; then
    CONFIG_FILE="$COLLECTOR_DIR/otel-collector.yaml"
elif [ "$PLATFORM" = "aws" ]; then
    CONFIG_FILE="$COLLECTOR_DIR/aws-cloudwatch.yaml"
elif [ "$PLATFORM" = "gcp" ]; then
    CONFIG_FILE="$COLLECTOR_DIR/gcp-cloud-logging.yaml"
elif [ "$PLATFORM" = "azure" ]; then
    CONFIG_FILE="$COLLECTOR_DIR/azure-monitor.yaml"
else
    CONFIG_FILE="$COLLECTOR_DIR/${PLATFORM}.yaml"
fi

# Verify config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Update docker-compose.yml to use the selected config
echo "🔧 Switching OTLP collector to: $PLATFORM"
echo "   Config file: $CONFIG_FILE"

# Create backup of docker-compose.yml
cp "$DOCKER_COMPOSE_FILE" "$DOCKER_COMPOSE_FILE.bak"

# Update the volumes section to mount the correct config
# This is a simple approach - update the symlink or env var instead
cd "$COLLECTOR_DIR"
if [ -L "active-config.yaml" ]; then
    rm active-config.yaml
fi
ln -s "$(basename "$CONFIG_FILE")" active-config.yaml

echo "✅ OTLP collector configuration switched to: $PLATFORM"
echo ""
echo "📝 Next steps:"
echo "   1. Set required environment variables in .env"
echo "   2. Restart Docker Compose: docker compose restart otel-collector"
echo ""

# Display required environment variables
case "$PLATFORM" in
    aws)
        echo "   Required environment variables:"
        echo "   - AWS_REGION=us-east-1"
        echo "   - AWS_ACCESS_KEY_ID=... (or use IAM role)"
        echo "   - AWS_SECRET_ACCESS_KEY=... (or use IAM role)"
        ;;
    gcp)
        echo "   Required environment variables:"
        echo "   - GCP_PROJECT_ID=your-project-id"
        echo "   - GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json (or use Workload Identity)"
        ;;
    azure)
        echo "   Required environment variables:"
        echo "   - AZURE_MONITOR_CONNECTION_STRING=InstrumentationKey=...;IngestionEndpoint=..."
        echo "   Or:"
        echo "   - AZURE_MONITOR_INSTRUMENTATION_KEY=your-key"
        ;;
    elasticsearch)
        echo "   Required environment variables:"
        echo "   - ELASTICSEARCH_ENDPOINT=https://elasticsearch:9200"
        echo "   - ELASTICSEARCH_USERNAME=elastic"
        echo "   - ELASTICSEARCH_PASSWORD=changeme"
        ;;
    datadog)
        echo "   Required environment variables:"
        echo "   - DATADOG_API_KEY=your-api-key"
        echo "   - DATADOG_SITE=datadoghq.com"
        ;;
    splunk)
        echo "   Required environment variables:"
        echo "   - SPLUNK_HEC_TOKEN=your-hec-token"
        echo "   - SPLUNK_HEC_ENDPOINT=https://splunk:8088"
        ;;
esac

echo ""
echo "💡 Tip: Use 'docker compose logs otel-collector' to verify configuration"
