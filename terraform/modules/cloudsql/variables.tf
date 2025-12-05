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

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string

  validation {
    condition     = length(var.name_prefix) <= 20
    error_message = "Name prefix must be 20 characters or less."
  }
}

variable "instance_name" {
  description = "Name of the Cloud SQL instance (leave empty to use name_prefix)"
  type        = string
  default     = ""
}

variable "region" {
  description = "GCP region for the instance"
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

#######################
# Database Configuration
#######################

variable "database_version" {
  description = "PostgreSQL version (e.g., POSTGRES_15, POSTGRES_14, POSTGRES_13)"
  type        = string
  default     = "POSTGRES_15"

  validation {
    condition     = can(regex("^POSTGRES_(11|12|13|14|15|16)$", var.database_version))
    error_message = "Database version must be a valid PostgreSQL version (11-16)."
  }
}

variable "postgres_major_version" {
  description = "PostgreSQL major version number (e.g., 15, 14, 13) - alternative to database_version"
  type        = number
  default     = null

  validation {
    condition     = var.postgres_major_version == null || (var.postgres_major_version >= 11 && var.postgres_major_version <= 16)
    error_message = "PostgreSQL major version must be between 11 and 16."
  }
}

variable "tier" {
  description = "Machine type tier (e.g., db-f1-micro, db-g1-small, db-n1-standard-1, db-custom-CPU-RAM)"
  type        = string
  default     = "db-custom-2-7680" # 2 vCPU, 7.5 GB RAM

  validation {
    condition     = can(regex("^db-(f1-micro|g1-small|n1-standard-\\d+|n1-highmem-\\d+|n1-highcpu-\\d+|custom-\\d+-\\d+)$", var.tier))
    error_message = "Tier must be a valid Cloud SQL machine type."
  }
}

variable "high_availability" {
  description = "Enable high availability (regional instance)"
  type        = bool
  default     = true
}

#######################
# Storage Configuration
#######################

variable "disk_type" {
  description = "Disk type (PD_SSD or PD_HDD)"
  type        = string
  default     = "PD_SSD"

  validation {
    condition     = contains(["PD_SSD", "PD_HDD"], var.disk_type)
    error_message = "Disk type must be PD_SSD or PD_HDD."
  }
}

variable "disk_size_gb" {
  description = "Initial disk size in GB"
  type        = number
  default     = 100

  validation {
    condition     = var.disk_size_gb >= 10 && var.disk_size_gb <= 65536
    error_message = "Disk size must be between 10 and 65536 GB."
  }
}

variable "enable_disk_autoresize" {
  description = "Enable automatic disk resize"
  type        = bool
  default     = true
}

variable "disk_autoresize_limit_gb" {
  description = "Maximum disk size in GB (0 = no limit)"
  type        = number
  default     = 0

  validation {
    condition     = var.disk_autoresize_limit_gb == 0 || (var.disk_autoresize_limit_gb >= 10 && var.disk_autoresize_limit_gb <= 65536)
    error_message = "Disk autoresize limit must be 0 (no limit) or between 10 and 65536 GB."
  }
}

#######################
# Network Configuration
#######################

variable "vpc_network_self_link" {
  description = "Self link of the VPC network for private IP"
  type        = string

  validation {
    condition     = can(regex("^https://www.googleapis.com/compute/v1/projects/[^/]+/global/networks/[^/]+$", var.vpc_network_self_link))
    error_message = "VPC network self link must be a valid GCP network resource link."
  }
}

variable "enable_public_ip" {
  description = "Enable public IP address (not recommended for production)"
  type        = bool
  default     = false
}

variable "require_ssl" {
  description = "Require SSL for connections"
  type        = bool
  default     = true
}

variable "authorized_networks" {
  description = "List of authorized networks (only used if public IP is enabled)"
  type = list(object({
    name = string
    cidr = string
  }))
  default = []
}

variable "private_service_connection_dependency" {
  description = "Dependency on private service connection (pass null to create independently)"
  type        = any
  default     = null
}

#######################
# Backup Configuration
#######################

variable "enable_backups" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_start_time" {
  description = "Start time for daily backups (HH:MM format, UTC)"
  type        = string
  default     = "03:00"

  validation {
    condition     = can(regex("^([01][0-9]|2[0-3]):[0-5][0-9]$", var.backup_start_time))
    error_message = "Backup start time must be in HH:MM format (00:00 to 23:59)."
  }
}

variable "enable_point_in_time_recovery" {
  description = "Enable point-in-time recovery (PITR)"
  type        = bool
  default     = true
}

variable "transaction_log_retention_days" {
  description = "Number of days to retain transaction logs for PITR (1-7)"
  type        = number
  default     = 7

  validation {
    condition     = var.transaction_log_retention_days >= 1 && var.transaction_log_retention_days <= 7
    error_message = "Transaction log retention must be between 1 and 7 days."
  }
}

variable "backup_retention_count" {
  description = "Number of backups to retain"
  type        = number
  default     = 30

  validation {
    condition     = var.backup_retention_count >= 1 && var.backup_retention_count <= 365
    error_message = "Backup retention count must be between 1 and 365."
  }
}

