output "cluster_name" {
  description = "Name of the GKE cluster"
  value       = module.gke.cluster_name
}

output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = module.gke.kubectl_config_command
}

output "console_link" {
  description = "Link to cluster in Google Cloud Console"
  value       = module.gke.console_link
}

output "cloudsql_connection_name" {
  description = "Connection name for Cloud SQL Proxy"
  value       = module.cloudsql.instance_connection_name
}

output "cloudsql_private_ip" {
  description = "Private IP address of Cloud SQL"
  value       = module.cloudsql.instance_private_ip
}

output "redis_host" {
  description = "Hostname of the Redis instance"
  value       = module.memorystore.instance_host
}

output "redis_port" {
  description = "Port of the Redis instance"
  value       = module.memorystore.instance_port
}

output "service_account_emails" {
  description = "GCP service account emails"
  value       = module.workload_identity.service_account_emails
}

output "deployment_summary" {
  description = "Summary of deployed infrastructure"
  value = {
    environment = "staging"
    region      = var.region
    cluster = {
      name     = module.gke.cluster_name
      location = module.gke.cluster_location
      type     = "autopilot-regional"
    }
    database = {
      type = "cloudsql-postgresql"
      tier = "db-custom-2-7680"
      ha   = true
    }
    cache = {
      type   = "memorystore-redis"
      tier   = "STANDARD_HA"
      memory = "3GB"
    }
    estimated_monthly_cost = "$250-350"
  }
}

#######################
# GitHub Actions WIF Outputs
#######################

output "github_secrets" {
  description = "GitHub Secrets to add to repository settings"
  value = {
    GCP_WIF_PROVIDER        = module.github_actions_wif.workload_identity_provider_name
    GCP_STAGING_SA_EMAIL    = module.github_actions_wif.service_account_emails["staging"]
    GCP_TERRAFORM_SA_EMAIL  = module.github_actions_wif.service_account_emails["terraform"]
    GCP_PRODUCTION_SA_EMAIL = module.github_actions_wif.service_account_emails["production"]
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
