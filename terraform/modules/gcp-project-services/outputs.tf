#######################
# API Enablement Outputs
#
# These outputs allow other modules to create dependencies on API enablement,
# ensuring APIs are enabled before resources that depend on them are created.
#######################

output "enabled_services" {
  description = "Map of all enabled services with their IDs (use for depends_on in other modules)"
  value = merge(
    var.enable_container_api ? { container = google_project_service.container[0].id } : {},
    var.enable_compute_api ? { compute = google_project_service.compute[0].id } : {},
    var.enable_service_networking_api ? { service_networking = google_project_service.service_networking[0].id } : {},
    var.enable_gke_backup_api ? { gke_backup = google_project_service.gke_backup[0].id } : {},
    var.enable_container_scanning_api ? { container_scanning = google_project_service.container_scanning[0].id } : {},
    var.enable_secret_manager_api ? { secret_manager = google_project_service.secret_manager[0].id } : {},
    var.enable_sql_admin_api ? { sql_admin = google_project_service.sql_admin[0].id } : {},
    var.enable_redis_api ? { redis = google_project_service.redis[0].id } : {},
    var.enable_monitoring_api ? { monitoring = google_project_service.monitoring[0].id } : {},
    var.enable_logging_api ? { logging = google_project_service.logging[0].id } : {}
  )
}

output "project_id" {
  description = "The project ID where APIs were enabled"
  value       = var.project_id
}

# Individual service outputs for granular dependencies

output "container_api_enabled" {
  description = "Whether the Kubernetes Engine API is enabled"
  value       = var.enable_container_api
}

output "compute_api_enabled" {
  description = "Whether the Compute Engine API is enabled"
  value       = var.enable_compute_api
}

output "service_networking_api_enabled" {
  description = "Whether the Service Networking API is enabled"
  value       = var.enable_service_networking_api
}

output "gke_backup_api_enabled" {
  description = "Whether the GKE Backup API is enabled"
  value       = var.enable_gke_backup_api
}

output "secret_manager_api_enabled" {
  description = "Whether the Secret Manager API is enabled"
  value       = var.enable_secret_manager_api
}