variable "backup_location" {
  description = "Location for backups (region or multi-region, empty for automatic)"
  type        = string
  default     = ""
}

#######################
# Maintenance Configuration
#######################

variable "maintenance_window_day" {
  description = "Day of week for maintenance (1=Monday, 7=Sunday)"
  type        = number
  default     = 7 # Sunday

  validation {
    condition     = var.maintenance_window_day >= 1 && var.maintenance_window_day <= 7
    error_message = "Maintenance window day must be between 1 (Monday) and 7 (Sunday)."
  }
}

variable "maintenance_window_hour" {
  description = "Hour of day for maintenance (0-23, UTC)"
  type        = number
  default     = 3 # 3 AM UTC

  validation {
    condition     = var.maintenance_window_hour >= 0 && var.maintenance_window_hour <= 23
    error_message = "Maintenance window hour must be between 0 and 23."
  }
}

variable "maintenance_window_update_track" {
  description = "Maintenance timing (canary or stable)"
  type        = string
  default     = "stable"

  validation {
    condition     = contains(["canary", "stable"], var.maintenance_window_update_track)
    error_message = "Maintenance window update track must be canary or stable."
  }
}

variable "deny_maintenance_period" {
  description = "Period during which maintenance is denied"
  type = object({
    start_date = string # YYYY-MM-DD
    end_date   = string # YYYY-MM-DD
    time       = string # HH:MM:SS
  })
  default = null
}

#######################
# Database Flags (PostgreSQL Configuration)
#######################

variable "database_flags" {
  description = "Map of database flags (PostgreSQL configuration parameters)"
  type        = map(string)
  default     = {}
}

variable "enable_default_database_flags" {
  description = "Enable default database flags for logging and performance monitoring. Set to false for minimal configuration."
  type        = bool
  default     = false
}

variable "enable_query_insights" {
  description = "Enable Query Insights (Performance Insights)"
  type        = bool
  default     = true
}

variable "query_insights_plans_per_minute" {
  description = "Number of query plans per minute to capture (5-20)"
  type        = number
  default     = 5

  validation {
    condition     = var.query_insights_plans_per_minute >= 5 && var.query_insights_plans_per_minute <= 20
    error_message = "Query insights plans per minute must be between 5 and 20."
  }
}

variable "query_insights_string_length" {
  description = "Maximum query string length to capture (256-4500)"
  type        = number
  default     = 1024

  validation {
    condition     = var.query_insights_string_length >= 256 && var.query_insights_string_length <= 4500
    error_message = "Query insights string length must be between 256 and 4500."
  }
}

variable "query_insights_record_app_tags" {
  description = "Record application tags in Query Insights"
  type        = bool
  default     = true
}

variable "query_insights_record_client_address" {
  description = "Record client address in Query Insights"
  type        = bool
  default     = true
}

variable "enable_slow_query_log" {
  description = "Enable slow query logging"
  type        = bool
  default     = true
}

variable "slow_query_threshold_ms" {
  description = "Slow query threshold in milliseconds"
  type        = string
  default     = "1000" # 1 second
}

variable "log_statement_level" {
  description = "Statement logging level (none, ddl, mod, all)"
  type        = string
  default     = "ddl"

  validation {
    condition     = contains(["none", "ddl", "mod", "all"], var.log_statement_level)
    error_message = "Log statement level must be none, ddl, mod, or all."
  }
}

#######################
# Databases
#######################

variable "default_database_name" {
  description = "Name of the default database to create"
  type        = string
  default     = "app"
}

variable "additional_databases" {
  description = "List of additional database names to create"
  type        = list(string)
  default     = []
}

variable "database_charset" {
  description = "Character set for databases"
  type        = string
  default     = "UTF8"
}

variable "database_collation" {
  description = "Collation for databases"
  type        = string
  default     = "en_US.UTF8"
}

variable "database_deletion_policy" {
  description = "Deletion policy for databases (ABANDON or DELETE)"
  type        = string
  default     = "DELETE"

  validation {
    condition     = contains(["ABANDON", "DELETE"], var.database_deletion_policy)
    error_message = "Database deletion policy must be ABANDON or DELETE."
  }
}

#######################
# Users
#######################

variable "create_default_user" {
  description = "Create a default admin user"
  type        = bool
  default     = true
}

variable "default_user_name" {
  description = "Name of the default admin user"
  type        = string
  default     = "postgres"
}

variable "default_user_password" {
  description = "Password for default user (leave null for auto-generated)"
  type        = string
  default     = null
  sensitive   = true
}

variable "additional_users" {
  description = "Map of additional users to create"
  type = map(object({
    password = optional(string) # null for auto-generated
    type     = optional(string) # BUILT_IN or CLOUD_IAM_SERVICE_ACCOUNT
  }))
  default   = {}
  sensitive = false # Can't be sensitive when used in for_each
}

variable "user_deletion_policy" {
  description = "Deletion policy for users (ABANDON or empty string)"
  type        = string
  default     = ""

  validation {
    condition     = contains(["ABANDON", ""], var.user_deletion_policy)
    error_message = "User deletion policy must be ABANDON or empty string."
  }
}

