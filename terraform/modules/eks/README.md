# EKS Cluster Module

Production-ready Amazon EKS cluster with managed node groups, IRSA (IAM Roles for Service Accounts), essential addons, and comprehensive security controls.

## Features

- **Managed EKS Cluster**: Fully managed Kubernetes control plane (v1.27+)
- **Multi-AZ Node Groups**: 3 node group types (general, compute, spot)
- **IRSA Support**: Complete IAM integration with service accounts
- **Essential Addons**: VPC CNI, CoreDNS, kube-proxy, EBS CSI driver
- **Security**: Encrypted secrets, control plane logging, security groups
- **Observability**: CloudWatch logs with configurable retention
- **Auto-scaling Ready**: Cluster Autoscaler IRSA role included
- **Cost Optimization**: Spot instances support for fault-tolerant workloads

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     EKS Control Plane                        │
│  - Kubernetes API Server (Multi-AZ)                         │
│  - etcd (Encrypted with KMS)                                │
│  - Control plane logging → CloudWatch                        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼─────────┐
│ General Nodes  │  │ Compute Nodes  │  │  Spot Nodes    │
│ (t3.large)     │  │ (c6i.2xlarge)  │  │ (mixed types)  │
│ ON_DEMAND      │  │ ON_DEMAND      │  │ SPOT           │
│ 2-10 nodes     │  │ 0-20 nodes     │  │ 0-20 nodes     │
└────────────────┘  └────────────────┘  └────────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                ┌───────────▼──────────┐
                │  VPC CNI (AWS CNI)   │
                │  - Native VPC IPs    │
                │  - Security groups   │
                │  - Network policies  │
                └──────────────────────┘
```

## Usage

### Basic Production Cluster

```hcl
module "eks" {
  source = "../../modules/eks"

  cluster_name       = "mcp-server-langgraph-prod"
  kubernetes_version = "1.28"
  region             = "us-east-1"

  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  public_subnet_ids   = module.vpc.public_subnet_ids

  # Control plane configuration
  cluster_endpoint_private_access = true
  cluster_endpoint_public_access  = true
  cluster_enabled_log_types       = ["api", "audit", "authenticator"]

  # General node group (for application workloads)
  enable_general_node_group       = true
  general_node_group_desired_size = 3
  general_node_group_min_size     = 2
  general_node_group_max_size     = 10
  general_node_group_instance_types = ["t3.large"]

  # Enable EBS CSI driver for persistent storage
  enable_ebs_csi_driver = true

  # IRSA for application
  create_application_irsa_role = true
  application_service_account_name      = "mcp-server-langgraph"
  application_service_account_namespace = "mcp-server-langgraph"

  tags = {
    Environment = "production"
    Team        = "platform"
  }
}
```

### Advanced Multi-Node-Group Configuration

```hcl
module "eks" {
  source = "../../modules/eks"

  cluster_name       = "mcp-server-langgraph-prod"
  kubernetes_version = "1.28"
  region             = "us-east-1"

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids

  # General-purpose nodes
  enable_general_node_group       = true
  general_node_group_desired_size = 3
  general_node_group_min_size     = 2
  general_node_group_max_size     = 10
  general_node_group_instance_types = ["t3.xlarge", "t3a.xlarge"]
  general_node_group_labels = {
    workload = "general"
  }

  # Compute-optimized nodes (for LLM processing)
  enable_compute_node_group       = true
  compute_node_group_desired_size = 2
  compute_node_group_min_size     = 0
  compute_node_group_max_size     = 20
  compute_node_group_instance_types = ["c6i.4xlarge", "c6a.4xlarge"]
  compute_node_group_labels = {
    workload = "llm-processing"
  }
  compute_node_group_taints = [
    {
      key    = "workload"
      value  = "llm"
      effect = "NoSchedule"
    }
  ]

  # Spot instances (for development/testing)
  enable_spot_node_group       = true
  spot_node_group_desired_size = 2
  spot_node_group_min_size     = 0
  spot_node_group_max_size     = 10
  spot_node_group_instance_types = [
    "t3.large", "t3a.large",
    "t3.xlarge", "t3a.xlarge"
  ]

  # Enable all addons
  enable_ebs_csi_driver          = true
  enable_cluster_autoscaler_irsa = true

  # Application IRSA with specific permissions
  create_application_irsa_role = true
  application_secrets_arns = [
    "arn:aws:secretsmanager:us-east-1:123456789012:secret:mcp-langgraph/*"
  ]
  application_kms_key_arns = [
    "arn:aws:kms:us-east-1:123456789012:key/*"
  ]
  enable_xray = true

