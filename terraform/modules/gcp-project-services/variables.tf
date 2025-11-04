#######################
# General Variables
#######################

variable "project_id" {
  description = "GCP project ID where APIs will be enabled"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Project ID must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

#######################
# Core APIs (Always Enabled)
#######################

variable "enable_container_api" {
  description = "Enable Kubernetes Engine API (required for GKE)"
  type        = bool
  default     = true
}

variable "enable_compute_api" {
  description = "Enable Compute Engine API (required for VPC, subnets, and compute resources)"
  type        = bool
  default     = true
}

#######################
# Networking APIs
#######################

variable "enable_service_networking_api" {
  description = "Enable Service Networking API (required for private service connections)"
  type        = bool
  default     = false
}

#######################
# GKE Feature APIs
#######################

variable "enable_gke_backup_api" {
  description = "Enable GKE Backup API (required for cluster backup plans)"
  type        = bool
  default     = false
}

variable "enable_container_scanning_api" {
  description = "Enable Container Scanning API (required for vulnerability scanning)"
  type        = bool
  default     = false
}

#######################
# Secret Management APIs
#######################

variable "enable_secret_manager_api" {
  description = "Enable Secret Manager API (required for Workload Identity secret access)"
  type        = bool
  default     = false
}

#######################
# Database APIs
#######################

variable "enable_sql_admin_api" {
  description = "Enable Cloud SQL Admin API (required for Cloud SQL instances)"
  type        = bool
  default     = false
}

variable "enable_redis_api" {
  description = "Enable Memorystore for Redis API (required for Redis instances)"
  type        = bool
  default     = false
}

#######################
# Monitoring & Logging APIs
#######################

variable "enable_monitoring_api" {
  description = "Enable Cloud Monitoring API (required for metrics and alerting)"
  type        = bool
  default     = false
}

variable "enable_logging_api" {
  description = "Enable Cloud Logging API (required for log exports)"
  type        = bool
  default     = false
}

#######################
# API Management
#######################

variable "disable_on_destroy" {
  description = "Whether to disable APIs when the resource is destroyed (WARNING: disabling APIs can break existing resources)"
  type        = bool
  default     = false
}

variable "disable_dependent_services" {
  description = "Whether to disable services that are enabled and depend on this service when destroying"
  type        = bool
  default     = false
}
