# Cloud DNS Setup for Staging GKE Overlay

This document explains how to configure Cloud DNS records for the staging environment to enable robust failover support for Cloud SQL and Memorystore Redis.

## Why Cloud DNS?

Using Cloud DNS instead of hard-coded IPs provides several benefits:

- **Failover resilience**: IP addresses can change during regional failover or instance recreation
- **Environment portability**: Same manifests work across different projects/regions
- **Centralized management**: DNS records managed separately from Kubernetes configs
- **No deployment updates**: DNS changes don't require redeploying the application

## Required DNS Records

Configure the following **Cloud DNS Private Zones** in your GCP project:

### 1. Cloud SQL PostgreSQL

**DNS Record:**
```
Name:  cloudsql-staging.internal
Type:  A
TTL:   300
Data:  <YOUR_CLOUD_SQL_PRIVATE_IP>
```

**Find your Cloud SQL private IP:**
```bash
gcloud sql instances describe preview-postgres \
  --format='get(ipAddresses[0].ipAddress)' \
  --project=YOUR_PROJECT_ID
```

### 2. Memorystore Redis (Primary)

**DNS Record:**
```
Name:  redis-staging.internal
Type:  A
TTL:   300
Data:  <YOUR_MEMORYSTORE_REDIS_IP>
```

**Find your Memorystore Redis IP:**
```bash
gcloud redis instances describe preview-redis \
  --region=us-central1 \
  --format='get(host)' \
  --project=YOUR_PROJECT_ID
```

### 3. Memorystore Redis (Session Store)

**DNS Record:**
```
Name:  redis-session-staging.internal
Type:  A
TTL:   300
Data:  <YOUR_MEMORYSTORE_REDIS_SESSION_IP>
```

**Find your session Redis IP:**
```bash
gcloud redis instances describe preview-redis-session \
  --region=us-central1 \
  --format='get(host)' \
  --project=YOUR_PROJECT_ID
```

## Setup Instructions

### Option 1: Using gcloud CLI

1. **Create a private DNS zone** (if not already exists):
```bash
gcloud dns managed-zones create preview-internal \
  --description="Private DNS for staging environment" \
  --dns-name="staging.internal" \
  --networks="default" \
  --visibility="private" \
  --project=YOUR_PROJECT_ID
```

2. **Add DNS records** for each service:

```bash
# Cloud SQL
gcloud dns record-sets create cloudsql-staging.internal. \
  --zone="preview-internal" \
  --type="A" \
  --ttl="300" \
  --rrdatas="<CLOUD_SQL_IP>" \
  --project=YOUR_PROJECT_ID

# Memorystore Redis
gcloud dns record-sets create redis-staging.internal. \
  --zone="preview-internal" \
  --type="A" \
  --ttl="300" \
  --rrdatas="<REDIS_IP>" \
  --project=YOUR_PROJECT_ID

# Redis Session Store
gcloud dns record-sets create redis-session-staging.internal. \
  --zone="preview-internal" \
  --type="A" \
  --ttl="300" \
  --rrdatas="<REDIS_SESSION_IP>" \
  --project=YOUR_PROJECT_ID
```

### Option 2: Using Terraform

```hcl
resource "google_dns_managed_zone" "staging_internal" {
  name        = "preview-internal"
  dns_name    = "staging.internal."
  description = "Private DNS for staging environment"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = google_compute_network.default.id
    }
  }
}

resource "google_dns_record_set" "cloudsql_staging" {
  name         = "cloudsql-staging.internal."
  managed_zone = google_dns_managed_zone.staging_internal.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_sql_database_instance.staging_postgres.private_ip_address]
}

resource "google_dns_record_set" "redis_staging" {
  name         = "redis-staging.internal."
  managed_zone = google_dns_managed_zone.staging_internal.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_redis_instance.staging_redis.host]
}

resource "google_dns_record_set" "redis_session_staging" {
  name         = "redis-session-staging.internal."
  managed_zone = google_dns_managed_zone.staging_internal.name
  type         = "A"
  ttl          = 300
  rrdatas      = [google_redis_instance.staging_redis_session.host]
}
```

### Option 3: Using Google Cloud Console

1. Go to [Cloud DNS](https://console.cloud.google.com/net-services/dns/zones)
2. Click **Create Zone**
   - Zone type: **Private**
   - Zone name: `preview-internal`
   - DNS name: `staging.internal`
   - Networks: Select your VPC (e.g., `default`)
3. Click **Create**
4. Add each DNS record:
   - Click **Add Record Set**
   - Resource record type: **A**
   - IPv4 Address: Enter the IP from the commands above
   - TTL: 300 seconds

## Verification

After creating the DNS records, verify they resolve correctly from within your GKE cluster:

```bash
# Test from a pod in the cluster
kubectl run -it --rm dns-test --image=gcr.io/google.com/cloudsdktool/cloud-sdk:slim --restart=Never -- bash

# Inside the pod:
nslookup cloudsql-staging.internal
nslookup redis-staging.internal
nslookup redis-session-staging.internal

# Should return the IPs you configured
```

## Updating IPs After Failover

If Cloud SQL or Memorystore fails over to a new IP:

1. Update the DNS record with the new IP:
```bash
gcloud dns record-sets update cloudsql-staging.internal. \
  --zone="preview-internal" \
  --type="A" \
  --ttl="300" \
  --rrdatas="<NEW_IP>" \
  --project=YOUR_PROJECT_ID
```

2. Wait for TTL expiration (5 minutes) or restart pods:
```bash
kubectl rollout restart deployment/mcp-server-langgraph -n preview-mcp-server-langgraph
```

## Troubleshooting

### DNS not resolving

1. **Check zone visibility**: Ensure the DNS zone is attached to your VPC network
```bash
gcloud dns managed-zones describe preview-internal --project=YOUR_PROJECT_ID
```

2. **Check network policy**: Ensure GKE nodes can access Cloud DNS (port 53 UDP/TCP)

3. **Check DNS record**: Verify the record exists
```bash
gcloud dns record-sets list --zone="preview-internal" --project=YOUR_PROJECT_ID
```

### Connection failures

1. **Verify firewall rules**: Ensure GKE nodes can reach Cloud SQL/Redis IPs
2. **Check service account permissions**: Ensure the GKE service account has access
3. **Verify the actual IP**: Get the current IP and update DNS if needed

## Migration from Hard-coded IPs

If you previously used hard-coded IPs (10.110.0.3, 10.110.1.4, etc.), the migration process is:

1. **Create DNS records** pointing to the current IPs (no changes yet)
2. **Verify DNS resolution** from pods (see Verification section)
3. **Deploy the updated manifests** (this update) which use DNS names
4. **Monitor logs** for any connection issues
5. **Future IP changes**: Just update DNS, no manifest changes needed

## References

- [Cloud DNS Overview](https://cloud.google.com/dns/docs/overview)
- [Private Zones](https://cloud.google.com/dns/docs/zones#create-private-zone)
- [Cloud SQL Private IP](https://cloud.google.com/sql/docs/postgres/private-ip)
- [Memorystore for Redis](https://cloud.google.com/memorystore/docs/redis)
