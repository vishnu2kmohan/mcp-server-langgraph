# Minimal GCP Staging Environment - WIF Only
# This is a temporary configuration to deploy only the GitHub Actions WIF module
# without the other infrastructure components that have pre-existing errors

terraform {
  required_version = ">= 1.3"

  # Backend configuration is provided via -backend-config flag
  # See backend-config.tfbackend.example for template
  # Example: terraform init -backend-config=backend-config.tfbackend
  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
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

    # Compliance scanner - read-only access for security/compliance scanning workflows
    # Used by: .github/workflows/gcp-compliance-scan.yaml
    # Permissions: Minimal read-only roles for CIS benchmarks, security review
    compliance_scanner = {
      account_id        = "compliance-scanner"
      display_name      = "GitHub Actions - Compliance Scanner"
      description       = "Service account for GCP compliance scanning workflows (CIS benchmarks, kube-bench)"
      repository_filter = "mcp-server-langgraph"

      project_roles = [
        # GKE read-only access for cluster inspection and CIS benchmarks
        "roles/container.clusterViewer",
        # IAM read-only for security audits
        "roles/iam.securityReviewer",
        # Storage read-only for audit log access (if needed)
        "roles/storage.objectViewer",
        # Logging read for security log review
        "roles/logging.viewer",
      ]
    }
  }
}
