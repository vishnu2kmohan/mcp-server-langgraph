# Cloud DNS Module for Staging Environment

This Terraform module creates a private Cloud DNS zone and DNS records for staging environment services (Cloud SQL and Memorystore Redis).

## Features

- Creates private DNS zone `staging.internal`
- Configures DNS records for:
  - Cloud SQL PostgreSQL: `cloudsql-staging.internal`
  - Memorystore Redis: `redis-staging.internal`
  - Redis Session Store: `redis-session-staging.internal`
- Optional CNAME for postgres alias
- Network-scoped visibility (private to specified VPC)

## Usage

### Basic Usage

```hcl
module "staging_dns" {
  source = "./modules/cloud-dns-staging"

  gcp_project_id                 = "your-project-id"
  vpc_network_self_link          = "projects/your-project-id/global/networks/default"
  cloud_sql_private_ip           = "10.110.0.3"
  memorystore_redis_host         = "10.110.1.4"
  memorystore_redis_session_host = "10.138.129.37"
}
```

### With Data Sources (Recommended)

```hcl
# Automatically fetch IPs from existing resources
data "google_sql_database_instance" "staging_postgres" {
  project = var.gcp_project_id
  name    = "staging-postgres"
}

data "google_redis_instance" "staging_redis" {
  project = var.gcp_project_id
  name    = "staging-redis"
  region  = var.gcp_region
}

data "google_redis_instance" "staging_redis_session" {
  project = var.gcp_project_id
  name    = "staging-redis-session"
  region  = var.gcp_region
}

module "staging_dns" {
  source = "./modules/cloud-dns-staging"

  gcp_project_id                 = var.gcp_project_id
  vpc_network_self_link          = "projects/${var.gcp_project_id}/global/networks/default"
  cloud_sql_private_ip           = data.google_sql_database_instance.staging_postgres.private_ip_address
  memorystore_redis_host         = data.google_redis_instance.staging_redis.host
  memorystore_redis_session_host = data.google_redis_instance.staging_redis_session.host
  create_postgres_cname          = true
}
```

## Inputs

| Name | Description | Type | Required | Default |
|------|-------------|------|----------|---------|
| `gcp_project_id` | GCP Project ID | `string` | Yes | - |
| `vpc_network_self_link` | VPC network self-link | `string` | No | `projects/PROJECT_ID/global/networks/default` |
| `cloud_sql_private_ip` | Cloud SQL private IP | `string` | Yes | - |
| `memorystore_redis_host` | Primary Redis IP | `string` | Yes | - |
| `memorystore_redis_session_host` | Session Redis IP | `string` | Yes | - |
| `create_postgres_cname` | Create postgres CNAME | `bool` | No | `false` |
| `dns_ttl` | DNS record TTL (seconds) | `number` | No | `300` |

## Outputs

| Name | Description |
|------|-------------|
| `dns_zone_name` | Name of the DNS managed zone |
| `dns_zone_dns_name` | DNS name of the zone |
| `cloudsql_dns_name` | DNS name for Cloud SQL |
| `redis_dns_name` | DNS name for Redis |
| `redis_session_dns_name` | DNS name for Redis session |
| `verification_command` | kubectl command to verify DNS |

## Prerequisites

1. **GCP Project** with required APIs enabled:
   ```bash
   gcloud services enable dns.googleapis.com \
     --project=YOUR_PROJECT_ID
   ```

2. **Existing Resources**:
   - Cloud SQL instance with private IP
   - Memorystore Redis instances
   - VPC network configured

3. **Terraform Permissions**:
   - `roles/dns.admin` or equivalent
   - `roles/compute.networkViewer` (to read VPC)

## Deployment

### Initialize and Plan

```bash
cd terraform/environments/staging
terraform init
terraform plan \
  -var="gcp_project_id=your-project-id" \
  -var="cloud_sql_private_ip=10.110.0.3" \
  -var="memorystore_redis_host=10.110.1.4" \
  -var="memorystore_redis_session_host=10.138.129.37"
```

### Apply

```bash
terraform apply \
  -var="gcp_project_id=your-project-id" \
  -var="cloud_sql_private_ip=10.110.0.3" \
  -var="memorystore_redis_host=10.110.1.4" \
  -var="memorystore_redis_session_host=10.138.129.37"
```

### Verify

```bash
# Check DNS zone created
gcloud dns managed-zones describe staging-internal \
  --project=your-project-id

# Check DNS records
gcloud dns record-sets list \
  --zone=staging-internal \
  --project=your-project-id

# Test DNS resolution from GKE cluster (use output command)
terraform output -raw verification_command | bash
```

## Integration with Kubernetes

After creating DNS records, deploy to GKE:

```bash
kubectl apply -k ../../deployments/overlays/staging-gke
```

The deployment will use DNS names configured in:
- `deployments/overlays/staging-gke/configmap-patch.yaml`
- `deployments/overlays/staging-gke/redis-session-service-patch.yaml`

## Failover Handling

When Cloud SQL or Memorystore fails over to a new IP:

### Option 1: Terraform Update (Recommended)

```bash
# Terraform will detect the IP change via data sources
terraform plan
terraform apply  # Updates DNS records automatically
```

### Option 2: Manual Update

```bash
# Update DNS record with new IP
gcloud dns record-sets update cloudsql-staging.internal. \
  --zone=staging-internal \
  --type=A \
  --ttl=300 \
  --rrdatas=NEW_IP \
  --project=your-project-id

# Wait for TTL (5 minutes) or restart pods
kubectl rollout restart deployment/staging-mcp-server-langgraph \
  -n staging-mcp-server-langgraph
```

## Cost Considerations

- **Cloud DNS Zone**: $0.20/month per zone
- **DNS Queries**: $0.40 per million queries
- **Typical Cost**: ~$1-2/month for staging environment

## Troubleshooting

### DNS not resolving

1. Check zone is attached to VPC:
   ```bash
   gcloud dns managed-zones describe staging-internal \
     --project=your-project-id \
     --format="value(privateVisibilityConfig.networks)"
   ```

2. Verify DNS record exists:
   ```bash
   gcloud dns record-sets describe cloudsql-staging.internal. \
     --zone=staging-internal \
     --type=A \
     --project=your-project-id
   ```

3. Test from within GKE:
   ```bash
   kubectl run -it --rm dns-test \
     --image=gcr.io/google.com/cloudsdktool/cloud-sdk:slim \
     --restart=Never \
     -- nslookup cloudsql-staging.internal
   ```

### Connection still using old IP

1. Check DNS cache TTL hasn't expired (wait 5 minutes)
2. Restart pods to flush connection pools:
   ```bash
   kubectl rollout restart deployment/staging-mcp-server-langgraph \
     -n staging-mcp-server-langgraph
   ```

## Security

- Private zone only (not exposed to internet)
- Network-scoped visibility (VPC-specific)
- Follows least-privilege IAM principles
- TTL optimized for failover speed (5 minutes)

## References

- [Cloud DNS Overview](https://cloud.google.com/dns/docs/overview)
- [Private Zones](https://cloud.google.com/dns/docs/zones#create-private-zone)
- [Cloud SQL Private IP](https://cloud.google.com/sql/docs/postgres/private-ip)
- [Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis)
