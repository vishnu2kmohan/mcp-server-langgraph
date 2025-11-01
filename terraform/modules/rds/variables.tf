variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "db_identifier" {
  description = "Custom database identifier (if empty, uses name_prefix-postgres)"
  type        = string
  default     = ""
}

variable "vpc_id" {
  description = "VPC ID where RDS will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for DB subnet group (must be in different AZs for Multi-AZ)"
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnets in different AZs are required."
  }
}

#######################
# Database Configuration
#######################

variable "engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.4"

  validation {
    condition     = can(regex("^1[4-6]\\.", var.engine_version))
    error_message = "Engine version must be PostgreSQL 14.x, 15.x, or 16.x."
  }
}

variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 100

  validation {
    condition     = var.allocated_storage >= 20 && var.allocated_storage <= 65536
    error_message = "Allocated storage must be between 20 and 65536 GB."
  }
}

variable "max_allocated_storage" {
  description = "Maximum storage for autoscaling (0 to disable)"
  type        = number
  default     = 1000

  validation {
    condition     = var.max_allocated_storage == 0 || var.max_allocated_storage >= 100
    error_message = "Max allocated storage must be 0 (disabled) or >= 100 GB."
  }
}

variable "storage_type" {
  description = "Storage type (gp2, gp3, io1, io2)"
  type        = string
  default     = "gp3"

  validation {
    condition     = contains(["gp2", "gp3", "io1", "io2"], var.storage_type)
    error_message = "Storage type must be gp2, gp3, io1, or io2."
  }
}

variable "iops" {
  description = "IOPS for io1/io2 storage (required for io1/io2)"
  type        = number
  default     = null
}

variable "storage_throughput" {
  description = "Storage throughput in MB/s for gp3 (125-1000)"
  type        = number
  default     = 125

  validation {
    condition     = var.storage_throughput >= 125 && var.storage_throughput <= 1000
    error_message = "Storage throughput must be between 125 and 1000 MB/s."
  }
}

variable "database_name" {
  description = "Name of the initial database to create"
  type        = string
  default     = "postgres"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.database_name))
    error_message = "Database name must start with a letter and contain only alphanumeric characters and underscores."
  }
}

variable "master_username" {
  description = "Master username for database"
  type        = string
  default     = "postgres"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]*$", var.master_username))
    error_message = "Username must start with a letter and contain only alphanumeric characters and underscores."
  }
}

variable "master_password" {
  description = "Master password (if empty, generates random password)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "database_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

#######################
# High Availability
#######################

variable "multi_az" {
  description = "Enable Multi-AZ deployment for high availability"
  type        = bool
  default     = true
}

variable "availability_zone" {
  description = "AZ for single-AZ deployment (ignored if multi_az is true)"
  type        = string
  default     = null
}

#######################
# Backup Configuration
#######################

variable "backup_retention_period" {
  description = "Backup retention period in days (0-35)"
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_period >= 0 && var.backup_retention_period <= 35
    error_message = "Backup retention period must be between 0 and 35 days."
  }
}

variable "backup_window" {
  description = "Preferred backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot when destroying (NOT recommended for production)"
  type        = bool
  default     = false
}

variable "delete_automated_backups" {
  description = "Delete automated backups when instance is deleted"
  type        = bool
  default     = false
}

#######################
# Maintenance
#######################

variable "maintenance_window" {
  description = "Preferred maintenance window (UTC)"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "auto_minor_version_upgrade" {
  description = "Automatically upgrade minor versions"
  type        = bool
  default     = true
}

variable "allow_major_version_upgrade" {
  description = "Allow major version upgrades"
  type        = bool
  default     = false
}

variable "apply_immediately" {
  description = "Apply changes immediately (may cause downtime)"
  type        = bool
  default     = false
}

#######################
# Monitoring
#######################

variable "enable_enhanced_monitoring" {
  description = "Enable enhanced monitoring"
  type        = bool
  default     = true
}

variable "monitoring_interval" {
  description = "Enhanced monitoring interval in seconds (0, 1, 5, 10, 15, 30, 60)"
  type        = number
  default     = 60

  validation {
    condition     = contains([0, 1, 5, 10, 15, 30, 60], var.monitoring_interval)
    error_message = "Monitoring interval must be 0, 1, 5, 10, 15, 30, or 60 seconds."
  }
}

variable "enable_performance_insights" {
  description = "Enable Performance Insights"
  type        = bool
  default     = true
}

variable "performance_insights_retention_period" {
  description = "Performance Insights retention period in days (7 or 731)"
  type        = number
  default     = 7

  validation {
    condition     = contains([7, 731], var.performance_insights_retention_period)
    error_message = "Performance Insights retention must be 7 or 731 days."
  }
}

variable "enabled_cloudwatch_logs_exports" {
  description = "List of log types to export to CloudWatch (postgresql, upgrade)"
  type        = list(string)
  default     = ["postgresql", "upgrade"]

  validation {
    condition = alltrue([
      for log in var.enabled_cloudwatch_logs_exports :
      contains(["postgresql", "upgrade"], log)
    ])
    error_message = "Log types must be postgresql or upgrade."
  }
}

variable "cloudwatch_log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cloudwatch_log_retention_days)
    error_message = "Log retention must be a valid CloudWatch retention period."
  }
}

variable "cloudwatch_log_kms_key_id" {
  description = "KMS key ID for encrypting CloudWatch logs"
  type        = string
  default     = null
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

#######################
# Security
#######################

variable "kms_key_id" {
  description = "KMS key ID for encryption (if null, creates new key)"
  type        = string
  default     = null
}

variable "publicly_accessible" {
  description = "Make database publicly accessible (NOT recommended)"
  type        = bool
  default     = false
}

variable "deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = true
}

variable "enable_iam_database_authentication" {
  description = "Enable IAM database authentication"
  type        = bool
  default     = true
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access database"
  type        = list(string)
  default     = []
}

variable "allowed_security_group_ids" {
  description = "Security group IDs allowed to access database"
  type        = list(string)
  default     = []
}

variable "additional_security_group_ids" {
  description = "Additional security groups to attach to RDS instance"
  type        = list(string)
  default     = []
}

#######################
# Parameter Group
#######################

variable "parameter_group_family" {
  description = "DB parameter group family"
  type        = string
  default     = "postgres16"
}

variable "db_parameters" {
  description = "Additional database parameters"
  type = list(object({
    name         = string
    value        = string
    apply_method = optional(string, "immediate")
  }))
  default = []
}

#######################
# CloudWatch Alarms
#######################

variable "create_cloudwatch_alarms" {
  description = "Create CloudWatch alarms for database metrics"
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
  default     = 80
}

variable "alarm_memory_threshold_bytes" {
  description = "Freeable memory alarm threshold in bytes"
  type        = number
  default     = 536870912 # 512 MB
}

variable "alarm_storage_threshold_bytes" {
  description = "Free storage space alarm threshold in bytes"
  type        = number
  default     = 10737418240 # 10 GB
}

variable "alarm_connections_threshold" {
  description = "Database connections alarm threshold"
  type        = number
  default     = 80 # Will vary by instance class
}

#######################
# Tags
#######################

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
