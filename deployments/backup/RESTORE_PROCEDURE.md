# Velero Disaster Recovery Procedure

## Prerequisites

- Velero CLI installed (`velero version`)
- kubectl access to the cluster
- Backup name or schedule information

## Quick Reference

```bash
# List all backups
velero backup get

# Describe a specific backup
velero backup describe <backup-name> --details

# Check backup logs
velero backup logs <backup-name>

# Create an on-demand backup
velero backup create <backup-name> --include-namespaces mcp-server-langgraph
```

---

## Disaster Recovery Scenarios

### Scenario 1: Restore Entire Namespace

**When to use**: Complete namespace deletion or corruption

```bash
# Step 1: List available backups
velero backup get

# Step 2: Restore from backup
velero restore create --from-backup <backup-name>

# Step 3: Monitor restore progress
velero restore describe <restore-name>

# Step 4: Check restore logs
velero restore logs <restore-name>

# Step 5: Verify pods are running
kubectl get pods -n mcp-server-langgraph
```

### Scenario 2: Restore Specific Resources

**When to use**: Accidental deletion of specific resources (ConfigMap, Secret, Deployment)

```bash
# Restore only deployments
velero restore create --from-backup <backup-name> \
  --include-resources deployments

# Restore only secrets and configmaps
velero restore create --from-backup <backup-name> \
  --include-resources secrets,configmaps

# Restore specific resources by label
velero restore create --from-backup <backup-name> \
  --selector app=mcp-server-langgraph
```

### Scenario 3: Restore to Different Namespace

**When to use**: Testing restore or creating a staging environment

```bash
# Restore to a different namespace
velero restore create --from-backup <backup-name> \
  --namespace-mappings mcp-server-langgraph:mcp-server-langgraph-restore

# Verify in new namespace
kubectl get all -n mcp-server-langgraph-restore
```

### Scenario 4: Cross-Cluster Restore

**When to use**: Disaster recovery to a different cluster

```bash
# On NEW cluster:

# Step 1: Install Velero with same storage location
helm install velero vmware-tanzu/velero \
  --namespace velero \
  --create-namespace \
  --values deployments/backup/velero-values-<cloud>.yaml

# Step 2: Verify backup is accessible
velero backup get

# Step 3: Perform restore
velero restore create --from-backup <backup-name>

# Step 4: Update DNS/Ingress to point to new cluster
```

### Scenario 5: Partial Restore (Exclude Resources)

**When to use**: Restore everything except specific resources

```bash
# Restore but exclude PVCs (use existing volumes)
velero restore create --from-backup <backup-name> \
  --exclude-resources persistentvolumeclaims,persistentvolumes

# Restore but exclude services (keep existing)
velero restore create --from-backup <backup-name> \
  --exclude-resources services
```

---

## PostgreSQL Database Restore

### Option 1: Restore from Velero Backup (includes PVC)

```bash
# Full restore including PostgreSQL PVC
velero restore create --from-backup <backup-name> \
  --include-namespaces mcp-server-langgraph \
  --include-resources persistentvolumeclaims,persistentvolumes

# Wait for PostgreSQL pod to start
kubectl wait --for=condition=ready pod -l app=postgres -n mcp-server-langgraph --timeout=300s
```

### Option 2: Restore from pg_dump Hook

If using pre/post backup hooks (see backup-schedule.yaml):

```bash
# Step 1: Access PostgreSQL pod
kubectl exec -it postgres-0 -n mcp-server-langgraph -- bash

# Step 2: Restore from dump
PGPASSWORD=$POSTGRES_PASSWORD pg_restore -U postgres -d postgres -c /tmp/backup.dump

# Step 3: Verify data
PGPASSWORD=$POSTGRES_PASSWORD psql -U postgres -c "SELECT COUNT(*) FROM <table>;"
```

### Option 3: Point-in-Time Recovery (Cloud-Managed Databases)

For CloudSQL/RDS/Azure Database (if using external databases):

