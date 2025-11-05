# ============================================================================
# GCP Secret Manager Module - Variables
# ============================================================================

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "replication_policy" {
  description = "Secret replication policy (automatic or user-managed)"
  type        = string
  default     = "automatic"

  validation {
    condition     = contains(["automatic", "user-managed"], var.replication_policy)
    error_message = "Replication policy must be 'automatic' or 'user-managed'."
  }
}

variable "external_secrets_service_account" {
  description = "Service account email for External Secrets Operator"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+@[a-z0-9-]+\\.iam\\.gserviceaccount\\.com$", var.external_secrets_service_account))
    error_message = "Must be a valid GCP service account email."
  }
}

variable "app_service_account" {
  description = "Application service account email (optional - for direct secret access)"
  type        = string
  default     = ""
}

variable "labels" {
  description = "Labels to apply to all secrets"
  type        = map(string)
  default     = {}
}
