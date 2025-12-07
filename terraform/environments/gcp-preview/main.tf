# GCP Preview Environment
# Auto-deployed preview environment from main branch

terraform {
  required_version = ">= 1.5.0"

  # Backend configuration is provided via -backend-config flag
  # See terraform/backend-configs/README.md for setup instructions
  # Example: terraform init -backend-config=../../backend-configs/gcp-preview.gcs.tfbackend
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
    environment = "preview"
    managed_by  = "terraform"
    project     = "mcp-server-langgraph"
  }
}

locals {
  # Full name for GKE cluster and K8s resources (no length limit)
  name_prefix  = "preview-mcp-server-langgraph"
  cluster_name = "${local.name_prefix}-gke"

  # Short name for VPC, Cloud SQL, Redis (20 char limit)
  short_prefix = "preview-mcp-slg"

  common_labels = {
    environment = "preview"
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
  enable_container_api = true # Required for GKE
  enable_compute_api   = true # Required for VPC, subnets, and compute resources

  # Networking APIs
  enable_service_networking_api = true # Required for private service connection (Cloud SQL, Memorystore)

  # GKE Feature APIs
  enable_gke_backup_api         = true  # Required for backup_plan (enabled below)
  enable_container_scanning_api = false # Vulnerability scanning not enabled in preview

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

  # Medium-sized CIDR blocks for preview
  nodes_cidr    = "10.20.0.0/20" # 4096 IPs
  pods_cidr     = "10.24.0.0/15" # 131k IPs
  services_cidr = "10.26.0.0/20" # 4096 IPs

  # Regional routing
  routing_mode = "REGIONAL"

  # Auto NAT IPs (preview doesn't need static)
  nat_ip_allocate_option         = "AUTO_ONLY"
  enable_dynamic_port_allocation = true

  # Flow logs with sampling
  enable_flow_logs               = true
  flow_logs_aggregation_interval = "INTERVAL_5_SEC"
  flow_logs_sampling             = 0.2 # 20% sampling

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

  # Regional cluster for preview (matches prod)
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
  # Security posture is managed automatically by GKE Autopilot (v1.27+)
  # Explicit configuration causes API conflicts
  # Reference: https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-security
  enable_security_posture = false

  # Networking
  enable_dataplane_v2   = true
  enable_network_policy = true

  # Observability
  monitoring_enabled_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  logging_enabled_components    = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  enable_managed_prometheus     = true

  # Monitoring alerts
  # DISABLED: GCP metrics don't exist until cluster has running workloads
  # Enable after cluster is operational for ~30 min to allow metric population
  # Issue: GCP API returns 404 for metrics like kubernetes.io/pod/phase
  enable_monitoring_alerts         = false
  monitoring_notification_channels = var.monitoring_notification_channels

  # Backup (weekly for preview)
  enable_backup_plan         = true
  backup_schedule_cron       = "0 2 * * 0" # Sunday 2 AM
  backup_retain_days         = 14
  backup_delete_lock_days    = 0 # Allow immediate deletion for preview (Issue #9)
  backup_include_volume_data = true

  # Fleet registration
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

  # Deletion protection (moderate for preview)
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
  name_prefix = local.short_prefix
  region      = var.region

  # PostgreSQL version (matches docker-compose.yml for local/cloud parity)
  postgres_major_version = 16

  # Medium instance with HA
  tier              = "db-custom-2-7680" # 2 vCPU, 7.5 GB RAM
  high_availability = true

  # Storage
  disk_type                = "PD_SSD"
  disk_size_gb             = 50
  enable_disk_autoresize   = true
  disk_autoresize_limit_gb = 500

  # Network
  vpc_network_self_link                 = module.vpc.network_self_link
  enable_public_ip                      = false
  ssl_mode                              = "ENCRYPTED_ONLY"
  private_service_connection_dependency = module.vpc.private_service_connection_status

  # Backups
  enable_backups                 = true
  backup_start_time              = "02:00"
  enable_point_in_time_recovery  = true
  transaction_log_retention_days = 7
  backup_retention_count         = 14 # 2 weeks

  # Maintenance
  maintenance_window_day  = 7
  maintenance_window_hour = 3

  # Query Insights
  enable_query_insights = true

  # Database
  default_database_name = "mcp_langgraph_preview"
  additional_databases  = var.additional_databases

  # Users
  create_default_user = true
  default_user_name   = "postgres"
  additional_users    = var.cloudsql_additional_users

  # Read replicas (optional for preview)
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
  name_prefix = local.short_prefix
  region      = var.region

  # Standard HA for preview
  tier           = "STANDARD_HA"
  memory_size_gb = 5 # Minimum 5GB for read replicas
  # Redis 7.2 to match docker-compose.yml for local/cloud parity
  redis_version = "REDIS_7_2"

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

  # No cross-region replicas for preview
  create_cross_region_replica = false

  # Monitoring
  # DISABLED: GCP metrics don't exist until Redis has active connections
  # Enable after Redis is actively used for ~30 min to allow metric population
  # Issue: GCP API returns 404 for metrics like redis.googleapis.com/stats/uptime
  enable_monitoring_alerts         = false
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
    # Keycloak service account
    # K8s SA: keycloak-sa (overlay resource, namePrefix not applied)
    "keycloak-sa" = {
      gcp_sa_name  = "preview-keycloak"
      display_name = "Keycloak Preview SA"
      roles = [
        "roles/logging.logWriter",
      ]
      cloudsql_access = true
    }

    # OpenFGA service account
    # K8s SA: openfga-sa (overlay resource, namePrefix not applied)
    "openfga-sa" = {
      gcp_sa_name  = "preview-openfga"
      display_name = "OpenFGA Preview SA"
      roles = [
        "roles/logging.logWriter",
      ]
      cloudsql_access = true
    }

    # Main MCP Server application service account
    "preview-mcp-server-langgraph" = {
      gcp_sa_name  = "preview-mcp-slg-sa"
      display_name = "MCP Server Preview Application SA"
      roles = [
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
        "roles/cloudtrace.agent",
        "roles/aiplatform.user", # For Vertex AI
      ]
      cloudsql_access = true
      secret_ids      = var.app_secret_ids
    }
  }

  depends_on = [module.project_services, module.gke]
}

