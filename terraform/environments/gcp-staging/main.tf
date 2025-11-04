# GCP Staging Environment
# Pre-production environment matching production configuration

terraform {
  required_version = ">= 1.5.0"

  # Backend configuration is provided via -backend-config flag
  # See terraform/backend-configs/README.md for setup instructions
  # Example: terraform init -backend-config=../../backend-configs/gcp-staging.gcs.tfbackend
  backend "gcs" {}

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
    environment = "staging"
    managed_by  = "terraform"
    project     = "mcp-server-langgraph"
  }
}

locals {
  name_prefix  = "mcp-staging"
  cluster_name = "${local.name_prefix}-gke"

  common_labels = {
    environment = "staging"
    managed_by  = "terraform"
    project     = "mcp-server-langgraph"
    team        = var.team
  }
}

#######################
# GCP API Enablement
#######################

module "project_services" {
  source = "../../modules/gcp-project-services"

  project_id = var.project_id

  # Core APIs (required for all GCP infrastructure)
  enable_container_api = true  # Required for GKE
  enable_compute_api   = true  # Required for VPC, subnets, and compute resources

  # Networking APIs
  enable_service_networking_api = true  # Required for private service connection (Cloud SQL, Memorystore)

  # GKE Feature APIs
  enable_gke_backup_api         = true   # Required for backup_plan (enabled below)
  enable_container_scanning_api = false  # Vulnerability scanning not enabled in staging

  # Secret Management APIs
  enable_secret_manager_api = true  # Required for Workload Identity secret access

  # Database APIs
  enable_sql_admin_api = true  # Required for Cloud SQL
  enable_redis_api     = true  # Required for Memorystore

  # Monitoring & Logging APIs
  enable_monitoring_api = true  # Required for monitoring alerts
  enable_logging_api    = true  # Required for log exports

  # Safety: Never disable APIs on destroy (can break existing resources)
  disable_on_destroy         = false
  disable_dependent_services = false
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

  # Medium-sized CIDR blocks for staging
  nodes_cidr    = "10.20.0.0/20"   # 4096 IPs
  pods_cidr     = "10.24.0.0/15"   # 131k IPs
  services_cidr = "10.26.0.0/20"   # 4096 IPs

  # Regional routing
  routing_mode = "REGIONAL"

  # Auto NAT IPs (staging doesn't need static)
  nat_ip_allocate_option        = "AUTO_ONLY"
  enable_dynamic_port_allocation = true

  # Flow logs with sampling
  enable_flow_logs                 = true
  flow_logs_aggregation_interval   = "INTERVAL_5_SEC"
  flow_logs_sampling               = 0.2  # 20% sampling

  # Private Service Connection
  enable_private_service_connection = true

  # Cloud Armor (optional)
  enable_cloud_armor = var.enable_cloud_armor

  labels = local.common_labels

  depends_on = [module.project_services]
}

#######################
# GKE Autopilot Cluster
#######################

module "gke" {
  source = "../../modules/gke-autopilot"

  project_id   = var.project_id
  cluster_name = local.cluster_name
  region       = var.region

  # Regional cluster for staging (matches prod)
  regional_cluster = true

  # Network configuration
  network_name        = module.vpc.network_name
  subnet_name         = module.vpc.nodes_subnet_name
  pods_range_name     = module.vpc.pods_range_name
  services_range_name = module.vpc.services_range_name

  # Private cluster (public endpoint for easier access)
  enable_private_nodes    = true
  enable_private_endpoint = false
  master_ipv4_cidr_block  = "172.16.0.0/28"

  # Master authorized networks
  enable_master_authorized_networks = var.enable_master_authorized_networks
  master_authorized_networks_cidrs  = var.master_authorized_networks_cidrs

  # Release channel
  release_channel = "REGULAR"

  # Maintenance window
  maintenance_start_time = "03:00"

  # Medium resource limits
  cluster_resource_limits = [
    {
      resource_type = "cpu"
      minimum       = 2
      maximum       = 500
    },
    {
      resource_type = "memory"
      minimum       = 8
      maximum       = 5000
    }
  ]

  # Security
  enable_binary_authorization = var.enable_binary_authorization
  enable_security_posture     = true
  security_posture_mode       = "BASIC"

  # Networking
  enable_dataplane_v2   = true
  enable_network_policy = true

  # Observability
  monitoring_enabled_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  logging_enabled_components    = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  enable_managed_prometheus     = true

