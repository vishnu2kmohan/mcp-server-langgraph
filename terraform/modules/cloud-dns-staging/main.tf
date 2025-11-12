# Cloud DNS Module for Staging Environment
# Creates private DNS zone and records for Cloud SQL and Memorystore Redis

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

# Private DNS Zone for staging internal services
resource "google_dns_managed_zone" "staging_internal" {
  project     = var.gcp_project_id
  name        = "staging-internal"
  dns_name    = "staging.internal."
  description = "Private DNS zone for staging environment - Cloud SQL and Memorystore"
  visibility  = "private"

  private_visibility_config {
    networks {
      network_url = var.vpc_network_self_link
    }
  }

  labels = {
    environment = "staging"
    managed_by  = "terraform"
    purpose     = "internal-services"
  }
}

# Cloud SQL PostgreSQL DNS record
resource "google_dns_record_set" "cloudsql_staging" {
  project      = var.gcp_project_id
  managed_zone = google_dns_managed_zone.staging_internal.name
  name         = "cloudsql-staging.internal."
  type         = "A"
  ttl          = 300

  rrdatas = [var.cloud_sql_private_ip]
}

# Memorystore Redis (primary) DNS record
resource "google_dns_record_set" "redis_staging" {
  project      = var.gcp_project_id
  managed_zone = google_dns_managed_zone.staging_internal.name
  name         = "redis-staging.internal."
  type         = "A"
  ttl          = 300

  rrdatas = [var.memorystore_redis_host]
}

# Memorystore Redis (session store) DNS record
resource "google_dns_record_set" "redis_session_staging" {
  project      = var.gcp_project_id
  managed_zone = google_dns_managed_zone.staging_internal.name
  name         = "redis-session-staging.internal."
  type         = "A"
  ttl          = 300

  rrdatas = [var.memorystore_redis_session_host]
}

# Optional: CNAME record for postgres alias
resource "google_dns_record_set" "postgres_staging_cname" {
  count        = var.create_postgres_cname ? 1 : 0
  project      = var.gcp_project_id
  managed_zone = google_dns_managed_zone.staging_internal.name
  name         = "postgres-staging.internal."
  type         = "CNAME"
  ttl          = 300

  rrdatas = ["cloudsql-staging.internal."]
}