#######################
# GitHub Actions WIF
#######################

module "github_actions_wif" {
  source = "../../modules/github-actions-wif"

  project_id              = var.project_id
  project_number          = var.project_number
  github_repository_owner = "vishnu2kmohan"

  service_accounts = {
    preview = {
      account_id        = "github-actions-preview"
      display_name      = "GitHub Actions - Preview Deployment"
      description       = "Service account for GitHub Actions preview deployments to GKE"
      repository_filter = "mcp-server-langgraph"

      project_roles = [
        "roles/container.developer",
        "roles/artifactregistry.writer",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
      ]
      # Note: artifact_registry_repositories removed - repository mcp-preview doesn't exist
      # Project-level roles/artifactregistry.writer grants access to all repos in project
    }

    terraform = {
      account_id   = "github-actions-terraform"
      display_name = "GitHub Actions - Terraform"
      description  = "Service account for GitHub Actions Terraform operations"

      project_roles = [
        "roles/compute.networkAdmin",
        "roles/container.admin",
        "roles/iam.serviceAccountAdmin",
        "roles/resourcemanager.projectIamAdmin",
        "roles/storage.admin",
      ]
    }

    production = {
      account_id        = "github-actions-production"
      display_name      = "GitHub Actions - Production Deployment"
      description       = "Service account for GitHub Actions production deployments to GKE"
      repository_filter = "mcp-server-langgraph"

      project_roles = [
        "roles/container.developer",
        "roles/artifactregistry.writer",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
        "roles/cloudtrace.agent",
      ]
    }
  }

  depends_on = [module.project_services]
}
