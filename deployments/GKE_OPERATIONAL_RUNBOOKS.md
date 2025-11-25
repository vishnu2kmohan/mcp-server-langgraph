# GKE Operational Runbooks

**Version**: 1.0
**Last Updated**: 2025-11-01
**Audience**: Platform Engineers, SREs, DevOps
**Environment**: GCP GKE Autopilot Production

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Incident Response](#incident-response)
3. [Deployment Operations](#deployment-operations)
4. [Database Operations](#database-operations)
5. [Scaling Operations](#scaling-operations)
6. [Security Operations](#security-operations)
7. [Disaster Recovery](#disaster-recovery)
8. [Monitoring & Alerts](#monitoring--alerts)

---

## Daily Operations

### Morning Health Check (5 minutes)

```bash
#!/bin/bash
# Daily health check routine

PROJECT_ID="YOUR_PROJECT_ID"
CLUSTER="production-mcp-server-langgraph-gke"
REGION="us-central1"
NAMESPACE="mcp-production"

echo "=== GKE Production Health Check ==="
echo "Date: $(date)"
echo

# 1. Get cluster credentials
gcloud container clusters get-credentials $CLUSTER \
  --region=$REGION \
  --project=$PROJECT_ID

# 2. Check cluster status
echo "Cluster Status:"
gcloud container clusters describe $CLUSTER \
  --region=$REGION \
  --project=$PROJECT_ID \
  --format="value(status)"

# 3. Check node health (Autopilot manages nodes, but good to verify)
echo -e "\nNode Count:"
kubectl get nodes --no-headers | wc -l

# 4. Check pod status
echo -e "\nPod Status:"
kubectl get pods -n $NAMESPACE \
  -o custom-columns=NAME:.metadata.name,STATUS:.status.phase,RESTARTS:.status.containerStatuses[0].restartCount

# 5. Check failed pods
FAILED_PODS=$(kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running,status.phase!=Succeeded --no-headers 2>/dev/null | wc -l)
if [ $FAILED_PODS -gt 0 ]; then
  echo -e "\n❌ WARNING: $FAILED_PODS failed pods found"
  kubectl get pods -n $NAMESPACE --field-selector=status.phase!=Running,status.phase!=Succeeded
else
  echo -e "\n✅ All pods healthy"
fi

# 6. Check HPA status
echo -e "\nHorizontal Pod Autoscaler:"
kubectl get hpa -n $NAMESPACE

# 7. Check recent events (last 30 minutes)
echo -e "\nRecent Events:"
kubectl get events -n $NAMESPACE \
  --sort-by='.lastTimestamp' \
  --field-selector=type!=Normal \
  | tail -10

# 8. Cloud SQL status
echo -e "\nCloud SQL Status:"
gcloud sql instances list \
  --filter="name:mcp-prod-postgres" \
  --format="table(name,state,ipAddresses[0].ipAddress)" \
  --project=$PROJECT_ID

# 9. Redis status
echo -e "\nMemorystore Redis Status:"
gcloud redis instances list \
  --region=$REGION \
  --filter="name:mcp-prod-redis" \
  --format="table(name,state,host,port)" \
  --project=$PROJECT_ID

# 10. Recent errors in logs (last hour)
echo -e "\nRecent Errors (last hour):"
gcloud logging read \
  'resource.type="k8s_container" AND resource.labels.namespace_name="'$NAMESPACE'" AND severity>=ERROR' \
  --limit=5 \
  --format="table(timestamp,jsonPayload.message)" \
  --project=$PROJECT_ID

echo -e "\n=== Health Check Complete ==="
```

**Expected Output**: All checks should show healthy status

**Remediation**: If issues found, see [Incident Response](#incident-response)

---

## Incident Response

### P0: Service Down (Complete Outage)

**Symptoms**:
- All pods crashing or unavailable
- Health checks failing
- Users cannot access service

**Response Procedure** (5-10 minutes):

```bash
# 1. Check pod status immediately
kubectl get pods -n mcp-production

# 2. Get pod logs (all pods)
kubectl logs -n mcp-production -l app=mcp-server-langgraph --tail=100

# 3. Describe failing pods
kubectl describe pod POD_NAME -n mcp-production

# 4. Check recent events
kubectl get events -n mcp-production --sort-by='.lastTimestamp' | tail -20

# 5. Quick fixes to try:

# Option A: Restart deployment
kubectl rollout restart deployment/production-mcp-server-langgraph -n mcp-production

# Option B: Rollback to previous version
kubectl rollout undo deployment/production-mcp-server-langgraph -n mcp-production

# Option C: Scale up to overcome bad pods
kubectl scale deployment production-mcp-server-langgraph \
  -n mcp-production \
  --replicas=6

# 6. Monitor recovery
kubectl rollout status deployment/production-mcp-server-langgraph -n mcp-production

# 7. Verify health
kubectl exec -it -n mcp-production \
  $(kubectl get pod -n mcp-production -l app=mcp-server-langgraph -o jsonpath='{.items[0].metadata.name}') \
  -- curl -f http://localhost:8000/health/live
```

**Root Cause Analysis** (after recovery):
```bash
# Check Cloud Logging for errors
gcloud logging read \
  'resource.type="k8s_container" AND resource.labels.namespace_name="mcp-production" AND severity>=ERROR' \
  --limit=50 \
  --format=json \
  --project=PROJECT_ID > incident-logs.json

# Analyze logs
jq '.[] | {time: .timestamp, message: .jsonPayload.message, pod: .resource.labels.pod_name}' incident-logs.json
```

**Escalation**: If not resolved in 10 minutes, escalate to on-call architect

---

### P1: Performance Degradation

**Symptoms**:
- Slow response times
- High CPU/memory usage
- Increased error rates

**Response Procedure**:

```bash
# 1. Check resource usage
kubectl top pods -n mcp-production
kubectl top nodes

# 2. Check HPA status
kubectl get hpa -n mcp-production -o yaml

# 3. Check if hitting resource limits
kubectl describe pod -n mcp-production -l app=mcp-server-langgraph | grep -A 10 "Limits\|Requests"

# 4. Review recent deployments
kubectl rollout history deployment/production-mcp-server-langgraph -n mcp-production

# 5. Check Cloud SQL performance
gcloud sql operations list \
  --instance=mcp-prod-postgres \
  --filter="startTime>=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S).000000Z" \
  --project=PROJECT_ID

# 6. Check Redis metrics
gcloud monitoring time-series list \
  --filter='resource.type="redis_instance" AND metric.type="redis.googleapis.com/stats/cpu_utilization"' \
  --project=PROJECT_ID

# 7. Scale up if needed (temporary)
kubectl scale deployment production-mcp-server-langgraph \
  -n mcp-production \
  --replicas=10

# 8. Monitor improvement
watch -n 5 'kubectl top pods -n mcp-production'
```

**Permanent Fix**: Adjust resource requests/limits based on actual usage

---

### P2: Database Connection Issues

**Symptoms**:
- "Connection refused" errors
- "Too many connections" errors
- Slow queries

**Response Procedure**:

```bash
# 1. Check Cloud SQL Proxy health
kubectl logs -n mcp-production -l app=mcp-server-langgraph -c cloud-sql-proxy --tail=50

# 2. Verify Cloud SQL instance is running
gcloud sql instances describe mcp-prod-postgres \
  --project=PROJECT_ID \
  --format="value(state)"

# 3. Check connection count
gcloud sql operations list \
  --instance=mcp-prod-postgres \
  --limit=10 \
  --project=PROJECT_ID

# 4. Check for blocked queries
# (Connect to database via Cloud SQL Proxy)
kubectl port-forward -n mcp-production svc/production-mcp-server-langgraph 5432:5432 &
psql "host=localhost port=5432 user=postgres dbname=mcp_langgraph" -c "SELECT pid, query, state FROM pg_stat_activity WHERE state != 'idle';"

# 5. Kill long-running queries (if needed)
psql -c "SELECT pg_terminate_backend(PID);"

# 6. Restart Cloud SQL Proxy pods
kubectl rollout restart deployment/production-mcp-server-langgraph -n mcp-production
```

**Prevention**: Monitor connection pool size, set `postgres_max_connections` appropriately

---

## Deployment Operations

### Standard Deployment

**Using CI/CD** (Recommended):
```bash
# 1. Create release in GitHub
gh release create v1.1.0 --title "Release 1.1.0" --notes "Release notes"

# 2. CI/CD automatically:
#    - Builds image
#    - Runs security scans
#    - Deploys to production (after manual approval)

# 3. Monitor deployment
# Go to: https://github.com/USER/REPO/actions
```

**Manual Deployment** (Emergency):
```bash
# 1. Update image tag
cd deployments/overlays/production-gke
kustomize edit set image mcp-server-langgraph=ARTIFACT_REGISTRY/IMAGE:TAG

# 2. Dry-run
kubectl apply -k . --dry-run=server

# 3. Apply
kubectl apply -k .

# 4. Monitor
kubectl rollout status deployment/production-mcp-server-langgraph -n mcp-production --timeout=10m

# 5. Verify
kubectl get pods -n mcp-production
kubectl logs -n mcp-production -l app=mcp-server-langgraph --tail=20
```

### Rollback Deployment

```bash
# Quick rollback (last revision)
kubectl rollout undo deployment/production-mcp-server-langgraph -n mcp-production

# Rollback to specific revision
kubectl rollout history deployment/production-mcp-server-langgraph -n mcp-production
kubectl rollout undo deployment/production-mcp-server-langgraph -n mcp-production --to-revision=5

# Monitor rollback
kubectl rollout status deployment/production-mcp-server-langgraph -n mcp-production
```

### Emergency Stop

```bash
# Scale to zero (stops all pods)
kubectl scale deployment production-mcp-server-langgraph -n mcp-production --replicas=0

# Resume
kubectl scale deployment production-mcp-server-langgraph -n mcp-production --replicas=3
```

---

## Database Operations

### Cloud SQL Backup & Restore

**Create Manual Backup**:
```bash
# Create on-demand backup
gcloud sql backups create \
  --instance=mcp-prod-postgres \
  --project=PROJECT_ID \
  --description="Manual backup before major change"

# List backups
gcloud sql backups list \
  --instance=mcp-prod-postgres \
  --project=PROJECT_ID
```

**Restore from Backup**:
```bash
# Restore to same instance (⚠️ CAUTION: Destructive)
gcloud sql backups restore BACKUP_ID \
  --backup-instance=mcp-prod-postgres \
  --backup-instance-project=PROJECT_ID

# Restore to new instance (Recommended)
gcloud sql instances clone mcp-prod-postgres mcp-prod-postgres-restored \
  --backup-id=BACKUP_ID \
  --project=PROJECT_ID
```

**Point-in-Time Recovery** (PITR):
```bash
# Restore to specific timestamp
gcloud sql instances clone mcp-prod-postgres mcp-prod-postgres-pitr \
  --point-in-time='2025-11-01T12:00:00.000Z' \
  --project=PROJECT_ID
```

### Redis Snapshot & Recovery

**Manual RDB Snapshot**:
```bash
# Trigger manual snapshot
gcloud redis instances export gs://BUCKET_NAME/redis-backup-$(date +%Y%m%d-%H%M%S).rdb \
  --source=mcp-prod-redis \
  --region=us-central1 \
  --project=PROJECT_ID
```

**Import from Snapshot**:
```bash
# Create new instance from backup
gcloud redis instances import gs://BUCKET_NAME/redis-backup.rdb \
  --source-instance=mcp-prod-redis \
  --region=us-central1 \
  --project=PROJECT_ID
```

---

## Scaling Operations

### Manual Scaling

```bash
# Scale deployment
kubectl scale deployment production-mcp-server-langgraph \
  -n mcp-production \
  --replicas=10

# Update HPA
kubectl patch hpa production-mcp-server-langgraph \
  -n mcp-production \
  --patch '{"spec":{"minReplicas":5,"maxReplicas":30}}'
```

### Cluster Resource Limits

**Check current usage**:
```bash
# GKE resource usage
gcloud container clusters describe production-mcp-server-langgraph-gke \
  --region=us-central1 \
  --format="yaml(resourceUsageExportConfig, currentMasterVersion)"

# Cloud Monitoring query
gcloud monitoring time-series list \
  --filter='metric.type="kubernetes.io/container/cpu/core_usage_time"' \
  --project=PROJECT_ID
```

**Update limits** (via Terraform):
```hcl
# terraform/environments/gcp-prod/terraform.tfvars
max_cluster_cpu    = 2000  # Increase to 2000 vCPUs
max_cluster_memory = 20000 # Increase to 20,000 GB
```

Apply:
```bash
cd terraform/environments/gcp-prod
terraform apply -target=module.gke
```

---

## Security Operations

### Rotate Secrets

```bash
# 1. Generate new secrets
NEW_JWT_SECRET=$(openssl rand -base64 32)
NEW_API_KEY=$(openssl rand -base64 32)

# 2. Update Secret Manager
gcloud secrets versions add mcp-production-secrets \
  --data-file=<(jq --arg jwt "$NEW_JWT_SECRET" '.jwt_secret = $jwt' secrets.json) \
  --project=PROJECT_ID

# 3. Restart pods to pick up new secrets (External Secrets Operator auto-syncs)
kubectl rollout restart deployment/production-mcp-server-langgraph -n mcp-production
```

### Audit Access Logs

```bash
# View who accessed the cluster
gcloud logging read \
  'protoPayload.serviceName="container.googleapis.com" AND protoPayload.methodName="io.k8s.core.v1.pods.exec"' \
  --limit=50 \
  --project=PROJECT_ID

# View kubectl commands
gcloud logging read \
  'protoPayload.request.@type="type.googleapis.com/google.container.v1.SetNetworkPolicyRequest"' \
  --project=PROJECT_ID
```

### Review Binary Authorization Denials

```bash
gcloud logging read \
  'protoPayload.serviceName="binaryauthorization.googleapis.com" AND protoPayload.response.allow=false' \
  --limit=20 \
  --project=PROJECT_ID
```

---

## Disaster Recovery

### Cloud SQL Failover

**Trigger Manual Failover** (for testing):
```bash
gcloud sql instances failover mcp-prod-postgres \
  --project=PROJECT_ID

# Monitor failover
watch -n 5 'gcloud sql instances describe mcp-prod-postgres --format="value(state)"'
```

**Recovery Time**: ~2-3 minutes for automatic failover

### Redis Failover

**Redis STANDARD_HA** automatically fails over within 1-2 minutes.

**Verify failover**:
```bash
# Check current primary location
gcloud redis instances describe mcp-prod-redis \
  --region=us-central1 \
  --format="value(currentLocationId)"
```

### Complete Environment Recovery

**Scenario**: Entire region unavailable

**Steps**:
1. **Deploy to backup region**:
   ```bash
   # Update Terraform to use backup region
   cd terraform/environments/gcp-prod
   sed -i 's/region = "us-central1"/region = "us-east1"/g' terraform.tfvars
   terraform apply
   ```

2. **Restore database** from backup:
   ```bash
   # Clone from latest backup
   gcloud sql instances clone mcp-prod-postgres mcp-prod-postgres-dr \
     --region=us-east1 \
     --project=PROJECT_ID
   ```

3. **Deploy application**:
   ```bash
   kubectl apply -k deployments/overlays/production-gke
   ```

**RTO** (Recovery Time Objective): 45-60 minutes
**RPO** (Recovery Point Objective): Up to 7 days (PITR window)

---

## Monitoring & Alerts

### View Active Alerts

```bash
# List firing alerts
gcloud alpha monitoring policies list \
  --filter="enabled=true" \
  --project=PROJECT_ID

# Get alert details
gcloud alpha monitoring policies describe POLICY_ID \
  --project=PROJECT_ID
```

### Create Custom Alert

```bash
# High error rate alert
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --project=PROJECT_ID
```

### View Metrics

```bash
# CPU usage
gcloud monitoring time-series list \
  --filter='metric.type="kubernetes.io/container/cpu/core_usage_time" AND resource.labels.namespace_name="mcp-production"' \
  --project=PROJECT_ID

# Memory usage
gcloud monitoring time-series list \
  --filter='metric.type="kubernetes.io/container/memory/used_bytes" AND resource.labels.namespace_name="mcp-production"' \
  --project=PROJECT_ID
```

---

## Maintenance Windows

### Cluster Upgrade

**GKE Autopilot** upgrades automatically based on release channel (STABLE).

**Check upgrade status**:
```bash
gcloud container clusters describe production-mcp-server-langgraph-gke \
  --region=us-central1 \
  --format="yaml(currentMasterVersion,releaseChannel)"
```

**Manual upgrade** (if needed):
```bash
# Check available versions
gcloud container get-server-config --region=us-central1

# Upgrade cluster
gcloud container clusters upgrade production-mcp-server-langgraph-gke \
  --region=us-central1 \
  --cluster-version=VERSION \
  --project=PROJECT_ID
```

### Database Maintenance

**Scheduled maintenance** happens during maintenance window (Sunday 3 AM UTC).

**Reschedule maintenance**:
```bash
gcloud sql instances patch mcp-prod-postgres \
  --maintenance-window-day=1 \
  --maintenance-window-hour=3 \
  --project=PROJECT_ID
```

**Defer maintenance** (one time):
```bash
gcloud sql instances reschedule-maintenance mcp-prod-postgres \
  --reschedule-type=NEXT_AVAILABLE_WINDOW \
  --project=PROJECT_ID
```

---

## Common Tasks

### View Application Logs

```bash
# Real-time logs
kubectl logs -f -n mcp-production -l app=mcp-server-langgraph --max-log-requests=10

# Cloud Logging (last hour)
gcloud logging read \
  'resource.type="k8s_container" AND resource.labels.namespace_name="mcp-production"' \
  --limit=100 \
  --format=json \
  --project=PROJECT_ID

# Specific pod
kubectl logs POD_NAME -n mcp-production -c mcp-server-langgraph
```

### Update Configuration

```bash
# Edit ConfigMap
kubectl edit configmap production-mcp-server-langgraph-config -n mcp-production

# Restart to pick up changes (Reloader does this automatically)
kubectl rollout restart deployment/production-mcp-server-langgraph -n mcp-production
```

### Connect to Database

```bash
# Via Cloud SQL Proxy
cloud-sql-proxy PROJECT_ID:us-central1:mcp-prod-postgres &
psql "host=localhost port=5432 user=postgres dbname=mcp_langgraph"

# Or via kubectl port-forward
kubectl port-forward -n mcp-production svc/production-mcp-server-langgraph 5432:5432 &
psql "host=localhost port=5432 user=postgres dbname=mcp_langgraph"
```

### Export Metrics

```bash
# Export to JSON for analysis
gcloud monitoring time-series list \
  --filter='resource.type="k8s_container"' \
  --format=json \
  --project=PROJECT_ID > metrics-$(date +%Y%m%d).json
```

---

## Contacts & Escalation

**On-Call Rotation**: (Configure in PagerDuty/Opsgenie)

**Escalation Path**:
1. **P0/P1**: On-call engineer (immediate)
2. **P2**: Engineering team lead (within 4 hours)
3. **P3**: Ticket for next sprint

**Communication Channels**:
- **Slack**: #production-incidents
- **Email**: platform-team@company.com
- **PagerDuty**: (Configure alert integration)

---

**End of Runbooks**

**Related Documents**:
- [Deployment Guide](./GKE_DEPLOYMENT_GUIDE.md)
- [GKE Best Practices](../archive/best-practices/GCP_GKE_BEST_PRACTICES_SUMMARY.md)
- [Cost Optimization](../archive/best-practices/GCP_COST_OPTIMIZATION_PLAYBOOK.md)
