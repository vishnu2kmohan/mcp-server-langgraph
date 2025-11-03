#######################
# General Variables
#######################

variable "project_id" {
  description = "GCP project ID"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Project ID must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string

  validation {
    condition     = length(var.cluster_name) > 0 && length(var.cluster_name) <= 40
    error_message = "Cluster name must be 1-40 characters."
  }
}

variable "region" {
  description = "GCP region for the cluster"
  type        = string

  validation {
    condition = contains([
      "us-central1", "us-east1", "us-east4", "us-west1", "us-west2", "us-west3", "us-west4",
      "europe-west1", "europe-west2", "europe-west3", "europe-west4", "europe-west6",
      "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2", "asia-northeast3",
      "asia-south1", "asia-southeast1", "asia-southeast2",
      "australia-southeast1", "australia-southeast2",
      "southamerica-east1", "northamerica-northeast1"
    ], var.region)
    error_message = "Region must be a valid GCP region."
  }
}

variable "zone" {
  description = "GCP zone for zonal cluster (only used if regional_cluster is false)"
  type        = string
  default     = null

  validation {
    condition     = var.zone == null || can(regex("^[a-z]+-[a-z]+[0-9]+-[a-z]$", var.zone))
    error_message = "Zone must be a valid GCP zone format (e.g., us-central1-a)."
  }
}

variable "regional_cluster" {
  description = "Create a regional cluster (recommended for production)"
  type        = bool
  default     = true
}

#######################
# Network Configuration
#######################

variable "network_name" {
  description = "Name of the VPC network"
  type        = string

  validation {
    condition     = length(var.network_name) > 0
    error_message = "Network name must not be empty."
  }
}

variable "subnet_name" {
  description = "Name of the subnet"
  type        = string

  validation {
    condition     = length(var.subnet_name) > 0
    error_message = "Subnet name must not be empty."
  }
}

variable "pods_range_name" {
  description = "Name of the secondary IP range for pods"
  type        = string

  validation {
    condition     = length(var.pods_range_name) > 0
    error_message = "Pods range name must not be empty."
  }
}

variable "services_range_name" {
  description = "Name of the secondary IP range for services"
  type        = string

  validation {
    condition     = length(var.services_range_name) > 0
    error_message = "Services range name must not be empty."
  }
}

#######################
# Private Cluster Configuration
#######################

variable "enable_private_nodes" {
  description = "Enable private nodes (nodes have private IPs only)"
  type        = bool
  default     = true
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint (control plane only accessible via private IP)"
  type        = bool
  default     = false # Set to true for maximum security, false for easier access
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for the Kubernetes master nodes (/28 recommended)"
  type        = string
  default     = "172.16.0.0/28"

  validation {
    condition     = can(cidrhost(var.master_ipv4_cidr_block, 0)) && tonumber(split("/", var.master_ipv4_cidr_block)[1]) == 28
    error_message = "Master CIDR must be a valid /28 IPv4 CIDR block."
  }
}

variable "enable_master_global_access" {
  description = "Allow master to be accessible globally (not just from VPC)"
  type        = bool
  default     = false
}

variable "enable_master_authorized_networks" {
  description = "Enable master authorized networks (restrict control plane access)"
  type        = bool
  default     = true
}

variable "master_authorized_networks_cidrs" {
  description = "CIDR blocks authorized to access the control plane"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []

  validation {
    condition     = !var.enable_master_authorized_networks || length(var.master_authorized_networks_cidrs) > 0
    error_message = "When master authorized networks are enabled, at least one CIDR block must be specified to prevent lockout."
  }
}

#######################
# Release Channel & Maintenance
#######################

variable "release_channel" {
  description = "Release channel for automatic upgrades (RAPID, REGULAR, STABLE, or UNSPECIFIED)"
  type        = string
  default     = "REGULAR"

  validation {
    condition     = contains(["RAPID", "REGULAR", "STABLE", "UNSPECIFIED"], var.release_channel)
    error_message = "Release channel must be RAPID, REGULAR, STABLE, or UNSPECIFIED."
  }
}

