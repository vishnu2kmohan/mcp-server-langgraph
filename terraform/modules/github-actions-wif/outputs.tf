# ============================================================================
# GitHub Actions Workload Identity Federation - Outputs
# ============================================================================

output "workload_identity_provider_name" {
  description = "Full resource name of the Workload Identity Provider (for use in GitHub Actions auth step)"
  value       = google_iam_workload_identity_pool_provider.github_actions.name
}

output "workload_identity_pool_id" {
  description = "Workload Identity Pool ID"
  value       = google_iam_workload_identity_pool.github_actions.workload_identity_pool_id
}

output "workload_identity_provider_id" {
  description = "Workload Identity Provider ID"
  value       = google_iam_workload_identity_pool_provider.github_actions.workload_identity_pool_provider_id
}

output "service_account_emails" {
  description = "Map of service account names to their email addresses (for use in GitHub Actions auth step)"
  value = {
    for sa_name, sa in google_service_account.github_actions :
    sa_name => sa.email
  }
}

output "service_account_ids" {
  description = "Map of service account names to their full resource IDs"
  value = {
    for sa_name, sa in google_service_account.github_actions :
    sa_name => sa.id
  }
}

output "github_secrets" {
  description = "GitHub Secrets configuration values (add these to GitHub repository settings)"
  value = {
    GCP_WIF_PROVIDER = google_iam_workload_identity_pool_provider.github_actions.name
    service_accounts = {
      for sa_name, sa in google_service_account.github_actions :
      sa_name => sa.email
    }
  }
}

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "project_number" {
  description = "GCP Project Number"
  value       = var.project_number
}
