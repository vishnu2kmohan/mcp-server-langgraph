# ============================================================================
# GitHub Actions Workload Identity Federation - Variables
# ============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "project_number" {
  description = "GCP Project Number (numeric ID)"
  type        = string
}

variable "pool_id" {
  description = "Workload Identity Pool ID"
  type        = string
  default     = "github-actions-pool"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{3,31}$", var.pool_id))
    error_message = "Pool ID must be 4-32 characters, start with a lowercase letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "pool_display_name" {
  description = "Display name for the Workload Identity Pool"
  type        = string
  default     = "GitHub Actions Pool"
}

variable "pool_description" {
  description = "Description for the Workload Identity Pool"
  type        = string
  default     = "Workload Identity Pool for GitHub Actions authentication"
}

variable "provider_id" {
  description = "Workload Identity Provider ID"
  type        = string
  default     = "github-actions-provider"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{3,31}$", var.provider_id))
    error_message = "Provider ID must be 4-32 characters, start with a lowercase letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "provider_display_name" {
  description = "Display name for the Workload Identity Provider"
  type        = string
  default     = "GitHub Actions OIDC Provider"
}

variable "provider_description" {
  description = "Description for the Workload Identity Provider"
  type        = string
  default     = "OIDC provider for GitHub Actions"
}

variable "github_repository_owner" {
  description = "GitHub repository owner/organization (e.g., 'vishnu2kmohan')"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9-]+$", var.github_repository_owner))
    error_message = "Repository owner must contain only alphanumeric characters and hyphens."
  }
}

variable "service_accounts" {
  description = <<-EOT
    Map of service accounts to create for GitHub Actions.
    Each service account can specify:
    - account_id: Service account ID (required)
    - display_name: Human-readable name (required)
    - description: Service account description (required)
    - repository_filter: Restrict to specific repository (optional, e.g., "mcp-server-langgraph")
    - project_roles: List of project-level IAM roles to grant (optional)
    - artifact_registry_repositories: List of Artifact Registry repositories to grant access (optional)
    - storage_buckets: List of GCS buckets to grant access (optional)
    - secret_ids: List of Secret Manager secrets to grant access (optional)
  EOT

  type = map(object({
    account_id        = string
    display_name      = string
    description       = string
    repository_filter = optional(string)
    project_roles     = optional(list(string), [])

    # Artifact Registry access
    artifact_registry_repositories = optional(list(object({
      location   = string
      repository = string
      role       = string
    })), [])

    # Storage bucket access
    storage_buckets = optional(list(object({
      bucket_name = string
      role        = string
    })), [])

    # Secret Manager access
    secret_ids = optional(list(string), [])
  }))

  validation {
    condition = alltrue([
      for sa in values(var.service_accounts) :
      can(regex("^[a-z][a-z0-9-]{5,29}$", sa.account_id))
    ])
    error_message = "Service account IDs must be 6-30 characters, start with a lowercase letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "enable_apis" {
  description = "Whether to enable required APIs (iam, iamcredentials, sts)"
  type        = bool
  default     = true
}