variable "maintenance_start_time" {
  description = "Start time for daily maintenance window (HH:MM format, UTC)"
  type        = string
  default     = "03:00"

  validation {
    condition     = can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.maintenance_start_time))
    error_message = "Maintenance start time must be in HH:MM format (00:00 to 23:59)."
  }
}

#######################
# Autoscaling
#######################

variable "cluster_resource_limits" {
  description = "Resource limits for cluster autoscaling"
  type = list(object({
    resource_type = string
    minimum       = number
    maximum       = number
  }))
  default = [
    {
      resource_type = "cpu"
      minimum       = 1
      maximum       = 1000
    },
    {
      resource_type = "memory"
      minimum       = 4
      maximum       = 10000
    }
  ]
}

variable "autoscaling_profile" {
  description = "Autoscaling profile (BALANCED or OPTIMIZE_UTILIZATION)"
  type        = string
  default     = "BALANCED"

  validation {
    condition     = contains(["BALANCED", "OPTIMIZE_UTILIZATION"], var.autoscaling_profile)
    error_message = "Autoscaling profile must be BALANCED or OPTIMIZE_UTILIZATION."
  }
}

variable "enable_vertical_pod_autoscaling" {
  description = "Enable Vertical Pod Autoscaling"
  type        = bool
  default     = true
}

#######################
# Security
#######################

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization (image signing verification)"
  type        = bool
  default     = false # Enable for production with signed images
}

variable "binary_authorization_evaluation_mode" {
  description = "Binary Authorization evaluation mode (PROJECT_SINGLETON_POLICY_ENFORCE or POLICY_BINDINGS)"
  type        = string
  default     = "PROJECT_SINGLETON_POLICY_ENFORCE"

  validation {
    condition     = contains(["PROJECT_SINGLETON_POLICY_ENFORCE", "POLICY_BINDINGS", "POLICY_BINDINGS_AND_PROJECT_SINGLETON_POLICY_ENFORCE"], var.binary_authorization_evaluation_mode)
    error_message = "Binary Authorization evaluation mode must be valid."
  }
}

variable "enable_security_posture" {
  description = "Enable GKE Security Posture (vulnerability scanning)"
  type        = bool
  default     = true
}

variable "security_posture_mode" {
  description = "Security posture mode (BASIC, ENTERPRISE, or DISABLED)"
  type        = string
  default     = "BASIC"

  validation {
    condition     = contains(["BASIC", "ENTERPRISE", "DISABLED"], var.security_posture_mode)
    error_message = "Security posture mode must be BASIC, ENTERPRISE, or DISABLED."
  }
}

variable "security_posture_vulnerability_mode" {
  description = "Vulnerability scanning mode (VULNERABILITY_BASIC, VULNERABILITY_ENTERPRISE, or VULNERABILITY_DISABLED)"
  type        = string
  default     = "VULNERABILITY_BASIC"

  validation {
    condition     = contains(["VULNERABILITY_BASIC", "VULNERABILITY_ENTERPRISE", "VULNERABILITY_DISABLED"], var.security_posture_vulnerability_mode)
    error_message = "Vulnerability mode must be VULNERABILITY_BASIC, VULNERABILITY_ENTERPRISE, or VULNERABILITY_DISABLED."
  }
}

variable "enable_vulnerability_scanning" {
  description = "Enable container vulnerability scanning API"
  type        = bool
  default     = true
}

#######################
# Networking
#######################

variable "enable_dataplane_v2" {
  description = "Enable Dataplane V2 (eBPF-based networking)"
  type        = bool
  default     = true
}

variable "enable_network_policy" {
  description = "Enable network policy enforcement"
  type        = bool
  default     = true
}

