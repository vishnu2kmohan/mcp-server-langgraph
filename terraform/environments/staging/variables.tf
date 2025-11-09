# Staging Environment Variables

variable "gcp_project_id" {
  description = "GCP Project ID for staging environment"
  type        = string
  default     = "vishnu-sandbox-20250310"
}

variable "gcp_region" {
  description = "GCP Region for staging resources"
  type        = string
  default     = "us-central1"
}

variable "vpc_network_name" {
  description = "Name of the VPC network"
  type        = string
  default     = "default"
}

variable "cloud_sql_instance_name" {
  description = "Name of the Cloud SQL instance"
  type        = string
  default     = "staging-postgres"
}

variable "redis_instance_name" {
  description = "Name of the primary Memorystore Redis instance"
  type        = string
  default     = "staging-redis"
}

variable "redis_session_instance_name" {
  description = "Name of the Redis session store instance"
  type        = string
  default     = "staging-redis-session"
}

variable "create_postgres_cname" {
  description = "Whether to create postgres-staging.internal CNAME"
  type        = bool
  default     = false
}

variable "dns_ttl" {
  description = "TTL for DNS records in seconds (lower = faster failover, higher = less queries)"
  type        = number
  default     = 300
}
