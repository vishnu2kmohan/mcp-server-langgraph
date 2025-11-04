# ============================================================================
# GitHub Actions Workload Identity Federation Module
# ============================================================================
#
# This module configures Workload Identity Federation (WIF) for keyless
# authentication from GitHub Actions to Google Cloud Platform.
#
# It creates:
# - Workload Identity Pool (for GitHub Actions OIDC)
# - Workload Identity Provider (configured for GitHub's OIDC issuer)
# - Service Accounts for GitHub Actions workflows
# - IAM bindings to allow GitHub Actions to impersonate service accounts
# - Project-level and resource-level IAM permissions
#
# ============================================================================

terraform {
  required_version = ">= 1.3"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

locals {
  # Full provider resource name
  workload_identity_provider_name = "projects/${var.project_number}/locations/global/workloadIdentityPools/${var.pool_id}/providers/${var.provider_id}"
}

# ============================================================================
# Workload Identity Pool
# ============================================================================

resource "google_iam_workload_identity_pool" "github_actions" {
  project                   = var.project_id
  workload_identity_pool_id = var.pool_id
  display_name              = var.pool_display_name
  description               = var.pool_description
  disabled                  = false
}

# ============================================================================
# Workload Identity Provider (GitHub Actions OIDC)
# ============================================================================

resource "google_iam_workload_identity_pool_provider" "github_actions" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_actions.workload_identity_pool_id
  workload_identity_pool_provider_id = var.provider_id
  display_name                       = var.provider_display_name
  description                        = var.provider_description
  disabled                           = false

  # GitHub Actions OIDC issuer
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  # Attribute mapping from GitHub OIDC token to Google Cloud attributes
  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }

  # Condition to restrict access to specific repository owner
  attribute_condition = "assertion.repository_owner=='${var.github_repository_owner}'"
}

# ============================================================================
# Service Accounts for GitHub Actions
# ============================================================================

resource "google_service_account" "github_actions" {
  for_each = var.service_accounts

  project      = var.project_id
  account_id   = each.value.account_id
  display_name = each.value.display_name
  description  = each.value.description
}

# ============================================================================
# IAM Bindings: Allow GitHub Actions to impersonate Service Accounts
# ============================================================================

resource "google_service_account_iam_member" "github_actions_wif" {
  for_each = var.service_accounts

  service_account_id = google_service_account.github_actions[each.key].name
  role               = "roles/iam.workloadIdentityUser"

  # Conditional access:
  # - If repository filter is specified, use it
  # - Otherwise, allow any repository from the configured owner
  member = each.value.repository_filter != null ? (
    "principalSet://iam.googleapis.com/${local.workload_identity_provider_name}/attribute.repository/${var.github_repository_owner}/${each.value.repository_filter}"
    ) : (
    "principalSet://iam.googleapis.com/${local.workload_identity_provider_name}/attribute.repository_owner/${var.github_repository_owner}"
  )
}

# ============================================================================
# Project-Level IAM Roles
# ============================================================================

resource "google_project_iam_member" "github_actions_roles" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for role in sa_config.project_roles : {
          key     = "${sa_name}-${role}"
          sa_name = sa_name
          role    = role
        }
      ]
    ]) : binding.key => binding
  }

  project = var.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.github_actions[each.value.sa_name].email}"
}

# ============================================================================
# Artifact Registry Repository IAM
# ============================================================================

resource "google_artifact_registry_repository_iam_member" "github_actions" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for repo_config in lookup(sa_config, "artifact_registry_repositories", []) : {
          key        = "${sa_name}-${repo_config.repository}-${repo_config.location}"
          sa_name    = sa_name
          location   = repo_config.location
          repository = repo_config.repository
          role       = repo_config.role
        }
      ]
    ]) : binding.key => binding
  }

  project    = var.project_id
  location   = each.value.location
  repository = each.value.repository
  role       = each.value.role
  member     = "serviceAccount:${google_service_account.github_actions[each.value.sa_name].email}"
}

# ============================================================================
# GCS Bucket IAM
# ============================================================================

resource "google_storage_bucket_iam_member" "github_actions" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for bucket_config in lookup(sa_config, "storage_buckets", []) : {
          key    = "${sa_name}-${bucket_config.bucket_name}"
          sa_name = sa_name
          bucket = bucket_config.bucket_name
          role   = bucket_config.role
        }
      ]
    ]) : binding.key => binding
  }

  bucket = each.value.bucket
  role   = each.value.role
  member = "serviceAccount:${google_service_account.github_actions[each.value.sa_name].email}"
}

# ============================================================================
# Secret Manager IAM
# ============================================================================

resource "google_secret_manager_secret_iam_member" "github_actions" {
  for_each = {
    for binding in flatten([
      for sa_name, sa_config in var.service_accounts : [
        for secret_id in lookup(sa_config, "secret_ids", []) : {
          key       = "${sa_name}-${secret_id}"
          sa_name   = sa_name
          secret_id = secret_id
        }
      ]
    ]) : binding.key => binding
  }

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.github_actions[each.value.sa_name].email}"
}