variable "cluster_dns_provider" {
  description = "DNS provider (CLOUD_DNS or PLATFORM_DEFAULT)"
  type        = string
  default     = "CLOUD_DNS"

  validation {
    condition     = contains(["CLOUD_DNS", "PLATFORM_DEFAULT"], var.cluster_dns_provider)
    error_message = "DNS provider must be CLOUD_DNS or PLATFORM_DEFAULT."
  }
}

variable "cluster_dns_scope" {
  description = "DNS scope (CLUSTER_SCOPE or VPC_SCOPE)"
  type        = string
  default     = "CLUSTER_SCOPE"

  validation {
    condition     = contains(["CLUSTER_SCOPE", "VPC_SCOPE"], var.cluster_dns_scope)
    error_message = "DNS scope must be CLUSTER_SCOPE or VPC_SCOPE."
  }
}

variable "cluster_dns_domain" {
  description = "Custom DNS domain for the cluster"
  type        = string
  default     = ""
}

#######################
# Monitoring & Logging
#######################

variable "monitoring_enabled_components" {
  description = "List of monitoring components to enable"
  type        = list(string)
  default     = ["SYSTEM_COMPONENTS", "WORKLOADS"]

  validation {
    condition = alltrue([
      for component in var.monitoring_enabled_components :
      contains(["SYSTEM_COMPONENTS", "WORKLOADS", "APISERVER", "SCHEDULER", "CONTROLLER_MANAGER", "STORAGE", "HPA", "POD", "DAEMONSET", "DEPLOYMENT", "STATEFULSET"], component)
    ])
    error_message = "Monitoring components must be valid GKE monitoring components."
  }
}

variable "logging_enabled_components" {
  description = "List of logging components to enable"
  type        = list(string)
  default     = ["SYSTEM_COMPONENTS", "WORKLOADS"]

  validation {
    condition = alltrue([
      for component in var.logging_enabled_components :
      contains(["SYSTEM_COMPONENTS", "WORKLOADS"], component)
    ])
    error_message = "Logging components must be SYSTEM_COMPONENTS or WORKLOADS."
  }
}

variable "enable_managed_prometheus" {
  description = "Enable managed Prometheus for metrics collection"
  type        = bool
  default     = true
}

variable "enable_advanced_datapath_observability" {
  description = "Enable advanced datapath observability (requires Dataplane V2)"
  type        = bool
  default     = false
}

variable "datapath_observability_relay_mode" {
  description = "Relay mode for datapath observability (INTERNAL_VPC_LB or EXTERNAL_LB)"
  type        = string
  default     = "INTERNAL_VPC_LB"

  validation {
    condition     = contains(["INTERNAL_VPC_LB", "EXTERNAL_LB", "DISABLED"], var.datapath_observability_relay_mode)
    error_message = "Datapath observability relay mode must be INTERNAL_VPC_LB, EXTERNAL_LB, or DISABLED."
  }
}

variable "enable_log_export" {
  description = "Enable log export to BigQuery"
  type        = bool
  default     = false
}

variable "log_export_dataset_id" {
  description = "BigQuery dataset ID for log export"
  type        = string
  default     = ""
}

variable "enable_monitoring_alerts" {
  description = "Enable Cloud Monitoring alert policies"
  type        = bool
  default     = true
}

variable "monitoring_notification_channels" {
  description = "List of notification channel IDs for monitoring alerts"
  type        = list(string)
  default     = []
}

#######################
# Gateway API & Ingress
#######################

variable "enable_gateway_api" {
  description = "Enable Gateway API for advanced ingress"
  type        = bool
  default     = false
}

variable "gateway_api_channel" {
  description = "Gateway API channel (CHANNEL_STANDARD or CHANNEL_EXPERIMENTAL)"
  type        = string
  default     = "CHANNEL_STANDARD"

  validation {
    condition     = contains(["CHANNEL_STANDARD", "CHANNEL_EXPERIMENTAL"], var.gateway_api_channel)
    error_message = "Gateway API channel must be CHANNEL_STANDARD or CHANNEL_EXPERIMENTAL."
  }
}

