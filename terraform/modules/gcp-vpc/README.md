# GCP VPC Terraform Module

This Terraform module creates a production-ready VPC network optimized for GKE (Google Kubernetes Engine) workloads with comprehensive networking, security, and observability features.

## Features

### Core Networking
- **Global VPC** with custom regional subnets
- **Multi-region support** with configurable routing mode
- **Secondary IP ranges** for GKE pods and services (VPC-native networking)
- **Optional public and management subnets**
- **Cloud NAT** for secure outbound internet access
- **Cloud Router** with BGP support

### Security
- **Private Google Access** enabled on all subnets
- **Firewall rules** for internal communication, health checks, and IAP SSH
- **Cloud Armor** integration for DDoS protection (optional)
- **Custom firewall rules** support
- **Private Service Connection** for Cloud SQL, Memorystore, etc.

### Observability
- **VPC Flow Logs** with configurable sampling and aggregation
- **Cloud NAT logging** for debugging and auditing
- **Customizable log retention** and filtering

### Cost Optimization
- **Dynamic port allocation** for Cloud NAT (reduces NAT IP costs)
- **Configurable NAT IP allocation** (AUTO or MANUAL)
- **Flow log sampling** to reduce logging costs
- **Regional routing mode** option (lower data transfer costs)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          VPC (Global)                           │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Nodes Subnet (Regional)                                  │ │
│  │  - Primary: 10.0.0.0/20 (4096 IPs)                        │ │
│  │  - Secondary (Pods): 10.4.0.0/14 (262k IPs)               │ │
│  │  - Secondary (Services): 10.8.0.0/20 (4096 IPs)           │ │
│  │  - Private Google Access: Enabled                         │ │
│  │  - VPC Flow Logs: Enabled                                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                   │
│  │ Public Subnet    │  │ Management       │                   │
│  │ (Optional)       │  │ Subnet (Optional)│                   │
│  │ 10.1.0.0/24      │  │ 10.2.0.0/24      │                   │
│  └──────────────────┘  └──────────────────┘                   │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Cloud NAT                                                │ │
│  │  - Auto/Manual IP allocation                              │ │
│  │  - Dynamic port allocation                                │ │
│  │  - Logging: ERRORS_ONLY                                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Private Service Connection                               │ │
│  │  - For Cloud SQL, Memorystore, etc.                       │ │
│  │  - /16 IP range by default                                │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Firewall Rules                                           │ │
│  │  - Allow internal (TCP/UDP/ICMP)                          │ │
│  │  - Allow IAP SSH (35.235.240.0/20)                        │ │
│  │  - Allow health checks (35.191.0.0/16, 130.211.0.0/22)    │ │
│  │  - Custom rules (configurable)                            │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Example

```hcl
module "vpc" {
  source = "./terraform/modules/gcp-vpc"

  project_id  = "my-gcp-project"
  name_prefix = "mcp-prod"
  region      = "us-central1"
  cluster_name = "mcp-gke-cluster"

  # Use default CIDR blocks
  nodes_cidr    = "10.0.0.0/20"
  pods_cidr     = "10.4.0.0/14"
  services_cidr = "10.8.0.0/20"
}
```

### Production Example with All Features

