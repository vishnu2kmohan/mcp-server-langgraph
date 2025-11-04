# Minimal GCP Staging Environment - WIF Only
# This is a temporary configuration to deploy only the GitHub Actions WIF module
# without the other infrastructure components that have pre-existing errors

terraform {
  required_version = ">= 1.3"

  backend "local" {
    path = "terraform.tfstate"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

#######################
# GitHub Actions WIF
#######################

module "github_actions_wif" {
  source = "../../modules/github-actions-wif"

  project_id              = var.project_id
  project_number          = var.project_number
  github_repository_owner = "vishnu2kmohan"

  service_accounts = {
    staging = {
      account_id        = "github-actions-staging"
      display_name      = "GitHub Actions - Staging Deployment"
      description       = "Service account for GitHub Actions staging deployments to GKE"
      repository_filter = "mcp-server-langgraph"

      project_roles = [
        "roles/container.developer",
        "roles/artifactregistry.writer",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
      ]

      artifact_registry_repositories = [
        {
          location   = var.region
          repository = "mcp-staging"
          role       = "roles/artifactregistry.writer"
        }
      ]
    }

    terraform = {
      account_id   = "github-actions-terraform"
      display_name = "GitHub Actions - Terraform"
      description  = "Service account for GitHub Actions Terraform operations"

      project_roles = [
        "roles/compute.networkAdmin",
        "roles/container.admin",
        "roles/iam.serviceAccountAdmin",
        "roles/resourcemanager.projectIamAdmin",
        "roles/storage.admin",
      ]
    }

    production = {
      account_id        = "github-actions-production"
      display_name      = "GitHub Actions - Production Deployment"
      description       = "Service account for GitHub Actions production deployments to GKE"
      repository_filter = "mcp-server-langgraph"

      project_roles = [
        "roles/container.developer",
        "roles/artifactregistry.writer",
        "roles/logging.logWriter",
        "roles/monitoring.metricWriter",
        "roles/cloudtrace.agent",
      ]
    }
  }
}
