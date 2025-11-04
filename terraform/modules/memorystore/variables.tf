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
  description = "Name of the Redis instance (leave empty to use name_prefix)"
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

variable "display_name" {
  description = "Display name for the instance"
  type        = string
  default     = ""
}

#######################
# Instance Configuration
#######################

variable "tier" {
  description = "Service tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "STANDARD_HA"

  validation {
    condition     = contains(["BASIC", "STANDARD_HA"], var.tier)
    error_message = "Tier must be BASIC or STANDARD_HA."
  }
}

variable "memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 5

  validation {
    condition     = var.memory_size_gb >= 1 && var.memory_size_gb <= 300
    error_message = "Memory size must be between 1 and 300 GB."
  }
}

variable "redis_version" {
  description = "Redis version (REDIS_6_X, REDIS_7_0, REDIS_7_2)"
  type        = string
  default     = "REDIS_7_0"

  validation {
    condition     = contains(["REDIS_4_0", "REDIS_5_0", "REDIS_6_X", "REDIS_7_0", "REDIS_7_2"], var.redis_version)
    error_message = "Redis version must be a valid version."
  }
}

variable "replica_count" {
  description = "Number of read replicas (0-5, only for STANDARD_HA tier)"
  type        = number
  default     = 1

  validation {
    condition     = var.replica_count >= 0 && var.replica_count <= 5
    error_message = "Replica count must be between 0 and 5."
  }
}

variable "read_replicas_mode" {
  description = "Read replicas mode (READ_REPLICAS_DISABLED or READ_REPLICAS_ENABLED)"
  type        = string
  default     = "READ_REPLICAS_ENABLED"

  validation {
    condition     = contains(["READ_REPLICAS_DISABLED", "READ_REPLICAS_ENABLED"], var.read_replicas_mode)
    error_message = "Read replicas mode must be READ_REPLICAS_DISABLED or READ_REPLICAS_ENABLED."
  }
}

#######################
# Network Configuration
#######################

variable "vpc_network_id" {
  description = "ID of the VPC network (e.g., projects/PROJECT/global/networks/NETWORK)"
  type        = string

  validation {
    condition     = can(regex("^projects/[^/]+/global/networks/[^/]+$", var.vpc_network_id))
    error_message = "VPC network ID must be in format: projects/PROJECT/global/networks/NETWORK."
  }
}

variable "connect_mode" {
  description = "Network connection mode (DIRECT_PEERING or PRIVATE_SERVICE_ACCESS)"
  type        = string
  default     = "DIRECT_PEERING"

  validation {
    condition     = contains(["DIRECT_PEERING", "PRIVATE_SERVICE_ACCESS"], var.connect_mode)
    error_message = "Connect mode must be DIRECT_PEERING or PRIVATE_SERVICE_ACCESS."
  }
}

variable "reserved_ip_range" {
  description = "CIDR range for Redis instance (optional, auto-allocated if not specified)"
  type        = string
  default     = null

  validation {
    condition     = var.reserved_ip_range == null || can(cidrhost(var.reserved_ip_range, 0))
    error_message = "Reserved IP range must be a valid CIDR block."
  }
}

#######################
# Security
#######################

variable "enable_transit_encryption" {
  description = "Enable in-transit encryption (TLS)"
  type        = bool
  default     = true
}

variable "enable_auth" {
  description = "Enable Redis AUTH (password authentication)"
  type        = bool
  default     = true
}

variable "customer_managed_key" {
  description = "KMS key name for customer-managed encryption (CMEK)"
  type        = string
  default     = null
}

#######################
# Maintenance
#######################

