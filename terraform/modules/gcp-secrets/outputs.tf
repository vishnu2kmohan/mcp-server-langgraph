# ============================================================================
# GCP Secret Manager Module - Outputs
# ============================================================================

output "secret_ids" {
  description = "Map of secret names to their IDs"
  value = {
    for k, v in google_secret_manager_secret.secrets : k => v.secret_id
  }
}

output "secret_names" {
  description = "List of all secret names created"
  value       = keys(google_secret_manager_secret.secrets)
}

output "iam_bindings_count" {
  description = "Number of IAM bindings created for External Secrets access"
  value       = length(google_secret_manager_secret_iam_member.external_secrets)
}