variable "create_proxy_user" {
  description = "Create a Cloud SQL Proxy user for Workload Identity"
  type        = bool
  default     = false
}

variable "proxy_user_name" {
  description = "Service account email for Cloud SQL Proxy user"
  type        = string
  default     = ""
}

#######################
# Read Replicas
#######################

variable "read_replica_count" {
  description = "Number of read replicas to create"
  type        = number
  default     = 0

  validation {
    condition     = var.read_replica_count >= 0 && var.read_replica_count <= 10
    error_message = "Read replica count must be between 0 and 10."
  }
}

variable "read_replica_regions" {
  description = "List of regions for read replicas (will cycle through this list)"
  type        = list(string)
  default     = []
}

variable "read_replica_tier" {
  description = "Machine type tier for read replicas (null to use same as primary)"
  type        = string
  default     = null
}

#######################
# Security
#######################

variable "kms_key_name" {
  description = "KMS key name for customer-managed encryption (CMEK)"
  type        = string
  default     = null
}

variable "enable_password_validation" {
  description = "Enable password validation policy"
  type        = bool
  default     = true
}

variable "password_min_length" {
  description = "Minimum password length"
  type        = number
  default     = 12

  validation {
    condition     = var.password_min_length >= 8 && var.password_min_length <= 128
    error_message = "Password minimum length must be between 8 and 128."
  }
}

variable "password_complexity" {
  description = "Password complexity level (COMPLEXITY_DEFAULT, COMPLEXITY_UNSPECIFIED)"
  type        = string
  default     = "COMPLEXITY_DEFAULT"

  validation {
    condition     = contains(["COMPLEXITY_DEFAULT", "COMPLEXITY_UNSPECIFIED"], var.password_complexity)
    error_message = "Password complexity must be COMPLEXITY_DEFAULT or COMPLEXITY_UNSPECIFIED."
  }
}

variable "password_reuse_interval" {
  description = "Number of previous passwords that cannot be reused (0-100)"
  type        = number
  default     = 5

  validation {
    condition     = var.password_reuse_interval >= 0 && var.password_reuse_interval <= 100
    error_message = "Password reuse interval must be between 0 and 100."
  }
}

variable "password_disallow_username" {
  description = "Disallow username as part of password"
  type        = bool
  default     = true
}

variable "active_directory_domain" {
  description = "Active Directory domain for authentication (null to disable)"
  type        = string
  default     = null
}

#######################
# Performance
#######################

variable "enable_data_cache" {
  description = "Enable data cache for improved read performance"
  type        = bool
  default     = false
}

#######################
# Monitoring
#######################

variable "enable_monitoring_alerts" {
  description = "Enable Cloud Monitoring alert policies"
  type        = bool
  default     = true
}

variable "monitoring_notification_channels" {
  description = "List of notification channel IDs for alerts"
  type        = list(string)
  default     = []
}

variable "alert_cpu_threshold" {
  description = "CPU usage threshold for alerts (percentage)"
  type        = number
  default     = 80

  validation {
    condition     = var.alert_cpu_threshold > 0 && var.alert_cpu_threshold <= 100
    error_message = "Alert CPU threshold must be between 1 and 100."
  }
}

variable "alert_memory_threshold" {
  description = "Memory usage threshold for alerts (percentage)"
  type        = number
  default     = 80

  validation {
    condition     = var.alert_memory_threshold > 0 && var.alert_memory_threshold <= 100
    error_message = "Alert memory threshold must be between 1 and 100."
  }
}

variable "alert_disk_threshold" {
  description = "Disk usage threshold for alerts (percentage)"
  type        = number
  default     = 80

  validation {
    condition     = var.alert_disk_threshold > 0 && var.alert_disk_threshold <= 100
    error_message = "Alert disk threshold must be between 1 and 100."
  }
}

variable "alert_duration_seconds" {
  description = "Duration for alert conditions (seconds)"
  type        = number
  default     = 300 # 5 minutes

  validation {
    condition     = var.alert_duration_seconds >= 60 && var.alert_duration_seconds <= 3600
    error_message = "Alert duration must be between 60 and 3600 seconds."
  }
}

#######################
# Lifecycle
#######################

variable "enable_deletion_protection" {
  description = "Enable deletion protection for the instance"
  type        = bool
  default     = true
}

variable "instance_create_timeout" {
  description = "Timeout for instance creation"
  type        = string
  default     = "30m"
}

variable "instance_update_timeout" {
  description = "Timeout for instance updates"
  type        = string
  default     = "30m"
}

variable "instance_delete_timeout" {
  description = "Timeout for instance deletion"
  type        = string
  default     = "30m"
}

#######################
# Labels
#######################

variable "labels" {
  description = "Labels to apply to the instance"
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for k, v in var.labels : can(regex("^[a-z][a-z0-9_-]{0,62}$", k))
    ])
    error_message = "Label keys must start with a lowercase letter and contain only lowercase letters, numbers, underscores, and hyphens (max 63 characters)."
  }
}
