# VPC Module

Creates a production-ready, multi-AZ VPC optimized for Amazon EKS with public and private subnets, NAT gateways, VPC endpoints, and flow logs.

## Features

- **Multi-AZ Design**: Spans 3 availability zones by default for high availability
- **Public Subnets**: For load balancers and NAT gateways (/20 networks, 4096 IPs each)
- **Private Subnets**: For EKS nodes and data services (/18 networks, 16384 IPs each)
- **NAT Gateways**: One per AZ for high availability (configurable to single NAT for cost savings)
- **VPC Endpoints**: Interface endpoints for ECR, CloudWatch, EC2, STS; Gateway endpoint for S3
- **VPC Flow Logs**: Enabled by default with CloudWatch Logs integration
- **EKS-Ready**: Proper subnet tagging for EKS load balancer discovery
- **Security**: Private DNS enabled for VPC endpoints, security groups, flow logs

## Usage

### Production Configuration (Multi-NAT Gateway)

```hcl
module "vpc" {
  source = "../../modules/vpc"

  name_prefix              = "mcp-langgraph-prod"
  vpc_cidr                 = "10.0.0.0/16"
  region                   = "us-east-1"
  availability_zones_count = 3
  cluster_name             = "mcp-server-langgraph-prod"

  # High availability - NAT gateway per AZ
  single_nat_gateway = false

  # Cost optimization with VPC endpoints
  enable_vpc_endpoints = true

  # Security and compliance
  enable_flow_logs           = true
  flow_logs_retention_days   = 30
  flow_logs_traffic_type     = "ALL"

  tags = {
    Environment = "production"
    Team        = "platform"
    CostCenter  = "engineering"
  }
}
```

### Development/Staging Configuration (Single NAT Gateway)

```hcl
module "vpc" {
  source = "../../modules/vpc"

  name_prefix              = "mcp-langgraph-dev"
  vpc_cidr                 = "10.1.0.0/16"
  region                   = "us-east-1"
  availability_zones_count = 2
  cluster_name             = "mcp-server-langgraph-dev"

  # Cost savings - single NAT gateway
  single_nat_gateway = true

  # Disable VPC endpoints for dev
  enable_vpc_endpoints = false

  # Reduced flow log retention
  enable_flow_logs         = true
  flow_logs_retention_days = 7

  tags = {
    Environment = "development"
    Team        = "platform"
  }
}
```

## Subnet Sizing

For a `/16` VPC (65,536 IPs):

| Subnet Type | CIDR Mask | IPs per Subnet | Total IPs | Use Case |
|-------------|-----------|----------------|-----------|----------|
| Public      | /20       | 4,096          | 12,288 (3 AZs) | ALB, NAT gateways |
| Private     | /18       | 16,384         | 49,152 (3 AZs) | EKS nodes, RDS, ElastiCache |

This allocation supports:
- **EKS Nodes**: Up to ~300 nodes per AZ with /24 pod CIDRs
- **Pods**: AWS VPC CNI supports up to 110 pods per node
- **Growth**: Ample IP space for future expansion

## VPC Endpoints

The module creates the following VPC endpoints when `enable_vpc_endpoints = true`:

### Gateway Endpoints (No Additional Cost)
- **S3**: For ECR image layers, backups, Terraform state

### Interface Endpoints ($0.01/hour + data transfer)
- **ECR API**: For Docker image manifest operations
- **ECR DKR**: For Docker image pull/push
- **CloudWatch Logs**: For application and system logging
- **EC2**: For EKS cluster management
- **STS**: For IRSA (IAM Roles for Service Accounts)

**Cost Savings**: Eliminates NAT gateway data transfer charges for AWS service traffic (~$0.045/GB)

## VPC Flow Logs

Captures network traffic metadata for security analysis and troubleshooting:

```
${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status} ${vpc-id} ${subnet-id} ${instance-id} ${tcp-flags} ${type} ${pkt-srcaddr} ${pkt-dstaddr} ${region} ${az-id}
```

Query flow logs using CloudWatch Logs Insights:

```sql
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
| filter action = "REJECT"
| stats count() by srcAddr
| sort count desc
| limit 20
```

## EKS Subnet Tagging

The module automatically tags subnets for EKS load balancer discovery:

**Public Subnets** (for internet-facing ALBs):
```hcl
"kubernetes.io/role/elb" = "1"
"kubernetes.io/cluster/${cluster_name}" = "shared"
```

