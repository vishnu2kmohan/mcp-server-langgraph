# Azure Database for PostgreSQL Flexible Server - Variables

#######################
# Basic Configuration
#######################

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "server_name" {
  description = "Name of the PostgreSQL server (if not using prefix)"
  type        = string
  default     = ""
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "location" {
  description = "Azure region for the database"
  type        = string
}

variable "postgres_version" {
  description = "PostgreSQL version (11, 12, 13, 14, 15, 16)"
  type        = string
  default     = "16"

  validation {
    condition     = contains(["11", "12", "13", "14", "15", "16"], var.postgres_version)
    error_message = "PostgreSQL version must be 11, 12, 13, 14, 15, or 16"
  }
}

variable "sku_name" {
  description = "SKU name for the database (e.g., B_Standard_B1ms, GP_Standard_D2s_v3, MO_Standard_E4s_v3)"
  type        = string
  default     = "GP_Standard_D2s_v3"
}

#######################
# Storage
#######################

variable "storage_mb" {
  description = "Storage size in MB (32768-16777216)"
  type        = number
  default     = 32768 # 32 GB

  validation {
    condition     = var.storage_mb >= 32768 && var.storage_mb <= 16777216
    error_message = "Storage must be between 32 GB and 16 TB (32768-16777216 MB)"
  }
}

variable "storage_tier" {
  description = "Storage tier (P4, P6, P10, P15, P20, P30, P40, P50, P60, P70, P80)"
  type        = string
  default     = "P10"
}

variable "auto_grow_enabled" {
  description = "Enable storage auto-grow"
  type        = bool
  default     = true
}

#######################
# High Availability
#######################

variable "enable_high_availability" {
  description = "Enable zone-redundant high availability"
  type        = bool
  default     = true
}

variable "high_availability_mode" {
  description = "High availability mode (ZoneRedundant or SameZone)"
  type        = string
  default     = "ZoneRedundant"

  validation {
    condition     = contains(["ZoneRedundant", "SameZone"], var.high_availability_mode)
    error_message = "HA mode must be ZoneRedundant or SameZone"
  }
}

variable "availability_zone" {
  description = "Availability zone for non-HA deployments (1, 2, or 3)"
  type        = string
  default     = "1"
}

variable "standby_availability_zone" {
  description = "Availability zone for standby server in HA mode"
  type        = string
  default     = "2"
}

#######################
# Backup
#######################

variable "backup_retention_days" {
  description = "Backup retention in days (7-35)"
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_days >= 7 && var.backup_retention_days <= 35
    error_message = "Backup retention must be between 7 and 35 days"
  }
}

variable "geo_redundant_backup_enabled" {
  description = "Enable geo-redundant backup"
  type        = bool
  default     = true
}

#######################
# Authentication
#######################

variable "admin_username" {
  description = "Administrator username"
  type        = string
  default     = "psqladmin"
}

variable "admin_password" {
  description = "Administrator password (leave empty to auto-generate)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "enable_azure_ad_auth" {
  description = "Enable Azure AD authentication"
  type        = bool
  default     = true
}

variable "enable_password_auth" {
  description = "Enable password authentication (in addition to Azure AD)"
  type        = bool
  default     = true
}

variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
  default     = null
}

#######################
# Networking
#######################

variable "delegated_subnet_id" {
  description = "ID of the delegated subnet for VNet integration"
  type        = string
  default     = null
}

variable "private_dns_zone_id" {
  description = "ID of the private DNS zone for VNet integration"
  type        = string
  default     = null
}

variable "public_network_access_enabled" {
  description = "Enable public network access"
  type        = bool
  default     = false
}

variable "allowed_ip_ranges" {
  description = "Map of allowed IP ranges (only if public access enabled)"
  type = map(object({
    start_ip = string
    end_ip   = string
  }))
  default = {}
}

variable "allow_azure_services" {
  description = "Allow Azure services to access the server"
  type        = bool
  default     = false
}

#######################
# Database Configuration
#######################

variable "default_database_name" {
  description = "Name of the default database"
  type        = string
  default     = "app"
}

variable "additional_databases" {
  description = "List of additional databases to create"
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
  default     = "en_US.utf8"
}

#######################
# PostgreSQL Configurations
#######################

variable "postgresql_configurations" {
  description = "PostgreSQL server configurations"
  type        = map(string)
  default     = {}
}

variable "enable_query_insights" {
  description = "Enable query insights logging"
  type        = bool
  default     = true
}

variable "enable_slow_query_log" {
  description = "Enable slow query logging"
  type        = bool
  default     = true
}

variable "slow_query_threshold_ms" {
  description = "Threshold for slow query logging (ms)"
  type        = number
  default     = 1000
}

#######################
# Encryption
#######################

variable "cmk_key_vault_key_id" {
  description = "Key Vault key ID for customer-managed encryption"
  type        = string
  default     = null
}

variable "primary_user_assigned_identity_id" {
  description = "User-assigned identity ID for customer-managed keys"
  type        = string
  default     = null
}

#######################
# Maintenance Window
#######################

variable "maintenance_window" {
  description = "Maintenance window configuration"
  type = object({
    day_of_week  = number
    start_hour   = number
    start_minute = number
  })
  default = null
}

#######################
# Monitoring
#######################

variable "enable_diagnostic_settings" {
  description = "Enable diagnostic settings"
  type        = bool
  default     = true
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostics"
  type        = string
  default     = null
}

variable "diagnostic_metrics" {
  description = "List of metrics to collect"
  type        = list(string)
  default     = ["AllMetrics"]
}

variable "diagnostic_logs" {
  description = "List of log categories to collect"
  type        = list(string)
  default     = ["PostgreSQLLogs"]
}

variable "enable_monitoring_alerts" {
  description = "Enable Azure Monitor alerts"
  type        = bool
  default     = true
}

variable "action_group_id" {
  description = "Action group ID for alerts"
  type        = string
  default     = null
}

variable "alert_cpu_threshold" {
  description = "CPU usage threshold for alerts (%)"
  type        = number
  default     = 80
}

variable "alert_memory_threshold" {
  description = "Memory usage threshold for alerts (%)"
  type        = number
  default     = 85
}

variable "alert_storage_threshold" {
  description = "Storage usage threshold for alerts (%)"
  type        = number
  default     = 85
}

variable "alert_connection_failures_threshold" {
  description = "Connection failures threshold for alerts"
  type        = number
  default     = 10
}

#######################
# Read Replicas
#######################

variable "read_replica_count" {
  description = "Number of read replicas to create"
  type        = number
  default     = 0
}

variable "read_replica_locations" {
  description = "Azure regions for read replicas"
  type        = list(string)
  default     = []
}

variable "read_replica_sku_name" {
  description = "SKU for read replicas (leave empty to use same as primary)"
  type        = string
  default     = ""
}

variable "read_replica_zones" {
  description = "Availability zones for read replicas"
  type        = list(string)
  default     = null
}

#######################
# Tags
#######################

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
