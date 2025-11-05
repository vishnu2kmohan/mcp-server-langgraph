# ============================================================================
# GCP Secret Manager - Application Secrets Module
# ============================================================================
#
# Creates and manages application secrets in GCP Secret Manager with:
# - Automatic rotation support
# - IAM bindings for service account access
# - Replication policy configuration
#
# This module ensures secrets are:
# - Managed via Terraform (Infrastructure as Code)
# - Reproducible across environments
# - Properly secured with IAM policies
#
# ============================================================================

locals {
  # Secret list with metadata
  secrets = {
    # API Keys (replace with real values or use existing secrets)
    "${var.environment}-anthropic-api-key" = {
      description = "Anthropic API key for Claude LLM access"
      replication = var.replication_policy
    }
    "${var.environment}-google-api-key" = {
      description = "Google AI API key for Gemini access"
      replication = var.replication_policy
    }

    # Authentication
    "${var.environment}-jwt-secret" = {
      description = "JWT signing secret for authentication tokens"
      replication = var.replication_policy
    }

    # Database Credentials
    "${var.environment}-postgres-username" = {
      description = "PostgreSQL username for application database"
      replication = var.replication_policy
    }
    "${var.environment}-keycloak-db-password" = {
      description = "Keycloak database password"
      replication = var.replication_policy
    }
    "${var.environment}-openfga-db-password" = {
      description = "OpenFGA database password"
      replication = var.replication_policy
    }
    "${var.environment}-gdpr-db-password" = {
      description = "GDPR database password"
      replication = var.replication_policy
    }

    # Redis/Cache Credentials
    "${var.environment}-redis-host" = {
      description = "Redis host address for session store"
      replication = var.replication_policy
    }
    "${var.environment}-redis-password" = {
      description = "Redis password for authentication"
      replication = var.replication_policy
    }
  }
}

#######################
# Secret Manager Secrets
#######################

resource "google_secret_manager_secret" "secrets" {
  for_each = local.secrets

  project   = var.project_id
  secret_id = each.key

  replication {
    auto {}
  }

  labels = merge(
    var.labels,
    {
      environment = var.environment
      managed_by  = "terraform"
    }
  )
}

#######################
# IAM Bindings for Service Accounts
#######################

# Grant External Secrets Operator access to all secrets
resource "google_secret_manager_secret_iam_member" "external_secrets" {
  for_each = google_secret_manager_secret.secrets

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.external_secrets_service_account}"
}

# Grant application service account access (if specified)
resource "google_secret_manager_secret_iam_member" "app_service_account" {
  for_each = var.app_service_account != "" ? google_secret_manager_secret.secrets : {}

  project   = var.project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.app_service_account}"
}
