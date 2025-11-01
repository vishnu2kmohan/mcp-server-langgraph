output "terraform_state_bucket" {
  description = "Name of the GCS bucket for Terraform state"
  value       = google_storage_bucket.terraform_state.name
}

output "terraform_state_bucket_url" {
  description = "URL of the GCS bucket for Terraform state"
  value       = google_storage_bucket.terraform_state.url
}

output "terraform_state_logs_bucket" {
  description = "Name of the GCS bucket for Terraform state access logs"
  value       = google_storage_bucket.terraform_state_logs.name
}

output "terraform_state_logs_bucket_url" {
  description = "URL of the GCS bucket for Terraform state access logs"
  value       = google_storage_bucket.terraform_state_logs.url
}

output "backend_config" {
  description = "Backend configuration for environment modules - use this in terraform backend block"
  value = {
    bucket  = google_storage_bucket.terraform_state.name
    prefix  = "env"  # This will be overridden per environment (e.g., "env/dev", "env/staging", "env/prod")
    project = var.project_id
    region  = var.region
  }
}

output "backend_config_hcl" {
  description = "HCL-formatted backend configuration for easy copy-paste"
  value = <<-EOT
    terraform {
      backend "gcs" {
        bucket  = "${google_storage_bucket.terraform_state.name}"
        prefix  = "env/ENVIRONMENT_NAME"  # Replace ENVIRONMENT_NAME with dev/staging/prod
      }
    }
  EOT
}

output "setup_instructions" {
  description = "Instructions for using this backend in other Terraform configurations"
  value = <<-EOT

    Terraform Backend Setup Complete!

    Next steps:

    1. Add this backend configuration to your environment Terraform files:

       terraform {
         backend "gcs" {
           bucket  = "${google_storage_bucket.terraform_state.name}"
           prefix  = "env/ENVIRONMENT_NAME"
         }
       }

    2. Initialize your Terraform configuration:

       cd terraform/environments/gcp-prod  # or gcp-staging, gcp-dev
       terraform init

    3. The state file will be stored at:
       gs://${google_storage_bucket.terraform_state.name}/env/ENVIRONMENT_NAME/default.tfstate

    4. Access logs are stored at:
       gs://${google_storage_bucket.terraform_state_logs.name}/state-access-logs/

    Important:
    - GCS provides built-in state locking - no additional resources needed
    - State versioning is enabled - you can recover previous versions if needed
    - Buckets are protected from accidental deletion
    - Public access is enforced to be blocked

    Service Account Permissions:
    ${var.terraform_service_account != "" ? "The service account ${var.terraform_service_account} has been granted storage.objectAdmin role." : "No service account configured. Add IAM permissions manually if using a service account."}

  EOT
}

output "project_id" {
  description = "GCP project ID where resources were created"
  value       = var.project_id
}

output "region" {
  description = "GCP region where resources were created"
  value       = var.region
}

output "random_suffix" {
  description = "Random suffix used for bucket uniqueness"
  value       = random_id.bucket_suffix.hex
}
