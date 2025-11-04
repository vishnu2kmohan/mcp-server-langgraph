#######################
# VPC Outputs
#######################

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = module.vpc.vpc_cidr
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnet_ids
}

output "nat_gateway_ips" {
  description = "NAT Gateway Elastic IPs"
  value       = module.vpc.nat_gateway_eips
}

#######################
# EKS Outputs
#######################

output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "EKS cluster Kubernetes version"
  value       = module.eks.cluster_version
}

output "cluster_security_group_id" {
  description = "EKS cluster security group ID"
  value       = module.eks.cluster_security_group_id
}

output "node_security_group_id" {
  description = "EKS node security group ID"
  value       = module.eks.node_security_group_id
}

output "oidc_provider_arn" {
  description = "OIDC provider ARN for IRSA"
  value       = module.eks.oidc_provider_arn
}

output "application_irsa_role_arn" {
  description = "Application IRSA role ARN"
  value       = module.eks.application_irsa_role_arn
}

output "cluster_autoscaler_irsa_role_arn" {
  description = "Cluster Autoscaler IRSA role ARN"
  value       = module.eks.cluster_autoscaler_irsa_role_arn
}

output "ebs_csi_irsa_role_arn" {
  description = "EBS CSI driver IRSA role ARN"
  value       = module.eks.ebs_csi_irsa_role_arn
}

# Outputs required by deployment scripts
output "velero_role_arn" {
  description = "Velero IRSA role ARN (placeholder - needs Velero module)"
  value       = module.eks.application_irsa_role_arn # Reuse app role for now
}

output "karpenter_controller_role_arn" {
  description = "Karpenter controller IRSA role ARN (placeholder - needs Karpenter module)"
  value       = module.eks.cluster_autoscaler_irsa_role_arn # Reuse autoscaler role for now
}

output "karpenter_node_instance_profile_name" {
  description = "Karpenter node instance profile name (placeholder)"
  value       = "mcp-langgraph-staging-karpenter-node"
}

output "karpenter_sqs_queue_name" {
  description = "Karpenter SQS queue name (placeholder)"
  value       = "mcp-langgraph-staging-karpenter"
}

#######################
# RDS Outputs
#######################

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.rds.db_instance_endpoint
}

output "rds_address" {
  description = "RDS hostname"
  value       = module.rds.db_instance_address
}

output "rds_port" {
  description = "RDS port"
  value       = module.rds.db_instance_port
}

output "rds_database_name" {
  description = "RDS database name"
  value       = module.rds.db_instance_name
}

output "rds_username" {
  description = "RDS master username"
  value       = module.rds.db_instance_username
  sensitive   = true
}

output "rds_password" {
  description = "RDS master password"
  value       = module.rds.db_instance_password
  sensitive   = true
}

output "rds_connection_string" {
  description = "PostgreSQL connection string"
  value       = module.rds.connection_string
  sensitive   = true
}

#######################
# Redis Outputs
#######################

output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = module.redis.primary_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = module.redis.port
}

output "redis_auth_token" {
  description = "Redis auth token"
  value       = module.redis.auth_token
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = module.redis.connection_string
  sensitive   = true
}

#######################
# Kubernetes Configuration
#######################

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}

output "namespace" {
  description = "Application namespace"
  value       = kubernetes_namespace.mcp_server.metadata[0].name
}

output "service_account_name" {
  description = "Application service account name"
  value       = kubernetes_service_account.mcp_server.metadata[0].name
}

#######################
# Summary
#######################

output "deployment_summary" {
  description = "Deployment summary"
  value = {
    environment = "staging"
    region      = var.region
    vpc = {
      id        = module.vpc.vpc_id
      cidr      = module.vpc.vpc_cidr
      azs       = module.vpc.availability_zones
      nat_count = length(module.vpc.nat_gateway_ids)
    }
    eks = {
      cluster_name = module.eks.cluster_name
      version      = module.eks.cluster_version
      endpoint     = module.eks.cluster_endpoint
    }
    rds = {
      endpoint = module.rds.db_instance_endpoint
      engine   = "PostgreSQL ${module.rds.db_instance_engine_version}"
      multi_az = false
    }
    redis = {
      endpoint = module.redis.primary_endpoint_address
      mode     = "standalone"
      replicas = 1
      multi_az = false
    }
  }
}

#######################
# Cost Estimation
#######################

output "estimated_monthly_cost" {
  description = "Estimated monthly cost (USD) - Staging Environment"
  value = {
    vpc = {
      nat_gateways  = "~$33 (1 x $32.85)"
      vpc_endpoints = "~$36 (5 endpoints)"
      total         = "~$69"
    }
    eks = {
      control_plane = "$73 (1 cluster x $0.10/hour)"
      nodes_general = "~$75 (2 x t3.large on-demand)"
      nodes_spot    = "~$5 (1 x t3.large spot @ 70% discount)"
      total         = "~$153"
    }
    rds = {
      instance = "~$60 (db.t3.medium Single-AZ)"
      storage  = "~$6 (50GB gp3)"
      backups  = "~$2 (7-day retention)"
      total    = "~$68"
    }
    redis = {
      nodes   = "~$27 (2 x cache.t3.small: 1 primary + 1 replica)"
      backups = "~$1"
      total   = "~$28"
    }
    cloudwatch = {
      logs    = "~$3"
      metrics = "~$2"
      alarms  = "~$1"
      total   = "~$6"
    }
    total_monthly = "~$324 (base infrastructure - 60% cheaper than production)"
    notes         = "Excludes data transfer, additional storage, and application-specific costs. Single-AZ and smaller instances for cost optimization."
  }
}