```hcl
module "vpc" {
  source = "./terraform/modules/gcp-vpc"

  # General
  project_id   = "my-gcp-project"
  name_prefix  = "mcp-prod"
  region       = "us-central1"
  cluster_name = "mcp-production-cluster"

  # VPC Configuration
  routing_mode = "REGIONAL"  # Or "GLOBAL" for multi-region

  # Subnet CIDRs
  nodes_cidr    = "10.0.0.0/20"   # 4096 IPs for nodes
  pods_cidr     = "10.4.0.0/14"   # 262k IPs for pods
  services_cidr = "10.8.0.0/20"   # 4096 IPs for services

  # Optional subnets
  create_public_subnet     = true
  public_cidr              = "10.1.0.0/24"
  create_management_subnet = true
  management_cidr          = "10.2.0.0/24"

  # Cloud NAT (Manual IPs for production)
  nat_ip_allocate_option        = "MANUAL_ONLY"
  nat_ip_count                  = 2  # Redundancy
  enable_dynamic_port_allocation = true
  nat_min_ports_per_vm          = 64
  nat_max_ports_per_vm          = 32768

  # NAT Logging
  enable_nat_logging = true
  nat_logging_filter = "ALL"  # or "ERRORS_ONLY" for production

  # VPC Flow Logs
  enable_flow_logs                 = true
  flow_logs_aggregation_interval   = "INTERVAL_5_SEC"
  flow_logs_sampling               = 0.1  # 10% sampling for cost savings
  flow_logs_metadata               = "INCLUDE_ALL_METADATA"

  # Firewall
  enable_iap_ssh            = true
  enable_deny_all_ingress   = false

  # Custom firewall rules
  custom_firewall_rules = {
    allow-https-from-lb = {
      description = "Allow HTTPS from load balancers"
      priority    = 1000
      direction   = "INGRESS"
      allow = [{
        protocol = "tcp"
        ports    = ["443"]
      }]
      source_ranges = ["0.0.0.0/0"]
      target_tags   = ["https-server"]
    }
  }

  # Private Service Connection
  enable_private_service_connection = true
  private_services_prefix_length    = 16  # /16 for Cloud SQL, Memorystore

  # Cloud Armor (DDoS protection)
  enable_cloud_armor                      = true
  cloud_armor_rate_limit_threshold        = 1000  # requests
  cloud_armor_rate_limit_interval         = 60    # per 60 seconds
  cloud_armor_ban_duration_sec            = 600   # 10 minutes
  enable_cloud_armor_adaptive_protection  = true

  # Labels
  labels = {
    environment = "production"
    managed_by  = "terraform"
    team        = "platform"
    cost_center = "engineering"
  }
}
```

### Development/Staging Example (Cost-Optimized)

```hcl
module "vpc" {
  source = "./terraform/modules/gcp-vpc"

  project_id   = "my-gcp-project"
  name_prefix  = "mcp-dev"
  region       = "us-central1"
  cluster_name = "mcp-dev-cluster"

  # Smaller CIDR blocks for dev
  nodes_cidr    = "10.10.0.0/22"  # 1024 IPs
  pods_cidr     = "10.12.0.0/16"  # 65k IPs
  services_cidr = "10.13.0.0/22"  # 1024 IPs

  # Cost savings
  nat_ip_allocate_option = "AUTO_ONLY"  # No static IPs needed
  enable_flow_logs       = true
  flow_logs_sampling     = 0.1          # 10% sampling
  enable_nat_logging     = true
  nat_logging_filter     = "ERRORS_ONLY"

  # Minimal setup
  create_public_subnet              = false
  create_management_subnet          = false
  enable_private_service_connection = true
  enable_cloud_armor                = false

  labels = {
    environment = "development"
    managed_by  = "terraform"
  }
}
```

### Using with GKE Module

```hcl
module "vpc" {
  source = "./terraform/modules/gcp-vpc"

  project_id   = var.project_id
  name_prefix  = var.name_prefix
  region       = var.region
  cluster_name = var.cluster_name

  # ... VPC configuration ...
}

module "gke" {
  source = "./terraform/modules/gke-autopilot"

  project_id   = var.project_id
  name_prefix  = var.name_prefix
  region       = var.region
  cluster_name = var.cluster_name

  # Use VPC outputs
  network_name        = module.vpc.network_name
  subnet_name         = module.vpc.nodes_subnet_name
  pods_range_name     = module.vpc.pods_range_name
  services_range_name = module.vpc.services_range_name

  # ... GKE configuration ...
}
```

## IP Address Planning

### Recommended CIDR Allocations

| Environment | Nodes       | Pods           | Services    | Total IPs |
|-------------|-------------|----------------|-------------|-----------|
| Development | /22 (1k)    | /16 (65k)      | /22 (1k)    | ~67k      |
| Staging     | /20 (4k)    | /15 (131k)     | /20 (4k)    | ~139k     |
| Production  | /18 (16k)   | /14 (262k)     | /20 (4k)    | ~282k     |

### CIDR Block Considerations