variable "maintenance_window_day" {
  description = "Day of week for maintenance (1=Monday, 7=Sunday, null=any day)"
  type        = number
  default     = 7 # Sunday

  validation {
    condition     = var.maintenance_window_day == null || (var.maintenance_window_day >= 1 && var.maintenance_window_day <= 7)
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

variable "maintenance_window_minute" {
  description = "Minute of hour for maintenance (0-59)"
  type        = number
  default     = 0

  validation {
    condition     = var.maintenance_window_minute >= 0 && var.maintenance_window_minute <= 59
    error_message = "Maintenance window minute must be between 0 and 59."
  }
}

variable "maintenance_version" {
  description = "Maintenance version (LATEST or specific version)"
  type        = string
  default     = null
}

#######################
# Persistence
#######################

variable "enable_persistence" {
  description = "Enable data persistence"
  type        = bool
  default     = true
}

variable "persistence_mode" {
  description = "Persistence mode (RDB or AOF)"
  type        = string
  default     = "RDB"

  validation {
    condition     = contains(["RDB", "AOF"], var.persistence_mode)
    error_message = "Persistence mode must be RDB or AOF."
  }
}

variable "rdb_snapshot_period" {
  description = "RDB snapshot period (ONE_HOUR, SIX_HOURS, TWELVE_HOURS, TWENTY_FOUR_HOURS)"
  type        = string
  default     = "TWELVE_HOURS"

  validation {
    condition     = contains(["ONE_HOUR", "SIX_HOURS", "TWELVE_HOURS", "TWENTY_FOUR_HOURS"], var.rdb_snapshot_period)
    error_message = "RDB snapshot period must be ONE_HOUR, SIX_HOURS, TWELVE_HOURS, or TWENTY_FOUR_HOURS."
  }
}

variable "rdb_snapshot_start_time" {
  description = "RDB snapshot start time (RFC3339 format)"
  type        = string
  default     = null
}

#######################
# Redis Configuration
#######################

variable "redis_configs" {
  description = "Map of Redis configuration parameters"
  type        = map(string)
  default     = {}
}

variable "maxmemory_policy" {
  description = "Eviction policy when maxmemory is reached"
  type        = string
  default     = "allkeys-lru"

  validation {
    condition = contains([
      "noeviction", "allkeys-lru", "allkeys-lfu", "allkeys-random",
      "volatile-lru", "volatile-lfu", "volatile-random", "volatile-ttl"
    ], var.maxmemory_policy)
    error_message = "Maxmemory policy must be a valid Redis eviction policy."
  }
}

variable "timeout_seconds" {
  description = "Close connection after client is idle for N seconds (0 to disable)"
  type        = number
  default     = 0

  validation {
    condition     = var.timeout_seconds >= 0 && var.timeout_seconds <= 3600
    error_message = "Timeout must be between 0 and 3600 seconds."
  }
}

variable "enable_notifications" {
  description = "Enable keyspace notifications"
  type        = bool
  default     = false
}

variable "notification_events" {
  description = "Keyspace notification events (e.g., 'Ex' for expired keys)"
  type        = string
  default     = ""
}

#######################
# Cross-Region Read Replicas
#######################

variable "create_cross_region_replica" {
  description = "Create read replicas in other regions"
  type        = bool
  default     = false
}

variable "read_replica_regions" {
  description = "List of regions for cross-region read replicas"
  type        = list(string)
  default     = []
}

variable "read_replica_memory_size_gb" {
  description = "Memory size for read replicas (null to use same as primary)"
  type        = number
  default     = null

  validation {
    condition     = var.read_replica_memory_size_gb == null || try(var.read_replica_memory_size_gb >= 1 && var.read_replica_memory_size_gb <= 300, false)
    error_message = "Read replica memory size must be between 1 and 300 GB."
  }
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

variable "alert_memory_threshold" {
  description = "Memory usage threshold for alerts (percentage)"
  type        = number
  default     = 80

  validation {
    condition     = var.alert_memory_threshold > 0 && var.alert_memory_threshold <= 100
    error_message = "Alert memory threshold must be between 1 and 100."
  }
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

variable "alert_connections_threshold" {
  description = "Connection count threshold for alerts"
  type        = number
  default     = 5000

  validation {
    condition     = var.alert_connections_threshold > 0
    error_message = "Alert connections threshold must be positive."
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
  default     = "20m"
}

variable "instance_update_timeout" {
  description = "Timeout for instance updates"
  type        = string
  default     = "20m"
}

variable "instance_delete_timeout" {
  description = "Timeout for instance deletion"
  type        = string
  default     = "20m"
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
