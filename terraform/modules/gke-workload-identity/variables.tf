variable "project_id" {
  description = "GCP project ID"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Project ID must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "namespace" {
  description = "Kubernetes namespace for the service accounts"
  type        = string

  validation {
    condition     = length(var.namespace) > 0 && length(var.namespace) <= 63
    error_message = "Namespace must be 1-63 characters."
  }
}

variable "service_accounts" {
  description = "Map of Kubernetes service accounts to create with their GCP service account configurations"
  type = map(object({
    gcp_sa_name  = string                    # GCP service account name (e.g., "app-sa")
    display_name = optional(string)          # Display name for the GCP SA
    description  = optional(string)          # Description for the GCP SA
    roles        = list(string)              # List of project-level IAM roles to grant

    # Optional: Cloud SQL access
    cloudsql_access = optional(bool, false)

    # Optional: Secret Manager secrets access
    secret_ids = optional(list(string), [])

    # Optional: Storage bucket access
    bucket_access = optional(list(object({
      bucket_name = string
      role        = string  # e.g., "roles/storage.objectViewer"
    })), [])

    # Optional: BigQuery dataset access
    bigquery_access = optional(list(object({
      dataset_id = string
      role       = string  # e.g., "roles/bigquery.dataViewer"
    })), [])

    # Optional: Pub/Sub topic access
    pubsub_topics = optional(list(object({
      topic = string
      role  = string  # e.g., "roles/pubsub.publisher"
    })), [])

    # Optional: Pub/Sub subscription access
    pubsub_subscriptions = optional(list(object({
      subscription = string
      role         = string  # e.g., "roles/pubsub.subscriber"
    })), [])

    # Optional: Create service account key (not recommended with Workload Identity)
    create_key = optional(bool, false)
  }))

  validation {
    condition = alltrue([
      for sa_name, sa_config in var.service_accounts :
      can(regex("^[a-z][a-z0-9-]{0,28}[a-z0-9]$", sa_config.gcp_sa_name))
    ])
    error_message = "GCP service account names must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}
