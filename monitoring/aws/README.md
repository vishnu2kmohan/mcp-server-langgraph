# AWS CloudWatch Monitoring

CloudWatch monitoring configuration for MCP Server LangGraph on AWS EKS.

## Features

- **CloudWatch Dashboards**: Pre-configured dashboard with EKS, RDS, ElastiCache, and application metrics
- **CloudWatch Alarms**: Automated alerts for high error rates, response times, and resource utilization
- **Log Aggregation**: Centralized logs in CloudWatch Logs
- **Container Insights**: EKS cluster-level monitoring

## Setup

### 1. Configure Environment

```bash
export EKS_CLUSTER_NAME=mcp-langgraph-prod-eks
export AWS_REGION=us-east-1
export ALARM_SNS_TOPIC=arn:aws:sns:us-east-1:123456789012:mcp-alerts
```

### 2. Run Setup Script

```bash
cd monitoring/aws
./setup-monitoring.sh
```

This will:
- Create CloudWatch Log Groups with appropriate retention
- Create CloudWatch Dashboard
- Create CloudWatch Alarms (if SNS topic provided)
- Check Container Insights status

## Dashboard

The CloudWatch dashboard includes:

1. **EKS Cluster Metrics**
   - Node count and health
   - Pod count and status

2. **Application Metrics**
   - Request rate and errors
   - Response time (average and p99)

3. **RDS Metrics**
   - CPU utilization
   - Database connections
   - Storage usage

4. **ElastiCache Metrics**
   - CPU utilization
   - Current connections
   - Cache hit rate

5. **Recent Errors**
   - Log query showing recent ERROR entries

## Alarms

Pre-configured alarms (requires SNS topic):

| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| High Error Rate | requests_errors | > 5% | Send SNS notification |
| High Response Time | response_time_ms (p99) | > 2000ms | Send SNS notification |
| RDS High CPU | RDS CPUUtilization | > 80% | Send SNS notification |
| ElastiCache High CPU | ElastiCache CPUUtilization | > 80% | Send SNS notification |

## Viewing Logs

### Tail logs in real-time
```bash
aws logs tail /aws/eks/mcp-server-langgraph --follow --region us-east-1
```

### Filter for errors
```bash
aws logs filter-log-events \
  --log-group-name /aws/eks/mcp-server-langgraph \
  --filter-pattern ERROR \
  --region us-east-1
```

### CloudWatch Insights queries

**Error rate by service**:
```
fields @timestamp, service.name, @message
| filter @message like /ERROR/
| stats count() by service.name
| sort count desc
```

**Slow queries (> 1s)**:
```
fields @timestamp, @message
| filter response_time_ms > 1000
| sort @timestamp desc
| limit 20
```

## Cost Optimization

- **Log Retention**: Automatically configured based on environment:
  - Production: 30 days
  - Staging: 7 days
  - Development: 1 day

- **Metrics**: CloudWatch charges per metric and API call
  - Estimated cost: $3-10/month for standard deployment

- **Logs**: Charged per GB ingested and stored
  - Estimated cost: $5-20/month depending on log volume

## Container Insights

Enable Container Insights for enhanced EKS monitoring:

```bash
aws eks update-cluster-config \
  --name mcp-langgraph-prod-eks \
  --region us-east-1 \
  --logging '{
    "clusterLogging": [{
      "types": ["api", "audit", "authenticator", "controllerManager", "scheduler"],
      "enabled": true
    }]
  }'
```

Cost: ~$10/month per cluster

## Troubleshooting

### Dashboard not showing data

Check that:
1. Application is running and emitting metrics
2. OpenTelemetry collector is configured for CloudWatch
3. IAM permissions allow CloudWatch PutMetricData

### Alarms not firing

Verify:
1. SNS topic exists and subscriptions are confirmed
2. Metrics are being published to CloudWatch
3. Threshold values are appropriate for your environment

### High CloudWatch costs

Optimize by:
1. Reducing log retention periods
2. Filtering logs before sending to CloudWatch
3. Using metric filters instead of detailed logs
4. Disabling Container Insights for non-production environments

## Additional Resources

- [CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [Container Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html)
- [CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)
