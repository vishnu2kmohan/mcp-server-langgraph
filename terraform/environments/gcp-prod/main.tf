# GCP Production Environment
# Complete infrastructure for MCP Server LangGraph on GKE Autopilot

terraform {
  required_version = ">= 1.5.0"

  # Backend configuration is provided via -backend-config flag
  # See terraform/backend-configs/README.md for setup instructions
  # Example: terraform init -backend-config=../../backend-configs/gcp-prod.gcs.tfbackend
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
    environment = "production"
    managed_by  = "terraform"
    project     = "mcp-server-langgraph"
  }
}

locals {
  # Full name for GKE cluster and K8s resources (no length limit)
  name_prefix  = "production-mcp-server-langgraph"
  cluster_name = "${local.name_prefix}-gke"

  # Short name for VPC, Cloud SQL, Redis (20 char limit)
  short_prefix = "production-mcp-slg"

  common_labels = {
    environment = "production"
    managed_by  = "terraform"
    project     = "mcp-server-langgraph"
    team        = var.team
    cost_center = var.cost_center
  }
}

#######################
# GCP API Enablement
#######################

module "project_services" {
  source = "../../modules/gcp-project-services"

  project_id = var.project_id

  # Core APIs (required for all GCP infrastructure)
  enable_container_api = true # Required for GKE
  enable_compute_api   = true # Required for VPC, subnets, and compute resources

  # Networking APIs
  enable_service_networking_api = true # Required for private service connection (Cloud SQL, Memorystore)

  # GKE Feature APIs
  enable_gke_backup_api         = true  # Required for backup_plan (enabled below)
  enable_container_scanning_api = false # Can be enabled for vulnerability scanning

  # Secret Management APIs
  enable_secret_manager_api = true # Required for Workload Identity secret access

  # Database APIs
  enable_sql_admin_api = true # Required for Cloud SQL
  enable_redis_api     = true # Required for Memorystore

  # Monitoring & Logging APIs
  enable_monitoring_api = true # Required for monitoring alerts
  enable_logging_api    = true # Required for log exports

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
  name_prefix  = local.short_prefix
  region       = var.region
  cluster_name = local.cluster_name

  # Network CIDR blocks
  nodes_cidr    = var.nodes_cidr
  pods_cidr     = var.pods_cidr
  services_cidr = var.services_cidr

  # Regional routing for cost optimization
  routing_mode = "REGIONAL"

  # Cloud NAT configuration
  nat_ip_allocate_option         = "MANUAL_ONLY" # Static IPs for production
  nat_ip_count                   = 2             # Redundancy
  enable_dynamic_port_allocation = true
  nat_min_ports_per_vm           = 64
  nat_max_ports_per_vm           = 32768

  # VPC Flow Logs (with sampling for cost control)
  enable_flow_logs               = true
  flow_logs_aggregation_interval = "INTERVAL_5_SEC"
  flow_logs_sampling             = 0.1 # 10% sampling
  flow_logs_metadata             = "INCLUDE_ALL_METADATA"

  # Private Service Connection for Cloud SQL/Memorystore
  enable_private_service_connection = true
  private_services_prefix_length    = 16 # /16 for managed services

  # Cloud Armor (optional - enable for public-facing services)
  enable_cloud_armor                     = var.enable_cloud_armor
  cloud_armor_rate_limit_threshold       = 1000
  cloud_armor_rate_limit_interval        = 60
  cloud_armor_ban_duration_sec           = 600
  enable_cloud_armor_adaptive_protection = true

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

  # High availability - regional cluster
  regional_cluster = true

  # Network configuration (from VPC module)
  network_name        = module.vpc.network_name
  subnet_name         = module.vpc.nodes_subnet_name
  pods_range_name     = module.vpc.pods_range_name
  services_range_name = module.vpc.services_range_name

  # Private cluster configuration
  enable_private_nodes    = true
  enable_private_endpoint = var.enable_private_endpoint
  master_ipv4_cidr_block  = var.master_ipv4_cidr_block

  # Master authorized networks
  enable_master_authorized_networks = var.enable_master_authorized_networks
  master_authorized_networks_cidrs  = var.master_authorized_networks_cidrs

  # Release channel (STABLE for production)
  release_channel = "STABLE"

  # Maintenance window (Sunday 3 AM UTC)
  maintenance_start_time = "03:00"

  # Cluster resource limits
  cluster_resource_limits = [
    {
      resource_type = "cpu"
      minimum       = 4
      maximum       = var.max_cluster_cpu
    },
    {
      resource_type = "memory"
      minimum       = 16
      maximum       = var.max_cluster_memory
    }
  ]

  # Security features
  enable_binary_authorization          = var.enable_binary_authorization
  binary_authorization_evaluation_mode = "PROJECT_SINGLETON_POLICY_ENFORCE"
  enable_security_posture              = true
  security_posture_mode                = "ENTERPRISE"
  security_posture_vulnerability_mode  = "VULNERABILITY_ENTERPRISE"

  # Networking
  enable_dataplane_v2   = true # eBPF-based networking
  enable_network_policy = true

  # Observability
  monitoring_enabled_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  logging_enabled_components    = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  enable_managed_prometheus     = true

  enable_advanced_datapath_observability = true
  datapath_observability_relay_mode      = "INTERNAL_VPC_LB"

  # Monitoring alerts
  enable_monitoring_alerts         = true
  monitoring_notification_channels = var.monitoring_notification_channels