**Nodes Subnet:**
- Small: `/22` = 1024 IPs (~200 nodes)
- Medium: `/20` = 4096 IPs (~800 nodes)
- Large: `/18` = 16384 IPs (~3000 nodes)

**Pods Subnet (Secondary Range):**
- GKE allocates /24 per node (256 IPs)
- Small cluster: `/16` = 65k IPs (~256 nodes × 256 pods/node)
- Medium cluster: `/15` = 131k IPs (~512 nodes)
- Large cluster: `/14` = 262k IPs (~1024 nodes)

**Services Subnet (Secondary Range):**
- One IP per Kubernetes Service
- Small: `/22` = 1024 services
- Medium: `/20` = 4096 services
- Large: `/18` = 16384 services

### Avoiding CIDR Conflicts

Ensure these ranges don't overlap:
1. **Nodes CIDR** (primary subnet range)
2. **Pods CIDR** (secondary range 1)
3. **Services CIDR** (secondary range 2)
4. **Public subnet** (if created)
5. **Management subnet** (if created)
6. **Private services** (allocated automatically, /16 by default)
7. **On-premises networks** (if using VPN/Interconnect)

## Firewall Rules

### Default Rules

The module creates these firewall rules by default:

1. **allow-internal**: Allows all TCP, UDP, ICMP between nodes, pods, and services
2. **allow-health-checks**: Allows health check probes from Google Cloud
3. **allow-iap-ssh** (optional): Allows SSH via Identity-Aware Proxy

### Custom Firewall Rules

Add custom rules via the `custom_firewall_rules` variable:

```hcl
custom_firewall_rules = {
  # Allow Redis access from GKE
  allow-redis = {
    description = "Allow Redis access from GKE pods"
    priority    = 1000
    direction   = "INGRESS"
    allow = [{
      protocol = "tcp"
      ports    = ["6379"]
    }]
    source_ranges = ["10.4.0.0/14"]  # Pods CIDR
    target_tags   = ["redis-server"]
  }

  # Allow PostgreSQL from GKE
  allow-postgres = {
    description = "Allow PostgreSQL from GKE"
    priority    = 1000
    direction   = "INGRESS"
    allow = [{
      protocol = "tcp"
      ports    = ["5432"]
    }]
    source_ranges = ["10.4.0.0/14"]
    target_tags   = ["postgres-server"]
  }

  # Deny specific traffic
  deny-sensitive-port = {
    description = "Block access to sensitive port"
    priority    = 900  # Lower number = higher priority
    direction   = "INGRESS"
    deny = [{
      protocol = "tcp"
      ports    = ["8080"]
    }]
    source_ranges = ["0.0.0.0/0"]
  }
}
```

## Cloud NAT Configuration

### Auto IP Allocation (Recommended for Dev/Staging)

```hcl
nat_ip_allocate_option = "AUTO_ONLY"
```

Pros:
- No manual IP management
- Automatic scaling

Cons:
- IPs can change
- Can't whitelist in external systems

### Manual IP Allocation (Recommended for Production)

```hcl
nat_ip_allocate_option = "MANUAL_ONLY"
nat_ip_count           = 2  # Number of static IPs
```

Pros:
- Static, predictable IPs
- Can whitelist in external systems
- Redundancy with multiple IPs

Cons:
- Additional cost (~$0.005/hour per IP)
- Manual management

### Port Allocation Strategies

**Dynamic Port Allocation** (Recommended):
```hcl
enable_dynamic_port_allocation = true
nat_min_ports_per_vm           = 64
nat_max_ports_per_vm           = 32768
```

- Allocates ports dynamically based on usage
- Reduces waste
- Supports more VMs per NAT IP

**Static Port Allocation**:
```hcl
enable_dynamic_port_allocation = false
nat_min_ports_per_vm           = 64
```

- Each VM gets exactly `nat_min_ports_per_vm` ports
- Simpler, but less efficient

### NAT IP Capacity

Each NAT IP supports:
- **64k total ports** (minus reserved ports)
- With `nat_min_ports_per_vm = 64`: ~1000 VMs per IP
- With `nat_min_ports_per_vm = 128`: ~500 VMs per IP

## Private Service Connection

