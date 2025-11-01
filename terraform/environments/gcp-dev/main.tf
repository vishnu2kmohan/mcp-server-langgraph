# GCP Development Environment
# Cost-optimized infrastructure for development and testing

terraform {
  required_version = ">= 1.5.0"

  backend "gcs" {
    bucket = "mcp-langgraph-terraform-state-us-central1-XXXXX"  # Replace with actual bucket
    prefix = "env/dev"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  default_labels = {
    environment = "development"
    managed_by  = "terraform"
    project     = "mcp-server-langgraph"
  }
}

locals {
  name_prefix  = "mcp-dev"
  cluster_name = "${local.name_prefix}-gke"

  common_labels = {
    environment = "development"
    managed_by  = "terraform"
    project     = "mcp-server-langgraph"
    team        = var.team
  }
}

#######################
# VPC Network
#######################

module "vpc" {
  source = "../../modules/gcp-vpc"

  project_id   = var.project_id
  name_prefix  = local.name_prefix
  region       = var.region
  cluster_name = local.cluster_name

  # Smaller CIDR blocks for dev
  nodes_cidr    = "10.10.0.0/22"   # 1024 IPs
  pods_cidr     = "10.12.0.0/16"   # 65k IPs
  services_cidr = "10.13.0.0/22"   # 1024 IPs

  # Regional routing (cost optimization)
  routing_mode = "REGIONAL"

  # Auto NAT IPs (no static IPs needed for dev)
  nat_ip_allocate_option        = "AUTO_ONLY"
  enable_dynamic_port_allocation = true
  nat_min_ports_per_vm          = 64

  # Minimal flow logs (cost optimization)
  enable_flow_logs                 = true
  flow_logs_aggregation_interval   = "INTERVAL_5_MIN"
  flow_logs_sampling               = 0.1  # 10% sampling

  # Private Service Connection
  enable_private_service_connection = true
  private_services_prefix_length    = 16

  # No Cloud Armor for dev
  enable_cloud_armor = false

  labels = local.common_labels
}

#######################
# GKE Autopilot Cluster
#######################

module "gke" {
  source = "../../modules/gke-autopilot"

  project_id   = var.project_id
  cluster_name = local.cluster_name
  region       = var.region

  # Zonal cluster for cost savings (not regional)
  regional_cluster = false
  zone             = "${var.region}-a"

  # Network configuration
  network_name        = module.vpc.network_name
  subnet_name         = module.vpc.nodes_subnet_name
  pods_range_name     = module.vpc.pods_range_name
  services_range_name = module.vpc.services_range_name

  # Private cluster (but allow public endpoint for easier access)
  enable_private_nodes    = true
  enable_private_endpoint = false  # Allow public access for dev
  master_ipv4_cidr_block  = "172.16.0.0/28"

  # Open master access (dev only!)
  enable_master_authorized_networks = false

  # Release channel
  release_channel = "REGULAR"  # Faster updates for dev

  # Maintenance window
  maintenance_start_time = "03:00"

  # Smaller resource limits
  cluster_resource_limits = [
    {
      resource_type = "cpu"
      minimum       = 1
      maximum       = 100
    },
    {
      resource_type = "memory"
      minimum       = 4
      maximum       = 1000
    }
  ]

  # Security (basic for dev)
  enable_binary_authorization = false
  enable_security_posture     = true
  security_posture_mode       = "BASIC"

  # Networking
  enable_dataplane_v2   = true
  enable_network_policy = true

  # Observability (basic)
  monitoring_enabled_components = ["SYSTEM_COMPONENTS"]
  logging_enabled_components    = ["SYSTEM_COMPONENTS"]
  enable_managed_prometheus     = false  # Cost savings

  # No advanced observability for dev
  enable_advanced_datapath_observability = false

  # Alerts (optional for dev)
  enable_monitoring_alerts = var.enable_monitoring_alerts

  # No backup for dev
  enable_backup_plan = false

  # No fleet registration for dev
  enable_fleet_registration = false

  # Cost management
  enable_cost_allocation = true

  # Addons (minimal)
  enable_http_load_balancing           = true
  enable_horizontal_pod_autoscaling    = true
  enable_vertical_pod_autoscaling      = false  # Not needed for dev
  enable_dns_cache                     = true
  enable_gce_persistent_disk_csi_driver = true
  enable_gcs_fuse_csi_driver           = false
  enable_config_connector              = false

  # No Gateway API for dev
  enable_gateway_api = false

  # No deletion protection for dev (easy cleanup)
  enable_deletion_protection = false

  labels = local.common_labels

  depends_on = [module.vpc]
}

#######################
# Cloud SQL (PostgreSQL)
#######################

module "cloudsql" {
  source = "../../modules/cloudsql"

  project_id  = var.project_id
  name_prefix = local.name_prefix
  region      = var.region

  # PostgreSQL version
  postgres_major_version = 15

  # Small instance (no HA for dev)
  tier              = "db-custom-1-3840"  # 1 vCPU, 3.75 GB RAM
  high_availability = false

  # Storage
  disk_type               = "PD_SSD"
  disk_size_gb            = 10  # Minimum
  enable_disk_autoresize  = true
  disk_autoresize_limit_gb = 100

  # Network
  vpc_network_self_link                 = module.vpc.network_self_link
  enable_public_ip                      = false
  require_ssl                           = true
  private_service_connection_dependency = module.vpc.private_service_connection_status

  # Backups (minimal for dev)
  enable_backups                 = true
  backup_start_time              = "02:00"
  enable_point_in_time_recovery  = false  # Cost savings
  backup_retention_count         = 7

  # Maintenance
  maintenance_window_day  = 7
  maintenance_window_hour = 3

  # Query Insights
  enable_query_insights = true

  # Database
  default_database_name = "mcp_langgraph_dev"
  additional_databases  = []

  # Users
  create_default_user = true
  default_user_name   = "postgres"

  # No read replicas for dev
  read_replica_count = 0

  # Monitoring (optional)
  enable_monitoring_alerts = var.enable_monitoring_alerts

  # No deletion protection for dev
  enable_deletion_protection = false

  labels = local.common_labels

  depends_on = [module.vpc]
}

#######################
# Memorystore (Redis)
#######################

module "memorystore" {
  source = "../../modules/memorystore"

  project_id  = var.project_id
  name_prefix = local.name_prefix
  region      = var.region

  # Basic tier for cost savings (no HA)
  tier           = "BASIC"
  memory_size_gb = 1  # Minimum
  redis_version  = "REDIS_7_0"

  # No replicas for dev
  replica_count      = 0
  read_replicas_mode = "READ_REPLICAS_DISABLED"

  # Network
  vpc_network_id = module.vpc.network_id
  connect_mode   = "DIRECT_PEERING"

  # Security
  enable_transit_encryption = true
  enable_auth               = true

  # Persistence (optional for dev)
  enable_persistence  = true
  persistence_mode    = "RDB"
  rdb_snapshot_period = "TWENTY_FOUR_HOURS"

  # Redis configuration
  maxmemory_policy = "allkeys-lru"

  # Maintenance
  maintenance_window_day  = 7
  maintenance_window_hour = 3

  # No cross-region replicas for dev
  create_cross_region_replica = false

  # Monitoring (optional)
  enable_monitoring_alerts = var.enable_monitoring_alerts

  # No deletion protection for dev
  enable_deletion_protection = false

  labels = local.common_labels

  depends_on = [module.vpc]
}

#######################
# Workload Identity
#######################

module "workload_identity" {
  source = "../../modules/gke-workload-identity"

  project_id = var.project_id
  namespace  = var.app_namespace

  service_accounts = {
    # Main application service account
    "mcp-server-sa" = {
      gcp_sa_name  = "${local.name_prefix}-app-sa"
      display_name = "MCP Server Dev Application SA"
      roles = [
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
      ]
      cloudsql_access = true
    }
  }

  depends_on = [module.gke]
}