  # Backup
  enable_backup_plan         = true
  backup_schedule_cron       = "0 2 * * *" # 2 AM daily
  backup_retain_days         = 30
  backup_delete_lock_days    = 7
  backup_include_volume_data = true
  backup_include_secrets     = false
  backup_namespace           = "*"

  # Fleet registration for Anthos
  enable_fleet_registration = var.enable_fleet_registration

  # Cost management
  enable_cost_allocation = true

  # Addons
  enable_http_load_balancing            = true
  enable_horizontal_pod_autoscaling     = true
  enable_vertical_pod_autoscaling       = true
  enable_dns_cache                      = true
  enable_gce_persistent_disk_csi_driver = true
  enable_gcs_fuse_csi_driver            = true
  enable_config_connector               = false

  # Gateway API
  enable_gateway_api  = var.enable_gateway_api
  gateway_api_channel = "CHANNEL_STANDARD"

  # Deletion protection
  enable_deletion_protection = true

  labels = local.common_labels

  depends_on = [module.project_services, module.vpc]
}

#######################
# Cloud SQL (PostgreSQL)
#######################

module "cloudsql" {
  source = "../../modules/cloudsql"

  project_id  = var.project_id
  name_prefix = local.short_prefix
  region      = var.region

  # PostgreSQL version
  postgres_major_version = 15

  # High availability
  tier              = var.cloudsql_tier
  high_availability = true

  # Storage
  disk_type                = "PD_SSD"
  disk_size_gb             = var.cloudsql_disk_size_gb
  enable_disk_autoresize   = true
  disk_autoresize_limit_gb = var.cloudsql_disk_autoresize_limit_gb

  # Network (private IP only)
  vpc_network_self_link                 = module.vpc.network_self_link
  enable_public_ip                      = false
  require_ssl                           = true
  private_service_connection_dependency = module.vpc.private_service_connection_status

  # Backups
  enable_backups                 = true
  backup_start_time              = "02:00"
  enable_point_in_time_recovery  = true
  transaction_log_retention_days = 7
  backup_retention_count         = 30

  # Maintenance
  maintenance_window_day  = 7 # Sunday
  maintenance_window_hour = 3 # 3 AM UTC

  # Query Insights
  enable_query_insights                = true
  query_insights_plans_per_minute      = 5
  query_insights_string_length         = 1024
  query_insights_record_app_tags       = true
  query_insights_record_client_address = true

  # Slow query logging
  enable_slow_query_log   = true
  slow_query_threshold_ms = "1000"

  # Database
  default_database_name = "mcp_langgraph"
  additional_databases  = var.additional_databases

  # Users
  create_default_user = true
  default_user_name   = "postgres"
  additional_users    = var.cloudsql_additional_users

  # Read replicas
  read_replica_count   = var.cloudsql_read_replica_count
  read_replica_regions = var.cloudsql_read_replica_regions

  # Security
  enable_password_validation = true
  password_min_length        = 12
  password_complexity        = "COMPLEXITY_DEFAULT"

  # Monitoring
  enable_monitoring_alerts         = true
  monitoring_notification_channels = var.monitoring_notification_channels
  alert_cpu_threshold              = 80
  alert_memory_threshold           = 80
  alert_disk_threshold             = 80

  # Deletion protection
  enable_deletion_protection = true

  labels = local.common_labels

  depends_on = [module.project_services, module.vpc]
}

#######################
# Memorystore (Redis)
#######################

module "memorystore" {
  source = "../../modules/memorystore"

  project_id  = var.project_id
  name_prefix = local.short_prefix
  region      = var.region

  # High availability
  tier           = "STANDARD_HA"
  memory_size_gb = var.redis_memory_size_gb
  redis_version  = "REDIS_7_0"

  # Replicas
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
  timeout_seconds  = 0

  # Maintenance
  maintenance_window_day    = 7 # Sunday
  maintenance_window_hour   = 3 # 3 AM UTC
  maintenance_window_minute = 30

  # Cross-region replicas (optional for DR)
  create_cross_region_replica = var.redis_create_cross_region_replica
  read_replica_regions        = var.redis_read_replica_regions

  # Monitoring
  enable_monitoring_alerts         = true
  monitoring_notification_channels = var.monitoring_notification_channels
  alert_memory_threshold           = 80
  alert_cpu_threshold              = 80
  alert_connections_threshold      = 5000

  # Deletion protection
  enable_deletion_protection = true

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
      display_name = "MCP Server Application Service Account"
      description  = "Service account for MCP Server application pods"
      roles = [
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
        "roles/cloudtrace.agent",
        "roles/cloudprofiler.agent",
      ]
      cloudsql_access = true
      secret_ids      = var.app_secret_ids
      bucket_access = [
        {
          bucket_name = var.app_storage_bucket
          role        = "roles/storage.objectAdmin"
        }
      ]
    }

    # Background worker service account
    "worker-sa" = {
      gcp_sa_name  = "${local.name_prefix}-worker-sa"
      display_name = "MCP Server Worker Service Account"
      description  = "Service account for background worker pods"
      roles = [
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
      ]
      cloudsql_access      = true
      pubsub_topics        = var.worker_pubsub_topics
      pubsub_subscriptions = var.worker_pubsub_subscriptions
    }
  }

  depends_on = [module.project_services, module.gke]
}
