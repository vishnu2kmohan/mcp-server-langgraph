# GCP Cost Optimization Playbook

**Version**: 1.0
**Last Updated**: 2025-11-01
**Target**: 40-60% cost reduction vs. baseline GKE
**Audience**: Platform Engineers, FinOps, Engineering Leadership

---

## Executive Summary

This playbook provides actionable strategies to optimize GCP costs for MCP Server LangGraph deployment while maintaining performance, security, and reliability.

**Current Baseline** (Production):
- GKE Autopilot: $360/month
- Cloud SQL: $280/month
- Memorystore Redis: $220/month
- Networking: $60/month
- Monitoring/Logging: $50/month
- **Total**: $970/month

**Optimized Target**: $580-680/month (30-40% savings = $290-390/month)

---

## Strategy 1: GKE Autopilot Optimization

### Current Costs

**Autopilot Pricing** (pay-per-pod):
- vCPU: $0.048/hour = $35/month per core
- Memory: $0.0053/GB/hour = $3.86/month per GB
- Storage: $0.000137/GB/hour = $0.10/month per GB

### Optimization Tactics

#### 1.1 Right-Size Pod Resources

**Problem**: Over-provisioned resource requests

**Current** (3 pods):
```yaml
resources:
  requests:
    cpu: 500m       # $52.50/month
    memory: 1Gi     # $11.58/month
  # Per pod: $64/month × 3 = $192/month
```

**Optimized** (after profiling):
```yaml
resources:
  requests:
    cpu: 250m       # $26.25/month
    memory: 512Mi   # $5.79/month
  # Per pod: $32/month × 3 = $96/month
```

**Savings**: $96/month (50% reduction)

**Action**:
```bash
# 1. Profile actual usage
kubectl top pods -n mcp-production --containers

# 2. Analyze over 7 days
gcloud monitoring time-series list \
  --filter='metric.type="kubernetes.io/container/cpu/core_usage_time"' \
  --project=PROJECT_ID \
  | jq '.[] | {pod: .resource.labels.pod_name, cpu: .points[].value.doubleValue}' \
  | jq -s 'group_by(.pod) | .[] | {pod: .[0].pod, avg_cpu: ([.[].cpu] | add / length)}'

# 3. Update deployment with optimized values
kubectl patch deployment production-mcp-server-langgraph -n mcp-production \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/cpu", "value": "250m"}]'
```

#### 1.2 Enable Vertical Pod Autoscaler (VPA)

**Automatically adjust resource requests**:

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: production-mcp-server-vpa
  namespace: mcp-production
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: production-mcp-server-langgraph
  updatePolicy:
    updateMode: Auto  # Or "Recommend" for manual review
```

**Savings**: 10-30% by auto-optimizing requests

#### 1.3 Optimize HPA Settings

**Current**: 3-20 replicas, scale at 60% CPU

**Optimized**:
```yaml
spec:
  minReplicas: 2  # Reduce from 3 (save $32/month)
  maxReplicas: 15  # Reduce from 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # Increase from 60%
```

**Savings**: $32/month (1 fewer min replica)

---

## Strategy 2: Cloud SQL Optimization

### Current Costs

**db-custom-4-15360** (4 vCPU, 15 GB RAM, HA):
- Instance: $280/month
- Storage: $17/month (100 GB SSD)
- **Total**: $297/month

### Optimization Tactics

#### 2.1 Right-Size Instance

**Analyze actual usage**:
```bash
# CPU utilization (last 7 days)
gcloud sql instances describe mcp-prod-postgres \
  --format="value(settings.tier)"

# Query insights
gcloud sql instances describe mcp-prod-postgres \
  --format="yaml(insightsConfig)"
```

**If CPU < 50% consistently**, downgrade:
- **db-custom-4-15360** → **db-custom-2-7680** (2 vCPU, 7.5 GB)
- **Savings**: $140/month (50%)

**Action**:
```hcl
# terraform/environments/gcp-prod/terraform.tfvars
cloudsql_tier = "db-custom-2-7680"
```

```bash
terraform apply
```

#### 2.2 Optimize Backups

**Current**: 30 backups + 7-day PITR

**Optimized**:
```hcl
backup_retention_count         = 14  # Reduce to 14 days
transaction_log_retention_days = 3   # Reduce to 3 days
```

**Savings**: $5-10/month

#### 2.3 Evaluate Read Replica Necessity

**Question**: Do you actually use the read replica?

**Check**:
```bash
# Connection count to read replica
gcloud sql instances describe mcp-prod-postgres-replica-1 \
  --format="value(currentDiskSize,state)"
