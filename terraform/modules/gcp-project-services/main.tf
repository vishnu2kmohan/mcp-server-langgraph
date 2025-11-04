#######################
# GCP Project API Enablement
#
# This module manages the enablement of required GCP APIs for the infrastructure.
# APIs are enabled conditionally based on which features are being used.
#######################

#######################
# Core APIs (Always Enabled)
#######################

resource "google_project_service" "container" {
  count = var.enable_container_api ? 1 : 0

  project = var.project_id
  service = "container.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services
}

resource "google_project_service" "compute" {
  count = var.enable_compute_api ? 1 : 0

  project = var.project_id
  service = "compute.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services
}

#######################
# Networking APIs
#######################

resource "google_project_service" "service_networking" {
  count = var.enable_service_networking_api ? 1 : 0

  project = var.project_id
  service = "servicenetworking.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services

  # Service networking depends on compute
  depends_on = [google_project_service.compute]
}

#######################
# GKE Feature APIs
#######################

resource "google_project_service" "gke_backup" {
  count = var.enable_gke_backup_api ? 1 : 0

  project = var.project_id
  service = "gkebackup.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services

  # GKE backup depends on container API
  depends_on = [google_project_service.container]
}

resource "google_project_service" "container_scanning" {
  count = var.enable_container_scanning_api ? 1 : 0

  project = var.project_id
  service = "containerscanning.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services

  # Container scanning depends on container API
  depends_on = [google_project_service.container]
}

#######################
# Secret Management APIs
#######################

resource "google_project_service" "secret_manager" {
  count = var.enable_secret_manager_api ? 1 : 0

  project = var.project_id
  service = "secretmanager.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services
}

#######################
# Database APIs
#######################

resource "google_project_service" "sql_admin" {
  count = var.enable_sql_admin_api ? 1 : 0

  project = var.project_id
  service = "sqladmin.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services

  # SQL Admin depends on compute and service networking
  depends_on = [
    google_project_service.compute,
    google_project_service.service_networking
  ]
}

resource "google_project_service" "redis" {
  count = var.enable_redis_api ? 1 : 0

  project = var.project_id
  service = "redis.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services

  # Redis depends on compute
  depends_on = [google_project_service.compute]
}

#######################
# Monitoring & Logging APIs
#######################

resource "google_project_service" "monitoring" {
  count = var.enable_monitoring_api ? 1 : 0

  project = var.project_id
  service = "monitoring.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services
}

resource "google_project_service" "logging" {
  count = var.enable_logging_api ? 1 : 0

  project = var.project_id
  service = "logging.googleapis.com"

  disable_on_destroy         = var.disable_on_destroy
  disable_dependent_services = var.disable_dependent_services
}
