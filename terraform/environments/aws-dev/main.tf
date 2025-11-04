# Development Environment - MCP Server LangGraph
# Minimal cost AWS EKS infrastructure for development and testing

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }

  # Backend configuration is provided via -backend-config flag
  # See terraform/backend-configs/README.md for setup instructions
  # Example: terraform init -backend-config=../../backend-configs/aws-dev.s3.tfbackend
  backend "s3" {}
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Environment = "development"
      Project     = "mcp-server-langgraph"
      ManagedBy   = "Terraform"
      Team        = "platform"
      CostCenter  = "engineering"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name_prefix  = "mcp-langgraph-dev"
  cluster_name = "${local.name_prefix}-eks"

  common_tags = {
    Environment = "development"
    Project     = "mcp-server-langgraph"
  }
}

#######################
# VPC
#######################

module "vpc" {
  source = "../../modules/vpc"

  name_prefix              = local.name_prefix
  vpc_cidr                 = var.vpc_cidr
  region                   = var.region
  availability_zones_count = 2  # Only 2 AZs for dev

  cluster_name             = local.cluster_name

  # Dev: Single NAT gateway for cost savings
  single_nat_gateway   = true
  enable_vpc_endpoints = false  # Disabled to save costs
  enable_flow_logs     = false  # Disabled for dev

  tags = local.common_tags
}

#######################
# EKS Cluster
#######################

module "eks" {
  source = "../../modules/eks"

  cluster_name       = local.cluster_name
  kubernetes_version = var.kubernetes_version
  region             = var.region

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  public_subnet_ids  = module.vpc.public_subnet_ids

  # Control plane configuration
  cluster_endpoint_private_access      = true
  cluster_endpoint_public_access       = var.cluster_endpoint_public_access
  cluster_endpoint_public_access_cidrs = var.cluster_endpoint_public_access_cidrs
  cluster_enabled_log_types            = ["api"] # Minimal logging for dev
  cluster_log_retention_days           = 1

  # General-purpose node group (minimal for dev)
  enable_general_node_group        = true
  general_node_group_desired_size  = 1
  general_node_group_min_size      = 1
  general_node_group_max_size      = 3
  general_node_group_instance_types = var.general_node_instance_types
  general_node_group_disk_size     = 30

  # No compute-optimized nodes in dev
  enable_compute_node_group = false

  # Spot instances (primary for dev to save costs)
  enable_spot_node_group        = var.enable_spot_nodes
  spot_node_group_desired_size  = 1
  spot_node_group_min_size      = 0
  spot_node_group_max_size      = 2
  spot_node_group_instance_types = [
    "t3.medium", "t3a.medium",
    "t3.large", "t3a.large"
  ]

  # Addons
  enable_ebs_csi_driver          = true
  enable_cluster_autoscaler_irsa = false # Disabled for dev

  # IRSA for application
  create_application_irsa_role          = true
  application_service_account_name      = "mcp-server-langgraph"
  application_service_account_namespace = "mcp-server-langgraph"
  application_secrets_arns = [
    "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:mcp-langgraph-dev/*"
  ]
  enable_xray = false # Disabled for dev

  tags = local.common_tags

  depends_on = [module.vpc]
}

#######################
# RDS PostgreSQL
#######################

module "rds" {
  source = "../../modules/rds"

  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  subnet_ids  = module.vpc.private_subnet_ids

  # Database configuration (minimal for dev)
  engine_version    = var.postgres_engine_version
  instance_class    = var.postgres_instance_class
  allocated_storage = var.postgres_allocated_storage
  max_allocated_storage = var.postgres_max_allocated_storage
  storage_type      = "gp3"

  database_name   = var.postgres_database_name
  master_username = var.postgres_master_username
  # master_password is auto-generated if not provided

  # Dev: Single-AZ for cost savings
  multi_az = false

  # Backup configuration (minimal)
  backup_retention_period = 1
  skip_final_snapshot     = true
  deletion_protection     = false

  # Monitoring (disabled for dev)
  enable_enhanced_monitoring    = false
  enable_performance_insights   = false
  enable_slow_query_log         = false

  # Security
  allowed_security_group_ids = [module.eks.node_security_group_id]
  enable_iam_database_authentication = false # Disabled for dev simplicity

  # CloudWatch alarms (disabled for dev)
  create_cloudwatch_alarms = false

  tags = local.common_tags

  depends_on = [module.vpc]
}

#######################
# ElastiCache Redis
#######################

module "redis" {
  source = "../../modules/elasticache"

  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  subnet_ids  = module.vpc.private_subnet_ids

  # Cluster configuration (minimal for dev)
  cluster_mode_enabled    = false
  node_type               = var.redis_node_type
  num_node_groups         = 1
  replicas_per_node_group = 0  # No replicas for dev

  engine_version = var.redis_engine_version

  # Dev: No HA
  multi_az_enabled           = false
  automatic_failover_enabled = false

  # Encryption (disabled for dev simplicity)
  at_rest_encryption_enabled = false
  transit_encryption_enabled = false

  # Backup (disabled for dev)
  enable_snapshot          = false
  snapshot_retention_limit = 0
  enable_final_snapshot    = false

  # Monitoring
  enable_slow_log = false
  log_retention_days = 1

  # Security
  allowed_security_group_ids = [module.eks.node_security_group_id]

  # CloudWatch alarms (disabled for dev)
  create_cloudwatch_alarms = false

  tags = local.common_tags

  depends_on = [module.vpc]
}

#######################
# Kubernetes Provider
#######################

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args = [
      "eks",
      "get-token",
      "--cluster-name",
      module.eks.cluster_name,
      "--region",
      var.region
    ]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args = [
        "eks",
        "get-token",
        "--cluster-name",
        module.eks.cluster_name,
        "--region",
        var.region
      ]
    }
  }
}

#######################
# Kubernetes Namespace
#######################

resource "kubernetes_namespace" "mcp_server" {
  metadata {
    name = "mcp-server-langgraph"

    labels = {
      name                                  = "mcp-server-langgraph"
      "pod-security.kubernetes.io/enforce" = "baseline" # Relaxed for dev
      "pod-security.kubernetes.io/audit"   = "restricted"
      "pod-security.kubernetes.io/warn"    = "restricted"
    }
  }

  depends_on = [module.eks]
}

#######################
# Service Account
#######################

resource "kubernetes_service_account" "mcp_server" {
  metadata {
    name      = "mcp-server-langgraph"
    namespace = kubernetes_namespace.mcp_server.metadata[0].name

    annotations = {
      "eks.amazonaws.com/role-arn" = module.eks.application_irsa_role_arn
    }
  }

  depends_on = [module.eks]
}

#######################
# Kubernetes Secrets
#######################

resource "kubernetes_secret" "postgres" {
  metadata {
    name      = "postgres-credentials"
    namespace = kubernetes_namespace.mcp_server.metadata[0].name
  }

  data = module.rds.kubernetes_secret_data

  type = "Opaque"

  depends_on = [module.rds]
}

resource "kubernetes_secret" "redis" {
  metadata {
    name      = "redis-credentials"
    namespace = kubernetes_namespace.mcp_server.metadata[0].name
  }

  data = module.redis.kubernetes_secret_data

  type = "Opaque"

  depends_on = [module.redis]
}
