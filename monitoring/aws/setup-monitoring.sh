#!/bin/bash
# Setup CloudWatch monitoring for MCP Server on AWS EKS

set -e

# Configuration
CLUSTER_NAME="${EKS_CLUSTER_NAME:-mcp-langgraph-prod-eks}"
AWS_REGION="${AWS_REGION:-us-east-1}"
DASHBOARD_NAME="MCP-Server-LangGraph-${CLUSTER_NAME}"
ALARM_SNS_TOPIC="${ALARM_SNS_TOPIC:-}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
        exit 1
    fi

    log_info "✓ All prerequisites met"
}

create_dashboard() {
    log_info "Creating CloudWatch dashboard: $DASHBOARD_NAME..."

    # Update region in dashboard JSON
    DASHBOARD_JSON=$(cat cloudwatch-dashboard.json | sed "s/us-east-1/$AWS_REGION/g")

    aws cloudwatch put-dashboard \
        --dashboard-name "$DASHBOARD_NAME" \
        --dashboard-body "$DASHBOARD_JSON" \
        --region "$AWS_REGION"

    log_info "✓ Dashboard created: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=$DASHBOARD_NAME"
}

create_log_groups() {
    log_info "Creating CloudWatch Log Groups..."

    # Application logs
    aws logs create-log-group \
        --log-group-name "/aws/eks/mcp-server-langgraph" \
        --region "$AWS_REGION" 2>/dev/null || log_warn "Log group already exists"

    # Metrics logs
    aws logs create-log-group \
        --log-group-name "/aws/eks/mcp-server-langgraph/metrics" \
        --region "$AWS_REGION" 2>/dev/null || log_warn "Metrics log group already exists"

    # Set retention policy (30 days for production, 7 days for staging/dev)
    RETENTION_DAYS=30
    if [[ "$CLUSTER_NAME" == *"staging"* ]]; then
        RETENTION_DAYS=7
    elif [[ "$CLUSTER_NAME" == *"dev"* ]]; then
        RETENTION_DAYS=1
    fi

    aws logs put-retention-policy \
        --log-group-name "/aws/eks/mcp-server-langgraph" \
        --retention-in-days "$RETENTION_DAYS" \
        --region "$AWS_REGION"

    log_info "✓ Log groups created with $RETENTION_DAYS day retention"
}

create_alarms() {
    log_info "Creating CloudWatch Alarms..."

    if [ -z "$ALARM_SNS_TOPIC" ]; then
        log_warn "ALARM_SNS_TOPIC not set. Skipping alarm creation."
        log_warn "Set ALARM_SNS_TOPIC to create alarms: export ALARM_SNS_TOPIC=arn:aws:sns:region:account:topic"
        return
    fi

    # High error rate alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${CLUSTER_NAME}-high-error-rate" \
        --alarm-description "Alert when error rate exceeds 5%" \
        --metric-name requests_errors \
        --namespace MCPServer/EKS \
        --statistic Sum \
        --period 300 \
        --evaluation-periods 2 \
        --threshold 5 \
        --comparison-operator GreaterThanThreshold \
        --alarm-actions "$ALARM_SNS_TOPIC" \
        --region "$AWS_REGION"

    # High response time alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${CLUSTER_NAME}-high-response-time" \
        --alarm-description "Alert when p99 response time exceeds 2000ms" \
        --metric-name response_time_ms \
        --namespace MCPServer/EKS \
        --statistic p99 \
        --period 300 \
        --evaluation-periods 2 \
        --threshold 2000 \
        --comparison-operator GreaterThanThreshold \
        --alarm-actions "$ALARM_SNS_TOPIC" \
        --region "$AWS_REGION"

    # RDS CPU alarm
    aws cloudwatch put-metric-alarm \
        --alarm-name "${CLUSTER_NAME}-rds-high-cpu" \
        --alarm-description "Alert when RDS CPU exceeds 80%" \
        --metric-name CPUUtilization \
        --namespace AWS/RDS \
        --statistic Average \
        --period 300 \
        --evaluation-periods 2 \
        --threshold 80 \
        --comparison-operator GreaterThanThreshold \
        --alarm-actions "$ALARM_SNS_TOPIC" \
        --region "$AWS_REGION"

    log_info "✓ CloudWatch alarms created"
}

setup_container_insights() {
    log_info "Checking Container Insights for EKS..."

    # Check if Container Insights is enabled
    INSIGHTS_ENABLED=$(aws eks describe-cluster \
        --name "$CLUSTER_NAME" \
        --region "$AWS_REGION" \
        --query "cluster.logging.clusterLogging[?types[?contains(@, 'api')]].enabled | [0]" \
        --output text 2>/dev/null || echo "false")

    if [ "$INSIGHTS_ENABLED" = "true" ]; then
        log_info "✓ Container Insights already enabled"
    else
        log_warn "Container Insights not enabled. Enable via:"
        log_warn "  aws eks update-cluster-config --name $CLUSTER_NAME --region $AWS_REGION --logging '{\"clusterLogging\":[{\"types\":[\"api\",\"audit\",\"authenticator\",\"controllerManager\",\"scheduler\"],\"enabled\":true}]}'"
    fi
}

print_next_steps() {
    log_info "\n=========================================="
    log_info "MONITORING SETUP COMPLETE!"
    log_info "==========================================\n"

    log_info "Access CloudWatch Dashboard:"
    log_info "  https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:name=$DASHBOARD_NAME"
    echo ""
    log_info "View Logs:"
    log_info "  aws logs tail /aws/eks/mcp-server-langgraph --follow --region $AWS_REGION"
    echo ""
    log_info "Query Logs (recent errors):"
    log_info "  aws logs filter-log-events --log-group-name /aws/eks/mcp-server-langgraph --filter-pattern ERROR --region $AWS_REGION"
    echo ""
    log_info "View Alarms:"
    log_info "  aws cloudwatch describe-alarms --alarm-name-prefix ${CLUSTER_NAME}- --region $AWS_REGION"
}

# Main execution
main() {
    log_info "Setting up CloudWatch monitoring for $CLUSTER_NAME in $AWS_REGION..."

    check_prerequisites
    create_log_groups
    create_dashboard
    create_alarms
    setup_container_insights
    print_next_steps

    log_info "\n✓ Monitoring setup completed successfully!"
}

main "$@"