#######################
# Addons
#######################

variable "enable_http_load_balancing" {
  description = "Enable HTTP load balancing addon"
  type        = bool
  default     = true
}

variable "enable_horizontal_pod_autoscaling" {
  description = "Enable horizontal pod autoscaling addon"
  type        = bool
  default     = true
}

variable "enable_dns_cache" {
  description = "Enable NodeLocal DNSCache"
  type        = bool
  default     = true
}

variable "enable_gce_persistent_disk_csi_driver" {
  description = "Enable GCE Persistent Disk CSI driver"
  type        = bool
  default     = true
}

variable "enable_gcp_filestore_csi_driver" {
  description = "Enable GCP Filestore CSI driver"
  type        = bool
  default     = false
}

variable "enable_gcs_fuse_csi_driver" {
  description = "Enable GCS FUSE CSI driver"
  type        = bool
  default     = false
}

variable "enable_config_connector" {
  description = "Enable Config Connector (manage GCP resources via Kubernetes)"
  type        = bool
  default     = false
}

variable "enable_gke_backup_agent" {
  description = "Enable GKE Backup agent"
  type        = bool
  default     = false
}

#######################
# Fleet & Multi-cluster
#######################

variable "enable_fleet_registration" {
  description = "Register cluster with GKE Fleet (for Anthos/multi-cluster features)"
  type        = bool
  default     = false
}

#######################
# Backup
#######################

variable "enable_backup_plan" {
  description = "Enable automated backup plan for the cluster"
  type        = bool
  default     = false
}

variable "backup_schedule_cron" {
  description = "Cron schedule for backups (e.g., '0 2 * * *' for daily at 2 AM)"
  type        = string
  default     = "0 2 * * *"
}

variable "backup_retain_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30

  validation {
    condition     = var.backup_retain_days >= 1 && var.backup_retain_days <= 365
    error_message = "Backup retain days must be between 1 and 365."
  }
}

variable "backup_delete_lock_days" {
  description = "Number of days backups are locked from deletion"
  type        = number
  default     = 7

  validation {
    condition     = var.backup_delete_lock_days >= 0 && var.backup_delete_lock_days <= 90
    error_message = "Backup delete lock days must be between 0 and 90."
  }
}

variable "backup_include_volume_data" {
  description = "Include volume data in backups"
  type        = bool
  default     = true
}

variable "backup_include_secrets" {
  description = "Include secrets in backups"
  type        = bool
  default     = false # Set to true if needed, but be aware of security implications
}

variable "backup_namespace" {
  description = "Namespace to backup (* for all namespaces)"
  type        = string
  default     = "*"
}

variable "backup_encryption_key" {
  description = "KMS key for backup encryption"
  type        = string
  default     = null
}

#######################
# Notifications
#######################

variable "notification_config_topic" {
  description = "Pub/Sub topic for cluster notifications"
  type        = string
  default     = null
}

#######################
# Cost Management
#######################

variable "enable_cost_allocation" {
  description = "Enable cost allocation tracking"
  type        = bool
  default     = true
}

#######################
# Lifecycle
#######################

variable "enable_deletion_protection" {
  description = "Enable deletion protection for the cluster"
  type        = bool
  default     = true
}

variable "cluster_create_timeout" {
  description = "Timeout for cluster creation"
  type        = string
  default     = "45m"
}

variable "cluster_update_timeout" {
  description = "Timeout for cluster updates"
  type        = string
  default     = "60m"
}

variable "cluster_delete_timeout" {
  description = "Timeout for cluster deletion"
  type        = string
  default     = "45m"
}

#######################
# Labels
#######################

variable "labels" {
  description = "Labels to apply to the cluster and resources"
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for k, v in var.labels : can(regex("^[a-z][a-z0-9_-]{0,62}$", k))
    ])
    error_message = "Label keys must start with a lowercase letter and contain only lowercase letters, numbers, underscores, and hyphens (max 63 characters)."
  }
}