**AWS RDS**:
```bash
# Restore to specific timestamp
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier mcp-prod-postgres \
  --target-db-instance-identifier mcp-prod-postgres-restored \
  --restore-time 2025-01-15T14:30:00Z
```

**GCP CloudSQL**:
```bash
gcloud sql backups restore <backup-id> \
  --backup-instance=<source-instance> \
  --backup-instance=<target-instance>
```

**Azure Database**:
```bash
az postgres flexible-server restore \
  --resource-group <rg> \
  --name <new-server> \
  --source-server <source-server> \
  --restore-time "2025-01-15T14:30:00Z"
```

---

## Verification Checklist

After restore, verify:

- [ ] All pods are running: `kubectl get pods -n mcp-server-langgraph`
- [ ] Services are accessible: `kubectl get svc -n mcp-server-langgraph`
- [ ] Persistent volumes are bound: `kubectl get pvc -n mcp-server-langgraph`
- [ ] ConfigMaps and Secrets exist: `kubectl get cm,secret -n mcp-server-langgraph`
- [ ] Database connectivity: `kubectl exec -it <app-pod> -- curl postgres:5432`
- [ ] Application health: `kubectl exec -it <app-pod> -- curl localhost:8000/health`
- [ ] Check logs: `kubectl logs -n mcp-server-langgraph -l app=mcp-server-langgraph --tail=50`

---

## Automated Restore Testing

Test restore procedure monthly:

```bash
#!/bin/bash
# automated-restore-test.sh

set -e

BACKUP_NAME=$(velero backup get -o json | jq -r '.items[0].metadata.name')
TEST_NAMESPACE="mcp-server-langgraph-test"

echo "Testing restore from backup: $BACKUP_NAME"

# Create test restore
velero restore create test-restore-$(date +%Y%m%d) \
  --from-backup $BACKUP_NAME \
  --namespace-mappings mcp-server-langgraph:$TEST_NAMESPACE

# Wait for restore to complete
velero restore wait test-restore-$(date +%Y%m%d)

# Verify pods are running
kubectl wait --for=condition=ready pod -l app=mcp-server-langgraph \
  -n $TEST_NAMESPACE --timeout=300s

# Clean up
kubectl delete namespace $TEST_NAMESPACE

echo "✅ Restore test successful"
```

---

## Troubleshooting

### Restore stuck in "InProgress"

```bash
# Check restore logs
velero restore logs <restore-name>

# Check for errors
kubectl get restore <restore-name> -n velero -o yaml

# Common fix: Delete and retry
velero restore delete <restore-name>
velero restore create --from-backup <backup-name>
```

### Persistent Volumes not binding

```bash
# Check PV/PVC status
kubectl get pv,pvc -n mcp-server-langgraph

# Delete and let Velero recreate
kubectl delete pvc <pvc-name> -n mcp-server-langgraph
velero restore create --from-backup <backup-name> \
  --include-resources persistentvolumeclaims
```

### Pod stuck in Init state

```bash
# Check events
kubectl describe pod <pod-name> -n mcp-server-langgraph

# Common causes:
# - Secrets/ConfigMaps not restored
# - PVCs not bound
# - Image pull errors

# Restore secrets and configmaps first
velero restore create --from-backup <backup-name> \
  --include-resources secrets,configmaps
```

---

## Emergency Contacts

- **On-call Engineer**: Slack #ops-oncall
- **Velero Documentation**: https://velero.io/docs/
- **Backup Storage**:
  - AWS S3: s3://mcp-server-backups
  - GCP GCS: gs://mcp-server-backups
  - Azure Blob: https://<storage-account>.blob.core.windows.net/mcp-server-backups

---

## RTO/RPO SLAs

- **Recovery Time Objective (RTO)**: 1 hour
- **Recovery Point Objective (RPO)**: 24 hours (daily backups)
- **Backup Retention**:
  - Daily: 30 days
  - Weekly: 90 days
  - Monthly: 365 days