```

**If unused**, remove:
```hcl
cloudsql_read_replica_count = 0
```

**Savings**: $140/month (full instance cost)

---

## Strategy 3: Memorystore Redis Optimization

### Current Costs

**5 GB STANDARD_HA**: $220/month

### Optimization Tactics

#### 3.1 Right-Size Memory

**Check actual usage**:
```bash
gcloud redis instances describe mcp-prod-redis \
  --region=us-central1 \
  --format="value(currentLocationId,memorySizeGb)"

# Memory usage metrics
gcloud monitoring time-series list \
  --filter='metric.type="redis.googleapis.com/stats/memory/usage_ratio"' \
  --project=PROJECT_ID
```

**If usage < 60%**, downgrade:
- 5 GB → 3 GB
- **Savings**: $88/month (40%)

#### 3.2 Evaluate STANDARD_HA Necessity

**For non-critical caching** (where cache miss is acceptable):
- STANDARD_HA → BASIC
- **Savings**: $110/month (50%)

**⚠️ Warning**: BASIC tier has no SLA, no auto-failover

#### 3.3 Optimize Persistence

**RDB snapshots** consume storage and I/O.

**Options**:
1. **Disable persistence** (if cache is rebuildable): $0 storage cost
2. **Reduce snapshot frequency**: 12 hours → 24 hours

---

## Strategy 4: Networking Optimization

### Current Costs

- NAT: $30/month (2 static IPs)
- Egress: $20/month
- Load Balancing: $10/month

### Optimization Tactics

#### 4.1 Use Auto NAT IPs (Non-Production)

**For dev/staging** (no static IP whitelisting needed):
```hcl
nat_ip_allocate_option = "AUTO_ONLY"
```

**Savings**: $30/month per environment

#### 4.2 Reduce Egress Traffic

**Techniques**:
1. **Use GCP services** (free egress within region)
2. **Cache API responses** (reduce external calls)
3. **Compress responses** (smaller data transfer)
4. **Use Cloud CDN** (cache at edge)

**Potential savings**: 20-40% of egress costs

#### 4.3 Optimize Flow Logs

**Current**: 10% sampling

**For dev**: Disable entirely
**For staging**: 5% sampling
**For production**: Keep 10%

**Savings**: $5-10/month

---

## Strategy 5: Monitoring & Logging Optimization

### Current Costs

- Cloud Monitoring: $25/month
- Cloud Logging: $20/month
- Storage: $5/month

### Optimization Tactics

#### 5.1 Reduce Log Retention

**Current**: 30 days

**Optimized**:
- **Error logs**: 30 days (keep)
- **Info logs**: 7 days
- **Debug logs**: 1 day or disable

```bash
# Set retention policy
gcloud logging sinks update LOG_SINK \
  --log-filter='severity>=ERROR' \
  --project=PROJECT_ID
```

**Savings**: $10-15/month

#### 5.2 Sample Traces

**Cloud Trace sampling**:
- Development: 0% (disable)
- Staging: 1%
- Production: 10% (current)

Already optimized in `otel-collector-config.yaml`

#### 5.3 Optimize Metric Collection

**Disable unnecessary metrics**:
```hcl
monitoring_enabled_components = ["SYSTEM_COMPONENTS"]  # Remove "WORKLOADS" if not needed
```

**Savings**: $5-10/month

---

## Strategy 6: Committed Use Discounts (CUDs)

### Overview

**Commit to 1-year or 3-year usage** for significant discounts:

| Resource | 1-Year | 3-Year |
|----------|--------|--------|
| GKE Autopilot | 25% | 52% |
| Cloud SQL | 25% | 52% |
| Memorystore | 25% | 52% |

### Cost Impact

**Current** (on-demand): $970/month

**With 1-year CUD**: $728/month (25% savings = **$242/month**)

**With 3-year CUD**: $466/month (52% savings = **$504/month**)

### How to Purchase

```bash
# 1. Analyze current usage (last 30 days)
gcloud billing accounts describe BILLING_ACCOUNT_ID

# 2. Purchase commitment via Cloud Console
# Go to: Billing → Commitments → Purchase Commitment

# 3. Select resources:
#    - Compute: 4 vCPU + 16 GB RAM (for Cloud SQL + GKE)
#    - Term: 1 year or 3 years

