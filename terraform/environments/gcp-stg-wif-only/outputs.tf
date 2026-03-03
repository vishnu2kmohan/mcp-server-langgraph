output "github_secrets" {
  description = "GitHub Secrets to add to repository settings"
  value = {
    GCP_WIF_PROVIDER        = module.github_actions_wif.workload_identity_provider_name
    GCP_STG_SA_EMAIL        = module.github_actions_wif.service_account_emails["stg"]
    GCP_TERRAFORM_SA_EMAIL  = module.github_actions_wif.service_account_emails["terraform"]
    GCP_PROD_SA_EMAIL       = module.github_actions_wif.service_account_emails["prod"]
    GCP_COMPLIANCE_SA_EMAIL = module.github_actions_wif.service_account_emails["compliance_scanner"]
  }
  sensitive = false
}

output "wif_provider_name" {
  description = "Workload Identity Provider name for GitHub Actions"
  value       = module.github_actions_wif.workload_identity_provider_name
}

output "github_actions_service_accounts" {
  description = "GitHub Actions service account emails"
  value       = module.github_actions_wif.service_account_emails
}