Enables private connectivity to Google-managed services:

- **Cloud SQL** (PostgreSQL, MySQL)
- **Memorystore** (Redis, Memcached)
- **Filestore** (NFS)

```hcl
enable_private_service_connection = true
private_services_prefix_length    = 16  # /16 = 65k IPs
```

IP range is automatically allocated from RFC 1918 space.

**Access the services:**
```hcl
# Cloud SQL private IP will be in this range
# Example: 10.x.x.x (automatically assigned)
```

## VPC Flow Logs

### Configuration Options

```hcl
enable_flow_logs                 = true
flow_logs_aggregation_interval   = "INTERVAL_5_SEC"
flow_logs_sampling               = 0.5  # 50% of flows
flow_logs_metadata               = "INCLUDE_ALL_METADATA"
flow_logs_filter                 = ""   # Empty = log all
```

### Cost Optimization

Flow logs can be expensive at scale. Optimize by:

1. **Sampling**: Set to 0.1-0.5 (10-50%)
2. **Aggregation**: Use longer intervals (INTERVAL_10_MIN)
3. **Filtering**: Log only specific traffic

Example filter:
```hcl
flow_logs_filter = "inIpRange(dest_ip, '10.0.0.0/8') AND protocol != 1"  # Internal TCP/UDP only
```

### Viewing Flow Logs

```bash
# Query via Cloud Logging
gcloud logging read "resource.type=gce_subnetwork" --limit=50

# Or use Cloud Console:
# Logging > Logs Explorer > Resource: VPC Subnet
```

## Cloud Armor

Provides DDoS protection and WAF capabilities:

```hcl
enable_cloud_armor                      = true
cloud_armor_rate_limit_threshold        = 1000  # requests per interval
cloud_armor_rate_limit_interval         = 60    # seconds
cloud_armor_ban_duration_sec            = 600   # 10 minutes
enable_cloud_armor_adaptive_protection  = true  # ML-based protection
```

**Cost**: ~$6/month per policy + $0.75/million requests

Apply to load balancer backend service:
```hcl
resource "google_compute_backend_service" "default" {
  # ...
  security_policy = module.vpc.cloud_armor_policy_self_link
}
```

## Best Practices

### Security

1. **Enable Private Google Access** (default in this module)
   - Allows private access to Google APIs
   - No public IPs needed for Google service access

2. **Use IAP for SSH** instead of bastion hosts
   - Set `enable_iap_ssh = true`
   - Tag VMs with `iap-ssh`
   - Access via: `gcloud compute ssh VM_NAME --tunnel-through-iap`

3. **Enable VPC Flow Logs** for security auditing
   - Start with sampling = 0.1 (10%)
   - Increase for production debugging

4. **Use Private Service Connection** for databases
   - No public IPs for Cloud SQL/Memorystore
   - Traffic stays within Google network

5. **Implement defense in depth**:
   - Network policies (Kubernetes)
   - Firewall rules (VPC)
   - Cloud Armor (Application layer)

### Cost Optimization

1. **Regional routing** for single-region deployments
   ```hcl
   routing_mode = "REGIONAL"
   ```

2. **Auto NAT IPs** for dev/staging
   ```hcl
   nat_ip_allocate_option = "AUTO_ONLY"
   ```

3. **Flow log sampling** to reduce volume
   ```hcl
   flow_logs_sampling = 0.1  # 10%
   ```

4. **Dynamic port allocation** for NAT
   ```hcl
   enable_dynamic_port_allocation = true
   ```

5. **Right-size subnets** for your environment
   - Don't over-allocate IP space
   - Use smaller ranges for dev/staging

### High Availability

1. **Multi-zone subnets** (automatic in GCP)
   - Subnets are regional (span all zones)

2. **Multiple NAT IPs** for production
   ```hcl
   nat_ip_count = 2  # Redundancy
   ```

3. **Global routing** for multi-region
   ```hcl
   routing_mode = "GLOBAL"
   ```

## Troubleshooting

### Issue: Pods can't reach the internet

**Symptoms**: Pods can't pull images, can't reach external APIs