  tags = {
    Environment = "production"
    Compliance  = "soc2"
  }
}
```

### Development/Staging Configuration

```hcl
module "eks" {
  source = "../../modules/eks"

  cluster_name       = "mcp-server-langgraph-dev"
  kubernetes_version = "1.28"
  region             = "us-east-1"

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  # Public endpoint only for dev
  cluster_endpoint_private_access = false
  cluster_endpoint_public_access  = true

  # Reduced logging
  cluster_enabled_log_types  = ["api", "audit"]
  cluster_log_retention_days = 7

  # Smaller node group
  enable_general_node_group       = true
  general_node_group_desired_size = 2
  general_node_group_min_size     = 1
  general_node_group_max_size     = 5
  general_node_group_instance_types = ["t3.medium"]

  # Use spot instances to save costs
  enable_spot_node_group       = true
  spot_node_group_desired_size = 2

  enable_ebs_csi_driver = true

  tags = {
    Environment = "development"
  }
}
```

## Node Group Strategies

### General-Purpose Nodes
- **Use case**: API servers, web apps, general workloads
- **Instance types**: t3.large, t3.xlarge (burstable)
- **Capacity**: ON_DEMAND for reliability
- **Cost**: ~$0.0832/hour per t3.large

### Compute-Optimized Nodes
- **Use case**: LLM inference, batch processing, high-CPU workloads
- **Instance types**: c6i.2xlarge, c6i.4xlarge
- **Capacity**: ON_DEMAND or SPOT
- **Cost**: ~$0.34/hour per c6i.2xlarge

### Spot Nodes
- **Use case**: Fault-tolerant workloads, dev/test
- **Instance types**: Mixed (t3/t3a families) for diversity
- **Capacity**: SPOT (can save 70-90%)
- **Cost**: ~$0.025/hour per t3.large spot
- **Auto-tainted**: `spot=true:NoSchedule`

## IRSA (IAM Roles for Service Accounts)

The module creates the following IRSA roles:

### 1. VPC CNI Role
Automatically configured for AWS VPC CNI addon.

### 2. EBS CSI Driver Role
For persistent volume provisioning:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ebs-csi-controller-sa
  namespace: kube-system
  annotations:
    eks.amazonaws.com/role-arn: <ebs_csi_irsa_role_arn>
```

### 3. Cluster Autoscaler Role
For automatic node scaling:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cluster-autoscaler
  namespace: kube-system
  annotations:
    eks.amazonaws.com/role-arn: <cluster_autoscaler_irsa_role_arn>
```

### 4. Application Role
For your application pods:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mcp-server-langgraph
  namespace: mcp-server-langgraph
  annotations:
    eks.amazonaws.com/role-arn: <application_irsa_role_arn>
```

**Permissions granted**:
- AWS Secrets Manager read access
- CloudWatch Logs write access
- X-Ray trace publishing (if enabled)
- KMS decrypt for secrets

## EKS Addons

### VPC CNI (Amazon VPC CNI)
- **Version**: Auto-updated to latest compatible
- **IRSA**: Enabled
- **Configuration**: Uses AWS VPC IPs for pods
- **Network policies**: Supported via security groups

### CoreDNS
- **Version**: Auto-updated
- **Purpose**: Kubernetes DNS resolution
- **HA**: Runs on multiple nodes

### kube-proxy
- **Version**: Auto-updated
- **Purpose**: Network proxy for services
- **Mode**: iptables

### EBS CSI Driver (Optional, Default: Enabled)
- **Version**: Latest compatible
- **IRSA**: Enabled
- **Purpose**: Dynamic EBS volume provisioning
- **Storage classes**: gp3, io2, st1, sc1

## Security Features

### 1. Control Plane
- ✅ Secrets encrypted with KMS (automatic key rotation)
- ✅ Control plane logging to CloudWatch
- ✅ Private endpoint support
- ✅ Public endpoint CIDR restrictions

### 2. Data Plane
- ✅ Nodes in private subnets
- ✅ Security groups with least-privilege rules
- ✅ SSM access for debugging (optional)
- ✅ IMDSv2 enforced

### 3. IAM
- ✅ IRSA for all service accounts
- ✅ Least-privilege policies
- ✅ No long-lived credentials

### 4. Network
- ✅ Node-to-node encryption via VPC CNI
- ✅ Security group per node group
- ✅ Cluster security group for control plane

## Accessing the Cluster

### Update kubeconfig

```bash
aws eks update-kubeconfig --region us-east-1 --name mcp-server-langgraph-prod

# Verify access
kubectl get nodes
kubectl get pods -A
```

