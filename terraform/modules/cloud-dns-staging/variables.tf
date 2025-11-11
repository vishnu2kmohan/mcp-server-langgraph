# Cloud DNS Staging Module - Input Variables

variable "gcp_project_id" {
  description = "GCP Project ID where Cloud DNS zone will be created"
  type        = string

  validation {
    condition     = length(var.gcp_project_id) > 0
    error_message = "GCP Project ID cannot be empty"
  }
}

variable "vpc_network_self_link" {
  description = "Self-link of the VPC network where private DNS zone should be visible (e.g., projects/my-project/global/networks/default)"
  type        = string

  validation {
    condition     = can(regex("^projects/.*/global/networks/.*$", var.vpc_network_self_link))
    error_message = "VPC network self-link must be in format: projects/PROJECT_ID/global/networks/NETWORK_NAME"
  }
}

variable "cloud_sql_private_ip" {
  description = "Private IP address of the Cloud SQL PostgreSQL instance"
  type        = string

  validation {
    condition     = can(regex("^10\\..*|^172\\.(1[6-9]|2[0-9]|3[01])\\..*|^192\\.168\\..*", var.cloud_sql_private_ip))
    error_message = "Cloud SQL IP must be a valid private IP address (10.x, 172.16-31.x, or 192.168.x)"
  }
}

variable "memorystore_redis_host" {
  description = "IP address of the primary Memorystore Redis instance"
  type        = string

  validation {
    condition     = can(regex("^10\\..*|^172\\.(1[6-9]|2[0-9]|3[01])\\..*|^192\\.168\\..*", var.memorystore_redis_host))
    error_message = "Redis host must be a valid private IP address"
  }
}

variable "memorystore_redis_session_host" {
  description = "IP address of the Memorystore Redis session store instance"
  type        = string

  validation {
    condition     = can(regex("^10\\..*|^172\\.(1[6-9]|2[0-9]|3[01])\\..*|^192\\.168\\..*", var.memorystore_redis_session_host))
    error_message = "Redis session host must be a valid private IP address"
  }
}

variable "create_postgres_cname" {
  description = "Whether to create a postgres-staging.internal CNAME pointing to cloudsql-staging.internal"
  type        = bool
  default     = false
}

variable "dns_ttl" {
  description = "TTL for DNS records in seconds"
  type        = number
  default     = 300

  validation {
    condition     = var.dns_ttl >= 60 && var.dns_ttl <= 86400
    error_message = "DNS TTL must be between 60 seconds (1 min) and 86400 seconds (24 hours)"
  }
}