**Private Subnets** (for internal NLBs):
```hcl
"kubernetes.io/role/internal-elb" = "1"
"kubernetes.io/cluster/${cluster_name}" = "shared"
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Region (us-east-1)                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    VPC (10.0.0.0/16)                       │  │
│  │                                                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │   AZ-1a     │  │   AZ-1b     │  │   AZ-1c     │       │  │
│  │  ├─────────────┤  ├─────────────┤  ├─────────────┤       │  │
│  │  │ Public      │  │ Public      │  │ Public      │       │  │
│  │  │ 10.0.0.0/20 │  │ 10.0.16.0/20│  │ 10.0.32.0/20│       │  │
│  │  │ - ALB       │  │ - ALB       │  │ - ALB       │       │  │
│  │  │ - NAT GW    │  │ - NAT GW    │  │ - NAT GW    │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  │         │                 │                 │             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │ Private     │  │ Private     │  │ Private     │       │  │
│  │  │ 10.0.64.0/18│  │ 10.0.128.0/ │  │ 10.0.192.0/ │       │  │
│  │  │             │  │       18    │  │       18    │       │  │
│  │  │ - EKS Nodes │  │ - EKS Nodes │  │ - EKS Nodes │       │  │
│  │  │ - RDS       │  │ - RDS       │  │ - ElastiCache│      │  │
│  │  │ - Redis     │  │             │  │             │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  │                                                             │  │
│  │  VPC Endpoints: S3, ECR, CloudWatch, EC2, STS             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| name_prefix | Prefix for resource names | string | - | yes |
| vpc_cidr | CIDR block for VPC | string | "10.0.0.0/16" | no |
| region | AWS region | string | - | yes |
| availability_zones_count | Number of AZs to use | number | 3 | no |
| cluster_name | EKS cluster name for tagging | string | - | yes |
| single_nat_gateway | Use single NAT gateway | bool | false | no |
| enable_vpc_endpoints | Enable VPC endpoints | bool | true | no |
| enable_flow_logs | Enable VPC Flow Logs | bool | true | no |
| flow_logs_retention_days | Flow logs retention period | number | 30 | no |
| flow_logs_traffic_type | Traffic type to capture | string | "ALL" | no |
| tags | Additional tags | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| vpc_id | VPC ID |
| vpc_cidr | VPC CIDR block |
| public_subnet_ids | Public subnet IDs |
| private_subnet_ids | Private subnet IDs |
| nat_gateway_ids | NAT gateway IDs |
| nat_gateway_eips | NAT gateway elastic IPs |
| availability_zones | Availability zones used |
| vpc_endpoint_s3_id | S3 VPC endpoint ID |
| flow_logs_log_group_name | Flow logs CloudWatch group |

## Cost Estimation

### Production (3 AZs, Multi-NAT)
- **VPC**: Free
- **NAT Gateways**: 3 × $0.045/hour × 730 hours = **$98.55/month**
- **NAT Data Transfer**: ~$0.045/GB (variable)
- **VPC Endpoints**: 5 × $0.01/hour × 730 hours = **$36.50/month**
- **VPC Endpoint Data**: ~$0.01/GB (variable)
- **CloudWatch Logs**: ~$0.50/GB ingested, $0.03/GB stored
- **Total (Fixed)**: **~$135/month** + data transfer

### Development (2 AZs, Single-NAT)
- **NAT Gateway**: 1 × $0.045/hour × 730 hours = **$32.85/month**
- **No VPC Endpoints**: $0
- **Total (Fixed)**: **~$33/month** + data transfer

**Cost Optimization**:
- VPC endpoints save ~70% on NAT data transfer for AWS service traffic
- Single NAT gateway saves ~$66/month but loses AZ redundancy

## Security Considerations

1. **Network Isolation**: Private subnets have no direct internet access
2. **Least Privilege**: Security groups on VPC endpoints restrict access to VPC CIDR only
3. **Encryption**: Flow logs can be encrypted with KMS
4. **Monitoring**: Flow logs capture all network traffic for security analysis
5. **Compliance**: Suitable for PCI-DSS, HIPAA, SOC 2 workloads

## Testing

```bash
# Format check
terraform fmt -check

# Validation
terraform init -backend=false
terraform validate

# Security scan
tfsec .
checkov -d .

# Integration test
cd ../../tests/vpc
terraform init
terraform plan
```

## Examples

See [examples/vpc](../../examples/vpc/) for:
- Minimal VPC (development)
- Full VPC (production)
- VPC with custom CIDR ranges
- VPC with KMS-encrypted flow logs

## References

- [AWS VPC Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-best-practices.html)
- [EKS VPC Requirements](https://docs.aws.amazon.com/eks/latest/userguide/network_reqs.html)
- [VPC Endpoint Pricing](https://aws.amazon.com/privatelink/pricing/)
- [NAT Gateway Pricing](https://aws.amazon.com/vpc/pricing/)