### Using with Terraform

```hcl
# Get kubeconfig command from output
output "configure_kubectl" {
  value = module.eks.kubeconfig_command
}
```

## Cluster Autoscaler Setup

After deploying the cluster, install Cluster Autoscaler:

```bash
# Download manifest
curl -o cluster-autoscaler-autodiscover.yaml \
  https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml

# Edit: Set cluster name and image version
kubectl apply -f cluster-autoscaler-autodiscover.yaml

# Annotate service account with IRSA role
kubectl annotate serviceaccount cluster-autoscaler \
  -n kube-system \
  eks.amazonaws.com/role-arn=<cluster_autoscaler_irsa_role_arn>
```

Or use Helm:

```bash
helm repo add autoscaler https://kubernetes.github.io/autoscaler
helm install cluster-autoscaler autoscaler/cluster-autoscaler \
  --namespace kube-system \
  --set autoDiscovery.clusterName=mcp-server-langgraph-prod \
  --set awsRegion=us-east-1 \
  --set rbac.serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=<role_arn>
```

## Monitoring

### CloudWatch Container Insights

```bash
# Install CloudWatch agent
curl https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml | sed "s/{{cluster_name}}/mcp-server-langgraph-prod/;s/{{region_name}}/us-east-1/" | kubectl apply -f -
```

### Control Plane Logs

View in CloudWatch Logs:
- Log group: `/aws/eks/mcp-server-langgraph-prod/cluster`
- Streams: `api`, `audit`, `authenticator`, `controllerManager`, `scheduler`

Query example:
```
fields @timestamp, @message
| filter @logStream like /api/
| filter @message like /error/
| sort @timestamp desc
| limit 100
```

## Cost Optimization

### Development Environment
- Use spot instances for non-critical workloads
- Single node group with t3.medium
- Reduced log retention (7 days)
- Estimated: ~$150-250/month

### Production Environment
- Mix of on-demand (critical) and spot (batch)
- Auto-scaling to match demand
- Reserved instances for baseline capacity
- Estimated: ~$800-1500/month

### Savings Strategies
1. **Spot instances**: Save 70-90% on compute
2. **Cluster Autoscaler**: Scale down during off-hours
3. **Karpenter**: More efficient bin-packing
4. **Reserved/Savings Plans**: 30-40% off on-demand pricing

## Troubleshooting

### Nodes not joining cluster

```bash
# Check node IAM role
aws eks describe-nodegroup --cluster-name <cluster> --nodegroup-name <nodegroup>

# Check security groups
aws eks describe-cluster --name <cluster> --query cluster.resourcesVpcConfig.clusterSecurityGroupId

# View node logs
kubectl logs -n kube-system -l k8s-app=aws-node
```

### IRSA not working

```bash
# Verify OIDC provider
aws eks describe-cluster --name <cluster> --query cluster.identity.oidc.issuer

# Check service account annotation
kubectl get sa <sa-name> -n <namespace> -o yaml

# Test from pod
kubectl run test --image=amazon/aws-cli --rm -it -- sts get-caller-identity
```

### EBS CSI driver issues

```bash
# Check addon status
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver

# View logs
kubectl logs -n kube-system -l app=ebs-csi-controller

# Verify IRSA
kubectl describe sa ebs-csi-controller-sa -n kube-system
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| cluster_name | EKS cluster name | string | - | yes |
| kubernetes_version | Kubernetes version | string | "1.28" | no |
| vpc_id | VPC ID | string | - | yes |
| private_subnet_ids | Private subnet IDs (≥2) | list(string) | - | yes |
| enable_general_node_group | Enable general node group | bool | true | no |
| general_node_group_instance_types | Instance types for general nodes | list(string) | ["t3.large"] | no |
| enable_ebs_csi_driver | Enable EBS CSI driver | bool | true | no |
| create_application_irsa_role | Create app IRSA role | bool | true | no |

See [variables.tf](./variables.tf) for complete list.

## Outputs

| Name | Description |
|------|-------------|
| cluster_endpoint | EKS cluster API endpoint |
| cluster_name | EKS cluster name |
| oidc_provider_arn | OIDC provider ARN for IRSA |
| application_irsa_role_arn | App IRSA role ARN |
| kubeconfig_command | Command to configure kubectl |

See [outputs.tf](./outputs.tf) for complete list.

## Examples

See the usage examples in this README for production, development, and multi-node-group configurations.

## References

- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/)
- [IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [EBS CSI Driver](https://github.com/kubernetes-sigs/aws-ebs-csi-driver)