# 4. Auto-renew option: Enable for continuous savings
```

**ROI**: Pays for itself in 1 month

---

## Strategy 7: Development & Staging Cost Controls

### Development Environment

**Current dev setup** already optimized:
- Zonal cluster (not regional): 50% savings
- BASIC Redis (not STANDARD_HA): 50% savings
- No HA Cloud SQL: 50% savings
- Auto NAT IPs: $30 savings

**Estimated**: $100-150/month

**Additional savings**:
1. **Auto-shutdown** dev cluster after hours:
   ```bash
   # Cloud Scheduler job to scale to zero at 6 PM
   gcloud scheduler jobs create app-engine scale-down-dev \
     --schedule="0 18 * * 1-5" \
     --http-method=POST \
     --uri="https://container.googleapis.com/v1/projects/PROJECT_ID/zones/us-central1-a/clusters/mcp-dev-gke/nodePools/default-pool" \
     --message-body='{"desiredNodeCount":0}'
   ```

2. **Delete dev on weekends**: Save ~30%

### Staging Environment

**Optimize when not in use**:
```bash
# Scale staging to minimal (Friday 6 PM)
kubectl scale deployment staging-mcp-server-langgraph -n mcp-staging --replicas=1

# Scale back up (Monday 6 AM)
kubectl scale deployment staging-mcp-server-langgraph -n mcp-staging --replicas=2
```

**Savings**: $50-70/month

---

## Strategy 8: Storage Optimization

### Persistent Disk Optimization

**Use Balanced PD** instead of SSD where possible:
- SSD: $0.17/GB/month
- Balanced: $0.10/GB/month
- **Savings**: 41%

**Enable disk autoresize**:
```hcl
enable_disk_autoresize = true
```

**Cleanup unused disks**:
```bash
# Find unattached disks
gcloud compute disks list --filter="users:null" --project=PROJECT_ID

# Delete unused
gcloud compute disks delete DISK_NAME --zone=ZONE --project=PROJECT_ID
```

### Snapshot Optimization

**Incremental snapshots** instead of full:
```bash
# Schedule incremental snapshots
gcloud compute resource-policies create snapshot-schedule daily-snapshot \
  --region=us-central1 \
  --max-retention-days=14 \
  --on-source-disk-delete=keep-auto-snapshots \
  --daily-schedule \
  --start-time=02:00 \
  --project=PROJECT_ID
```

---

## Cost Monitoring & Alerts

### Set Up Budget Alerts

```bash
# Create budget with alerts at 50%, 90%, 100%
gcloud billing budgets create \
  --billing-account=BILLING_ACCOUNT_ID \
  --display-name="MCP Production Monthly Budget" \
  --budget-amount=1200USD \
  --threshold-rule=percent=50 \
  --threshold-rule=percent=90 \
  --threshold-rule=percent=100 \
  --all-updates-rule-pubsub-topic=projects/PROJECT_ID/topics/budget-alerts
```

### Enable Cost Allocation

**Already enabled in Terraform**:
```hcl
enable_cost_allocation = true
```

**View costs by label**:
```bash
# Export billing to BigQuery
gcloud billing accounts describe BILLING_ACCOUNT_ID

# Query in BigQuery
SELECT
  labels.value AS team,
  SUM(cost) AS total_cost
FROM
  `PROJECT_ID.billing_dataset.gcp_billing_export_*`
WHERE
  labels.key = 'team'
GROUP BY
  team
ORDER BY
  total_cost DESC
```

### Cost Anomaly Detection

```bash
# Set up anomaly detection alert
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Cost Anomaly Alert" \
  --condition-display-name="Unexpected cost increase" \
  --condition-threshold-value=1.5 \
  --comparison-type=COMPARISON_GT \
  --project=PROJECT_ID
```

---

## Optimization Roadmap

### Month 1: Quick Wins ($100-150/month savings)

- [x] GKE Autopilot (vs. Standard GKE): $200 saved
- [ ] Right-size pod resources: $96 saved
- [ ] Reduce dev/staging usage: $50 saved
- [ ] Optimize log retention: $15 saved

**Total Month 1**: $361/month saved

### Month 2: Committed Use Discounts ($200-300/month savings)

- [ ] Purchase 1-year CUD: $242/month saved
- [ ] Right-size Cloud SQL: $140 saved (if applicable)
- [ ] Optimize Redis tier: $88 saved (if caching is non-critical)

**Total Month 2**: $470/month additional savings

### Month 3-6: Advanced Optimization ($50-100/month savings)

- [ ] Implement autoscaling schedules
- [ ] Optimize network egress
- [ ] Cleanup unused resources
- [ ] Implement FinOps best practices

**Total Potential**: $580/month savings (60% of baseline)

---

## Cost Comparison by Environment

| Environment | Current | Optimized | Savings |
|-------------|---------|-----------|---------|
| **Production** | $970 | $680 | $290 (30%) |
| **Staging** | $310 | $200 | $110 (35%) |
| **Development** | $100 | $50 | $50 (50%) |
| **Total** | **$1,380** | **$930** | **$450 (33%)** |

---

## Tools & Automation

### Cost Monitoring Script

```bash
#!/bin/bash
# daily-cost-report.sh