**Solution**:
1. Verify Cloud NAT is configured:
   ```bash
   gcloud compute routers nats list --router=ROUTER_NAME --region=REGION
   ```

2. Check NAT logs:
   ```bash
   gcloud logging read "resource.type=nat_gateway" --limit=50
   ```

3. Verify firewall rules allow egress:
   ```bash
   gcloud compute firewall-rules list --filter="direction=EGRESS"
   ```

### Issue: Can't connect to Cloud SQL private IP

**Symptoms**: Connection timeout to Cloud SQL private IP

**Solution**:
1. Verify private service connection:
   ```bash
   gcloud services vpc-peerings list --network=VPC_NAME
   ```

2. Check IP range allocation:
   ```bash
   gcloud compute addresses list --global --filter="purpose=VPC_PEERING"
   ```

3. Verify firewall allows traffic:
   ```bash
   gcloud compute firewall-rules list --filter="targetTags:cloudsql"
   ```

### Issue: VPC Flow Logs not appearing

**Symptoms**: No flow logs in Cloud Logging

**Solution**:
1. Verify flow logs are enabled on subnet:
   ```bash
   gcloud compute networks subnets describe SUBNET_NAME --region=REGION
   ```

2. Check if logs are being generated:
   ```bash
   gcloud logging read "resource.type=gce_subnetwork AND resource.labels.subnetwork_name=SUBNET_NAME" --limit=10
   ```

3. Increase sampling rate temporarily:
   ```hcl
   flow_logs_sampling = 1.0  # 100%
   ```

### Issue: CIDR exhaustion

**Symptoms**: Can't create more pods/nodes, "no available IP addresses"

**Solution**:
1. Check current usage:
   ```bash
   gcloud compute networks subnets describe SUBNET_NAME --region=REGION
   ```

2. Expand secondary ranges (if possible):
   ```bash
   gcloud compute networks subnets update SUBNET_NAME \
     --region=REGION \
     --add-secondary-ranges pods=NEW_LARGER_CIDR
   ```

3. Create new subnet with larger range (if expanding isn't possible)

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_id | GCP project ID | `string` | n/a | yes |
| name_prefix | Prefix for resource names | `string` | n/a | yes |
| region | GCP region | `string` | n/a | yes |
| cluster_name | GKE cluster name | `string` | n/a | yes |
| routing_mode | VPC routing mode (REGIONAL or GLOBAL) | `string` | `"REGIONAL"` | no |
| nodes_cidr | CIDR block for nodes subnet | `string` | `"10.0.0.0/20"` | no |
| pods_cidr | CIDR block for pods (secondary range) | `string` | `"10.4.0.0/14"` | no |
| services_cidr | CIDR block for services (secondary range) | `string` | `"10.8.0.0/20"` | no |
| create_public_subnet | Create public subnet | `bool` | `false` | no |
| create_management_subnet | Create management subnet | `bool` | `false` | no |
| enable_flow_logs | Enable VPC Flow Logs | `bool` | `true` | no |
| enable_private_service_connection | Enable private service connection | `bool` | `true` | no |
| enable_cloud_armor | Enable Cloud Armor security policy | `bool` | `false` | no |

See [variables.tf](./variables.tf) for complete list of inputs.

## Outputs

| Name | Description |
|------|-------------|
| network_id | ID of the VPC network |
| network_name | Name of the VPC network |
| nodes_subnet_name | Name of the nodes subnet |
| pods_cidr | CIDR block for pods |
| services_cidr | CIDR block for services |
| cloud_nat_id | ID of Cloud NAT |
| private_services_ip_range | IP range for private services |
| gke_network_config | Network config for GKE module |

See [outputs.tf](./outputs.tf) for complete list of outputs.

## Examples

See the [examples](../../environments/) directory for complete working examples:

- [GCP Development](../../environments/gcp-dev/)
- [GCP Staging](../../environments/gcp-staging/)
- [GCP Production](../../environments/gcp-prod/)

## License

This module is part of the MCP Server LangGraph project.

## Support

For issues or questions:
1. Check this README and troubleshooting section
2. Review [GCP VPC documentation](https://cloud.google.com/vpc/docs)
3. Open an issue in the repository
