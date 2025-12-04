# Staging Environment - Cloud DNS Configuration
# This configuration sets up Cloud DNS for the staging GKE environment

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Configure backend for state storage
  # Uncomment and configure for production use
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "staging/cloud-dns"
  # }
}

# Configure the Google Cloud provider
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Data sources to automatically fetch IPs from existing resources
data "google_sql_database_instance" "staging_postgres" {
  project = var.gcp_project_id
  name    = var.cloud_sql_instance_name
}

data "google_redis_instance" "staging_redis" {
  project = var.gcp_project_id
  name    = var.redis_instance_name
  region  = var.gcp_region
}

data "google_redis_instance" "staging_redis_session" {
  project = var.gcp_project_id
  name    = var.redis_session_instance_name
  region  = var.gcp_region
}

# Get VPC network information
data "google_compute_network" "vpc" {
  project = var.gcp_project_id
  name    = var.vpc_network_name
}

# Create Cloud DNS zone and records
module "cloud_dns" {
  source = "../../modules/cloud-dns-staging"

  gcp_project_id                 = var.gcp_project_id
  vpc_network_self_link          = data.google_compute_network.vpc.self_link
  cloud_sql_private_ip           = data.google_sql_database_instance.staging_postgres.private_ip_address
  memorystore_redis_host         = data.google_redis_instance.staging_redis.host
  memorystore_redis_session_host = data.google_redis_instance.staging_redis_session.host
  create_postgres_cname          = var.create_postgres_cname
  dns_ttl                        = var.dns_ttl
}

# Output for verification
output "dns_setup_complete" {
  description = "DNS setup completion status and verification instructions"
  value = {
    zone_name         = module.cloud_dns.dns_zone_name
    cloudsql_dns      = module.cloud_dns.cloudsql_dns_name
    redis_dns         = module.cloud_dns.redis_dns_name
    redis_session_dns = module.cloud_dns.redis_session_dns_name
    verification_cmd  = module.cloud_dns.verification_command
    next_steps        = "Run: kubectl apply -k ../../../deployments/overlays/preview-gke"
  }
}
