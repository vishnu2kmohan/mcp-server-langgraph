# Production Environment - MCP Server LangGraph
# Complete AWS EKS infrastructure with RDS, ElastiCache, and supporting services

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

  backend "s3" {
    # Configure after running backend-setup
    # bucket         = "mcp-langgraph-terraform-state-us-east-1-ACCOUNT_ID"
    # key            = "environments/prod/terraform.tfstate"
    # region         = "us-east-1"
    # dynamodb_table = "mcp-langgraph-terraform-locks"
    # encrypt        = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Environment = "production"
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
  name_prefix  = "mcp-langgraph-prod"
  cluster_name = "${local.name_prefix}-eks"

  common_tags = {
    Environment = "production"
    Project     = "mcp-server-langgraph"
    Compliance  = "soc2"
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
  availability_zones_count = 3
  cluster_name             = local.cluster_name

  # Production: Multi-NAT gateway for HA
  single_nat_gateway   = false
  enable_vpc_endpoints = true
  enable_flow_logs     = true

  flow_logs_retention_days = 90
  flow_logs_traffic_type   = "ALL"

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
  cluster_enabled_log_types            = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  cluster_log_retention_days           = 90

  # General-purpose node group (for application workloads)
  enable_general_node_group        = true
  general_node_group_desired_size  = 3
  general_node_group_min_size      = 2
  general_node_group_max_size      = 10
  general_node_group_instance_types = var.general_node_instance_types
  general_node_group_disk_size     = 100

  # Compute-optimized node group (for LLM processing - optional)
  enable_compute_node_group        = var.enable_compute_nodes
  compute_node_group_desired_size  = 0
  compute_node_group_min_size      = 0
  compute_node_group_max_size      = 20
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

  # Spot instances (for fault-tolerant workloads)
  enable_spot_node_group        = var.enable_spot_nodes
  spot_node_group_desired_size  = 2
  spot_node_group_min_size      = 0
  spot_node_group_max_size      = 10
  spot_node_group_instance_types = [
    "t3.xlarge", "t3a.xlarge",
    "t3.2xlarge", "t3a.2xlarge"
  ]

  # Addons
  enable_ebs_csi_driver          = true
  enable_cluster_autoscaler_irsa = true

  # IRSA for application
  create_application_irsa_role          = true
  application_service_account_name      = "mcp-server-langgraph"
  application_service_account_namespace = "mcp-server-langgraph"
  application_secrets_arns = [
    "arn:aws:secretsmanager:${var.region}:${data.aws_caller_identity.current.account_id}:secret:mcp-langgraph/*"
  ]
  enable_xray = true

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

  # Database configuration
  engine_version    = var.postgres_engine_version
  instance_class    = var.postgres_instance_class
  allocated_storage = var.postgres_allocated_storage
  max_allocated_storage = var.postgres_max_allocated_storage
  storage_type      = "gp3"

  database_name   = var.postgres_database_name
  master_username = var.postgres_master_username
  # master_password is auto-generated if not provided

  # High availability
  multi_az = true

  # Backup configuration
  backup_retention_period = 30
  skip_final_snapshot     = false
  deletion_protection     = true

  # Monitoring
  enable_enhanced_monitoring    = true
  enable_performance_insights   = true
  enable_slow_query_log         = true
  slow_query_threshold_ms       = "1000"

  # Security
  allowed_security_group_ids = [module.eks.node_security_group_id]
  enable_iam_database_authentication = true

  # CloudWatch alarms
  create_cloudwatch_alarms = true
  alarm_sns_topic_arns     = var.alarm_sns_topic_arns

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

  # Cluster configuration (Cluster mode for production)
  cluster_mode_enabled    = true
  node_type               = var.redis_node_type
  num_node_groups         = 3
  replicas_per_node_group = 2

  engine_version = var.redis_engine_version

  # High availability
  multi_az_enabled           = true
  automatic_failover_enabled = true

  # Encryption
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  # auth_token is auto-generated

  # Backup
  enable_snapshot          = true
  snapshot_retention_limit = 7
  enable_final_snapshot    = true

  # Monitoring
  enable_slow_log = true
  log_retention_days = 30

  # Security
  allowed_security_group_ids = [module.eks.node_security_group_id]

  # CloudWatch alarms
  create_cloudwatch_alarms = true
  alarm_sns_topic_arns     = var.alarm_sns_topic_arns

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
      "pod-security.kubernetes.io/enforce" = "restricted"
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