  # Monitoring alerts
  enable_monitoring_alerts         = true
  monitoring_notification_channels = var.monitoring_notification_channels

  # Backup (weekly for staging)
  enable_backup_plan          = true
  backup_schedule_cron        = "0 2 * * 0"  # Sunday 2 AM
  backup_retain_days          = 14
  backup_include_volume_data  = true

  # Fleet registration
  enable_fleet_registration = var.enable_fleet_registration

  # Cost management
  enable_cost_allocation = true

  # Addons
  enable_http_load_balancing           = true
  enable_horizontal_pod_autoscaling    = true
  enable_vertical_pod_autoscaling      = true
  enable_dns_cache                     = true
  enable_gce_persistent_disk_csi_driver = true
  enable_gcs_fuse_csi_driver           = true

  # Deletion protection (moderate for staging)
  enable_deletion_protection = var.enable_deletion_protection

  labels = local.common_labels

  depends_on = [module.project_services, module.vpc]
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

  # Medium instance with HA
  tier              = "db-custom-2-7680"  # 2 vCPU, 7.5 GB RAM
  high_availability = true

  # Storage
  disk_type               = "PD_SSD"
  disk_size_gb            = 50
  enable_disk_autoresize  = true
  disk_autoresize_limit_gb = 500

  # Network
  vpc_network_self_link                 = module.vpc.network_self_link
  enable_public_ip                      = false
  require_ssl                           = true
  private_service_connection_dependency = module.vpc.private_service_connection_status

  # Backups
  enable_backups                 = true
  backup_start_time              = "02:00"
  enable_point_in_time_recovery  = true
  transaction_log_retention_days = 7
  backup_retention_count         = 14  # 2 weeks

  # Maintenance
  maintenance_window_day  = 7
  maintenance_window_hour = 3

  # Query Insights
  enable_query_insights = true

  # Database
  default_database_name = "mcp_langgraph_staging"
  additional_databases  = var.additional_databases

  # Users
  create_default_user = true
  default_user_name   = "postgres"
  additional_users    = var.cloudsql_additional_users

  # Read replicas (optional for staging)
  read_replica_count   = var.cloudsql_read_replica_count
  read_replica_regions = var.cloudsql_read_replica_regions

  # Monitoring
  enable_monitoring_alerts         = true
  monitoring_notification_channels = var.monitoring_notification_channels

  # Moderate deletion protection
  enable_deletion_protection = var.enable_deletion_protection

  labels = local.common_labels

  depends_on = [module.project_services, module.vpc]
}

#######################
# Memorystore (Redis)
#######################

module "memorystore" {
  source = "../../modules/memorystore"

  project_id  = var.project_id
  name_prefix = local.name_prefix
  region      = var.region

  # Standard HA for staging
  tier           = "STANDARD_HA"
  memory_size_gb = 3
  redis_version  = "REDIS_7_0"

  # Read replica
  replica_count      = 1
  read_replicas_mode = "READ_REPLICAS_ENABLED"

  # Network
  vpc_network_id = module.vpc.network_id
  connect_mode   = "DIRECT_PEERING"

  # Security
  enable_transit_encryption = true
  enable_auth               = true

  # Persistence
  enable_persistence  = true
  persistence_mode    = "RDB"
  rdb_snapshot_period = "TWELVE_HOURS"

  # Redis configuration
  maxmemory_policy = "allkeys-lru"

  # Maintenance
  maintenance_window_day  = 7
  maintenance_window_hour = 3

  # No cross-region replicas for staging
  create_cross_region_replica = false

  # Monitoring
  enable_monitoring_alerts         = true
  monitoring_notification_channels = var.monitoring_notification_channels

  # Moderate deletion protection
  enable_deletion_protection = var.enable_deletion_protection

  labels = local.common_labels

  depends_on = [module.project_services, module.vpc]
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
      display_name = "MCP Server Staging Application SA"
      roles = [
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
        "roles/cloudtrace.agent",
        "roles/aiplatform.user",  # For Vertex AI
      ]
      cloudsql_access = true
      secret_ids      = var.app_secret_ids
    }

    # Worker service account (if needed)
    "worker-sa" = {
      gcp_sa_name  = "${local.name_prefix}-worker-sa"
      display_name = "MCP Server Staging Worker SA"
      roles = [
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
      ]
      cloudsql_access = true
    }
  }

  depends_on = [module.project_services, module.gke]
}
