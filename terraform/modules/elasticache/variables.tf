variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "cluster_id" {
  description = "Custom cluster identifier (if empty, uses name_prefix-redis)"
  type        = string
  default     = ""

  validation {
    condition     = var.cluster_id == "" || can(regex("^[a-z0-9-]+$", var.cluster_id))
    error_message = "Cluster ID must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "vpc_id" {
  description = "VPC ID where ElastiCache will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for ElastiCache subnet group"
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnets are required for high availability."
  }
}

#######################
# Engine Configuration
#######################

variable "engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.1"

  validation {
    condition     = can(regex("^[67]\\.", var.engine_version))
    error_message = "Engine version must be Redis 6.x or 7.x."
  }
}

variable "port" {
  description = "Port number for Redis"
  type        = number
  default     = 6379
}

variable "parameter_group_family" {
  description = "Parameter group family"
  type        = string
  default     = "redis7"
}

variable "parameters" {
  description = "Additional Redis parameters"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "timeout" {
  description = "Close connection after client is idle for N seconds (0 = never)"
  type        = string
  default     = "300"
}

variable "maxmemory_policy" {
  description = "Eviction policy when maxmemory is reached"
  type        = string
  default     = "allkeys-lru"

  validation {
    condition = contains([
      "allkeys-lru", "allkeys-lfu", "allkeys-random",
      "volatile-lru", "volatile-lfu", "volatile-random", "volatile-ttl",
      "noeviction"
    ], var.maxmemory_policy)
    error_message = "Invalid maxmemory policy."
  }
}

#######################
# Cluster Configuration
#######################

variable "cluster_mode_enabled" {
  description = "Enable cluster mode for sharding (recommended for production)"
  type        = bool
  default     = true
}

variable "node_type" {
  description = "Node instance type"
  type        = string
  default     = "cache.t3.medium"
}

# Cluster mode settings
variable "num_node_groups" {
  description = "Number of node groups (shards) - cluster mode only"
  type        = number
  default     = 3

  validation {
    condition     = var.num_node_groups >= 1 && var.num_node_groups <= 500
    error_message = "Number of node groups must be between 1 and 500."
  }
}

variable "replicas_per_node_group" {
  description = "Number of replica nodes per shard - cluster mode only"
  type        = number
  default     = 2

  validation {
    condition     = var.replicas_per_node_group >= 0 && var.replicas_per_node_group <= 5
    error_message = "Replicas per node group must be between 0 and 5."
  }
}

# Non-cluster mode settings
variable "num_cache_clusters" {
  description = "Number of cache clusters (nodes) - non-cluster mode only"
  type        = number
  default     = 3

  validation {
    condition     = var.num_cache_clusters >= 1 && var.num_cache_clusters <= 6
    error_message = "Number of cache clusters must be between 1 and 6."
  }
}

#######################
# High Availability
#######################

variable "multi_az_enabled" {
  description = "Enable Multi-AZ with automatic failover"
  type        = bool
  default     = true
}

variable "automatic_failover_enabled" {
  description = "Enable automatic failover (required for Multi-AZ)"
  type        = bool
  default     = true
}

#######################
# Encryption
#######################

variable "at_rest_encryption_enabled" {
  description = "Enable encryption at rest"
  type        = bool
  default     = true
}

variable "transit_encryption_enabled" {
  description = "Enable encryption in transit (TLS)"
  type        = bool
  default     = true
}

variable "auth_token" {
  description = "Auth token for Redis (required when transit encryption enabled, auto-generated if empty)"
  type        = string
  default     = ""
  sensitive   = true

  validation {
    condition     = var.auth_token == "" || (length(var.auth_token) >= 16 && length(var.auth_token) <= 128)
    error_message = "Auth token must be between 16 and 128 characters if provided."
  }
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (if null, creates new key)"
  type        = string
  default     = null
}

#######################
# Maintenance
#######################

variable "maintenance_window" {
  description = "Maintenance window (UTC)"
  type        = string
  default     = "sun:05:00-sun:06:00"
}

variable "auto_minor_version_upgrade" {
  description = "Automatically upgrade minor versions"
  type        = bool
  default     = true
}

variable "apply_immediately" {
  description = "Apply changes immediately (may cause downtime)"
  type        = bool
  default     = false
}

#######################
# Backup
#######################

variable "enable_snapshot" {
  description = "Enable automated snapshots"
  type        = bool
  default     = true
}

variable "snapshot_retention_limit" {
  description = "Number of days to retain snapshots (0-35)"
  type        = number
  default     = 7

  validation {
    condition     = var.snapshot_retention_limit >= 0 && var.snapshot_retention_limit <= 35
    error_message = "Snapshot retention must be between 0 and 35 days."
  }
}

variable "snapshot_window" {
  description = "Daily snapshot window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "enable_final_snapshot" {
  description = "Create final snapshot when destroying"
  type        = bool
  default     = true
}

#######################
# Monitoring & Logging
#######################

variable "enable_slow_log" {
  description = "Enable slow log to CloudWatch"
  type        = bool
  default     = true
}

variable "enable_engine_log" {
  description = "Enable engine log to CloudWatch"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be a valid CloudWatch retention period."
  }
}

variable "cloudwatch_log_kms_key_id" {
  description = "KMS key ID for encrypting CloudWatch logs"
  type        = string
  default     = null
}

variable "notification_topic_arn" {
  description = "SNS topic ARN for ElastiCache notifications"
  type        = string
  default     = null
}

#######################
# Security
#######################

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access Redis"
  type        = list(string)
  default     = []
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed to access Redis"
  type        = list(string)
  default     = []
}

variable "additional_security_group_ids" {
  description = "Additional security groups to attach"
  type        = list(string)
  default     = []
}

#######################
# CloudWatch Alarms
#######################

variable "create_cloudwatch_alarms" {
  description = "Create CloudWatch alarms"
  type        = bool
  default     = true
}

variable "alarm_sns_topic_arns" {
  description = "SNS topic ARNs for alarm notifications"
  type        = list(string)
  default     = []
}

variable "alarm_cpu_threshold" {
  description = "CPU utilization alarm threshold (percentage)"
  type        = number
  default     = 75
}

variable "alarm_memory_threshold" {
  description = "Memory utilization alarm threshold (percentage)"
  type        = number
  default     = 90
}

variable "alarm_evictions_threshold" {
  description = "Evictions alarm threshold (count per 5 minutes)"
  type        = number
  default     = 1000
}

variable "alarm_replication_lag_threshold" {
  description = "Replication lag alarm threshold (seconds)"
  type        = number
  default     = 30
}

#######################
# Tags
#######################

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
