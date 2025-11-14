# Terraform Backend Setup for GCP
# This creates the GCS bucket for Terraform state management
# Run this once per GCP project before deploying environments
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Project created in GCP
# - Billing enabled on the project
# - Terraform 1.5.0 or later installed
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Data source for project information
data "google_project" "current" {
  project_id = var.project_id
}

# Random suffix for bucket uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# GCS bucket for Terraform state
resource "google_storage_bucket" "terraform_state" {
  name          = "${var.bucket_prefix}-terraform-state-${var.region}-${random_id.bucket_suffix.hex}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  # Uniform bucket-level access (recommended over ACLs)
  uniform_bucket_level_access {
    enabled = true
  }

  # Versioning for state file history
  versioning {
    enabled = true
  }

  # Encryption (GCS encrypts by default with Google-managed keys)
  # For customer-managed encryption keys (CMEK), uncomment below:
  # encryption {
  #   default_kms_key_name = var.kms_key_name
  # }

  # Lifecycle rules to manage old versions
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 10
      with_state         = "ARCHIVED"
    }
  }

  # Enable access logging
  logging {
    log_bucket        = google_storage_bucket.terraform_state_logs.name
    log_object_prefix = "state-access-logs/"
  }

  # Labels for resource management
  labels = {
    managed_by  = "terraform"
    purpose     = "terraform-state-backend"
    project     = "mcp-server-langgraph"
    environment = "infrastructure"
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  # Public access prevention
  public_access_prevention = "enforced"
}

# GCS bucket for access logs
resource "google_storage_bucket" "terraform_state_logs" {
  name          = "${var.bucket_prefix}-terraform-logs-${var.region}-${random_id.bucket_suffix.hex}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  # Uniform bucket-level access
  uniform_bucket_level_access = true

  # Lifecycle policy to delete old logs after 90 days
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90
    }
  }

  # Lifecycle policy to move to NEARLINE after 30 days
  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age = 30
    }
  }

  # Labels for resource management
  labels = {
    managed_by  = "terraform"
    purpose     = "terraform-state-logs"
    project     = "mcp-server-langgraph"
    environment = "infrastructure"
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  # Public access prevention
  public_access_prevention = "enforced"
}

# IAM binding for the service account that will manage Terraform state
# This grants the necessary permissions to read/write state files
resource "google_storage_bucket_iam_member" "terraform_state_admin" {
  count  = var.terraform_service_account != "" ? 1 : 0
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.terraform_service_account}"
}

# IAM binding for state logs bucket
resource "google_storage_bucket_iam_member" "terraform_logs_admin" {
  count  = var.terraform_service_account != "" ? 1 : 0
  bucket = google_storage_bucket.terraform_state_logs.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.terraform_service_account}"
}

# Random ID provider configuration already in main terraform block above
