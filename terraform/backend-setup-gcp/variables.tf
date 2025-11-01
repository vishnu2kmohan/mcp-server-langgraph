variable "project_id" {
  description = "GCP project ID for the backend resources"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Project ID must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "region" {
  description = "GCP region for the backend resources"
  type        = string
  default     = "us-central1"

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

variable "bucket_prefix" {
  description = "Prefix for the GCS bucket name (must be globally unique)"
  type        = string
  default     = "mcp-langgraph"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_prefix))
    error_message = "Bucket prefix must be 3-63 characters, contain only lowercase letters, numbers, and hyphens, and start/end with a letter or number."
  }
}

variable "terraform_service_account" {
  description = "Service account email that will manage Terraform state (optional, for IAM bindings)"
  type        = string
  default     = ""

  validation {
    condition     = var.terraform_service_account == "" || can(regex("^[a-z0-9-]+@[a-z0-9-]+\\.iam\\.gserviceaccount\\.com$", var.terraform_service_account))
    error_message = "Service account must be a valid GCP service account email or empty string."
  }
}

variable "enable_cmek" {
  description = "Enable Customer-Managed Encryption Keys (CMEK) for GCS buckets"
  type        = bool
  default     = false
}

variable "kms_key_name" {
  description = "KMS key name for customer-managed encryption (required if enable_cmek is true)"
  type        = string
  default     = ""

  validation {
    condition     = !var.enable_cmek || (var.enable_cmek && var.kms_key_name != "")
    error_message = "KMS key name must be provided when enable_cmek is true."
  }
}

variable "log_retention_days" {
  description = "Number of days to retain access logs before deletion"
  type        = number
  default     = 90

  validation {
    condition     = var.log_retention_days >= 1 && var.log_retention_days <= 3650
    error_message = "Log retention days must be between 1 and 3650 (10 years)."
  }
}

variable "state_version_retention" {
  description = "Number of newer versions to keep before deleting old archived versions"
  type        = number
  default     = 10

  validation {
    condition     = var.state_version_retention >= 1
    error_message = "State version retention must be at least 1."
  }
}

variable "labels" {
  description = "Additional labels to apply to all resources"
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for k, v in var.labels : can(regex("^[a-z][a-z0-9_-]{0,62}$", k))
    ])
    error_message = "Label keys must start with a lowercase letter and contain only lowercase letters, numbers, underscores, and hyphens (max 63 characters)."
  }
}
