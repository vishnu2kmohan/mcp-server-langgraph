# AWS EKS Kubernetes Overlay

This overlay configures the MCP Server LangGraph for deployment on Amazon EKS with AWS-native integrations.

## Features

- **IRSA Integration**: Service accounts annotated for IAM Roles for Service Accounts
- **AWS Secrets Manager**: External Secrets Operator integration for RDS and ElastiCache credentials
- **RDS PostgreSQL**: Managed database connection via AWS Secrets Manager
- **ElastiCache Redis**: Managed cache connection with optional authentication
- **AWS X-Ray**: Distributed tracing integration
- **CloudWatch**: Logs and metrics export via OpenTelemetry
- **ECR**: Container images from Amazon ECR

## Prerequisites

1. **EKS Cluster** deployed via Terraform (see `terraform/environments/aws-*`)
2. **External Secrets Operator** installed in the cluster
3. **AWS Load Balancer Controller** (optional, for ingress)
4. **Secrets in AWS Secrets Manager**:
   - `mcp-langgraph/ENVIRONMENT/rds` - RDS credentials
   - `mcp-langgraph/ENVIRONMENT/redis` - Redis credentials

## Deployment

### 1. Customize for Your Environment

Edit `kustomization.yaml` and replace:
- `ACCOUNT_ID` - Your AWS account ID
- `REGION` - Your AWS region (e.g., `us-east-1`)
- `ENVIRONMENT` - Environment name (`dev`, `staging`, `prod`)

### 2. Deploy with Kustomize

```bash
# Deploy to EKS cluster
kubectl apply -k deployments/kubernetes/overlays/aws/

# Verify deployment
kubectl get pods -n mcp-server-langgraph
kubectl get externalsecrets -n mcp-server-langgraph
```

### 3. Verify IRSA Configuration

```bash
# Check service account annotations
kubectl describe sa mcp-server-langgraph -n mcp-server-langgraph

# Verify pod has AWS credentials
kubectl exec -it <pod-name> -n mcp-server-langgraph -- env | grep AWS
```

## Configuration Files

| File | Purpose |
|------|---------|
| `kustomization.yaml` | Main Kustomize configuration |
| `serviceaccount-patch.yaml` | IRSA annotations for service accounts |
| `deployment-patch.yaml` | AWS-specific environment variables and secrets |
| `external-secrets.yaml` | External Secrets Operator resources |
| `otel-collector-config.yaml` | OpenTelemetry configuration for AWS |

## Environment Variables

The deployment is configured with these AWS-specific environment variables:

- `AWS_REGION` - AWS region
- `CLOUD_PROVIDER` - Set to `aws`
- `POSTGRES_*` - RDS connection details (from Secrets Manager)
- `REDIS_*` - ElastiCache connection details (from Secrets Manager)
- `AWS_XRAY_DAEMON_ADDRESS` - X-Ray daemon endpoint

## IAM Roles Required

### Application Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:mcp-langgraph/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    }
  ]
}
```

### External Secrets Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecrets"
      ],
      "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT_ID:secret:mcp-langgraph/*"
    }
  ]
}
```

## Monitoring

### CloudWatch Logs
Logs are exported to CloudWatch Logs:
- Log Group: `/aws/eks/mcp-server-langgraph`
- Log Stream: `{service.name}/{pod_name}`

### CloudWatch Metrics
Metrics are exported as EMF (Embedded Metric Format):
- Namespace: `MCPServer/EKS`
- Log Group: `/aws/eks/mcp-server-langgraph/metrics`

### X-Ray Traces
Distributed traces are sent to AWS X-Ray for analysis.

## Cost Optimization

For development and staging environments:
- Use smaller RDS instance classes (db.t3.micro, db.t3.small)
- Single-AZ deployments
- Reduce backup retention periods
- Use spot instances for non-critical workloads
- Consider pausing/stopping resources when not in use

## Troubleshooting

### Pods not getting secrets
```bash
# Check External Secrets status
kubectl get externalsecrets -n mcp-server-langgraph
kubectl describe externalsecret postgres-credentials -n mcp-server-langgraph

# Check IAM role assumption
kubectl logs <pod-name> -n mcp-server-langgraph | grep -i iam
```

### IRSA not working
```bash
# Verify service account annotation
kubectl get sa mcp-server-langgraph -n mcp-server-langgraph -o yaml

# Check pod environment
kubectl exec <pod-name> -n mcp-server-langgraph -- env | grep AWS

# Verify OIDC provider
aws eks describe-cluster --name <cluster-name> --query "cluster.identity.oidc.issuer"
```

### Can't connect to RDS/Redis
```bash
# Check security groups allow EKS nodes
aws ec2 describe-security-groups --group-ids <rds-sg-id>

# Test connectivity from pod
kubectl exec -it <pod-name> -n mcp-server-langgraph -- nc -zv <rds-endpoint> 5432
kubectl exec -it <pod-name> -n mcp-server-langgraph -- nc -zv <redis-endpoint> 6379
```

## Additional Resources

- [Terraform Environments](../../../../terraform/environments/)
- [EKS Deployment Script](../../../../scripts/deploy-aws-eks.sh)
- [EKS Documentation](../../../../docs/deployment/kubernetes/eks.mdx)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [External Secrets Operator](https://external-secrets.io/latest/)
