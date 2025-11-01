variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "team" {
  description = "Team name for labeling"
  type        = string
  default     = "platform"
}

variable "app_namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "mcp-staging"
}

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor for DDoS protection"
  type        = bool
  default     = false
}

variable "enable_master_authorized_networks" {
  description = "Enable master authorized networks"
  type        = bool
  default     = false  # Open access for staging
}

variable "master_authorized_networks_cidrs" {
  description = "CIDR blocks authorized to access the control plane"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = []
}

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization"
  type        = bool
  default     = false
}

variable "enable_fleet_registration" {
  description = "Register cluster with GKE Fleet"
  type        = bool
  default     = false
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false  # Allow easy teardown in staging
}

variable "monitoring_notification_channels" {
  description = "Cloud Monitoring notification channel IDs"
  type        = list(string)
  default     = []
}

variable "additional_databases" {
  description = "Additional databases to create"
  type        = list(string)
  default     = []
}

variable "cloudsql_additional_users" {
  description = "Additional PostgreSQL users"
  type = map(object({
    password = optional(string)
    type     = optional(string)
  }))
  default   = {}
  sensitive = true
}

variable "cloudsql_read_replica_count" {
  description = "Number of read replicas"
  type        = number
  default     = 0  # No replicas needed for staging
}

variable "cloudsql_read_replica_regions" {
  description = "Regions for read replicas"
  type        = list(string)
  default     = []
}

variable "app_secret_ids" {
  description = "Secret Manager secret IDs for application"
  type        = list(string)
  default     = []
}