PROJECT_ID="YOUR_PROJECT_ID"

echo "=== GCP Cost Report ==="
echo "Date: $(date)"
echo

# Current month costs
gcloud billing accounts describe BILLING_ACCOUNT_ID \
  --format="table(name,displayName,open)"

# Cost by service
bq query --use_legacy_sql=false "
SELECT
  service.description AS service,
  SUM(cost) AS total_cost
FROM
  \`PROJECT_ID.billing_dataset.gcp_billing_export_*\`
WHERE
  _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY
  service
ORDER BY
  total_cost DESC
LIMIT 10
"

# Top 10 resources by cost
bq query --use_legacy_sql=false "
SELECT
  labels.value AS resource_name,
  SUM(cost) AS total_cost
FROM
  \`PROJECT_ID.billing_dataset.gcp_billing_export_*\`
WHERE
  _PARTITIONDATE >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND labels.key = 'name'
GROUP BY
  resource_name
ORDER BY
  total_cost DESC
LIMIT 10
"
```

### Automated Cleanup

```bash
# cleanup-unused-resources.sh

# Delete unused disks
gcloud compute disks list --filter="users:null" --format="value(name,zone)" \
  | while read name zone; do
      gcloud compute disks delete $name --zone=$zone --quiet
    done

# Delete old backups (keep 30 days)
gcloud sql backups list --instance=mcp-prod-postgres \
  --filter="window.endTime<$(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%S).000Z" \
  --format="value(id)" \
  | while read backup_id; do
      gcloud sql backups delete $backup_id --instance=mcp-prod-postgres --quiet
    done
```

---

## Best Practices

### 1. Use Labels Consistently

```hcl
labels = {
  environment = "production"
  team        = "platform"
  cost_center = "engineering"
  application = "mcp-server"
}
```

**Benefit**: Track costs by team, application, environment

### 2. Review Costs Weekly

**Schedule**:
- Monday morning: Review last week's costs
- Check for anomalies
- Investigate unexpected increases

### 3. Implement Quota Management

```bash
# Set quota for cost protection
gcloud compute project-info update \
  --usage-export-bucket=gs://BUCKET \
  --project=PROJECT_ID
```

### 4. Use Preemptible/Spot Instances (For Batch Workloads)

**Note**: Not applicable to Autopilot (managed automatically)

**For Standard GKE** (if needed):
- Spot instances: 60-91% cheaper
- Use for batch jobs, CI/CD

---

## ROI Analysis

### Investment

- **Development time**: 1 day
- **Testing**: 0.5 days
- **Ongoing monitoring**: 1 hour/week

### Returns

**Monthly Savings**:
- Quick wins: $150/month
- CUD: $242/month
- Right-sizing: $140/month
- **Total**: $532/month

**Annual Savings**: $6,384/year

**Payback Period**: Immediate (first month)

---

## Cost Optimization Checklist

### Monthly Review

- [ ] Review billing dashboard
- [ ] Check resource utilization (CPU, memory, disk)
- [ ] Identify unused resources
- [ ] Review committed use discount utilization
- [ ] Check for cost anomalies
- [ ] Update resource sizing based on actual usage
- [ ] Review and renew CUDs if expiring

### Quarterly Review

- [ ] Evaluate tier/size changes for all services
- [ ] Review multi-region strategy (is it needed?)
- [ ] Assess backup retention policies
- [ ] Re-evaluate environment necessity (do we need 3 envs?)
- [ ] Benchmark against industry standards

---

**End of Cost Optimization Playbook**

**Related Documents**:
- [Deployment Guide](./deployments/GKE_DEPLOYMENT_GUIDE.md)
- [Operational Runbooks](./deployments/GKE_OPERATIONAL_RUNBOOKS.md)
- [Implementation Status](./GCP_GKE_IMPLEMENTATION_COMPLETE.md)
