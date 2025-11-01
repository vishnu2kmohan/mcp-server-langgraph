output "service_account_emails" {
  description = "Map of Kubernetes SA names to GCP service account emails"
  value = {
    for sa_name, sa in google_service_account.workload_identity :
    sa_name => sa.email
  }
}

output "service_account_ids" {
  description = "Map of Kubernetes SA names to GCP service account IDs"
  value = {
    for sa_name, sa in google_service_account.workload_identity :
    sa_name => sa.id
  }
}

output "service_account_unique_ids" {
  description = "Map of Kubernetes SA names to GCP service account unique IDs"
  value = {
    for sa_name, sa in google_service_account.workload_identity :
    sa_name => sa.unique_id
  }
}

output "workload_identity_pool" {
  description = "Workload Identity pool name"
  value       = local.workload_identity_pool
}

output "kubernetes_service_account_annotations" {
  description = "Annotations to add to Kubernetes ServiceAccounts"
  value = {
    for sa_name, sa in google_service_account.workload_identity :
    sa_name => {
      "iam.gke.io/gcp-service-account" = sa.email
    }
  }
}

output "kubernetes_service_account_manifests" {
  description = "Example Kubernetes ServiceAccount manifests"
  value = {
    for sa_name, sa in google_service_account.workload_identity :
    sa_name => yamlencode({
      apiVersion = "v1"
      kind       = "ServiceAccount"
      metadata = {
        name      = sa_name
        namespace = var.namespace
        annotations = {
          "iam.gke.io/gcp-service-account" = sa.email
        }
      }
    })
  }
}

output "service_account_keys" {
  description = "Service account keys (if created - not recommended for Workload Identity)"
  value = {
    for sa_name, key in google_service_account_key.keys :
    sa_name => {
      private_key = key.private_key
      public_key  = key.public_key
    }
  }
  sensitive = true
}
