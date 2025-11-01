#######################
# Cluster Outputs
#######################

output "cluster_id" {
  description = "ID of the GKE cluster"
  value       = google_container_cluster.autopilot.id
}

output "cluster_name" {
  description = "Name of the GKE cluster"
  value       = google_container_cluster.autopilot.name
}

output "cluster_location" {
  description = "Location (region or zone) of the GKE cluster"
  value       = google_container_cluster.autopilot.location
}

output "cluster_self_link" {
  description = "Self link of the GKE cluster"
  value       = google_container_cluster.autopilot.self_link
}

output "cluster_endpoint" {
  description = "Endpoint for accessing the cluster"
  value       = google_container_cluster.autopilot.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "Base64 encoded CA certificate for the cluster"
  value       = google_container_cluster.autopilot.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "cluster_master_version" {
  description = "Current master version of the cluster"
  value       = google_container_cluster.autopilot.master_version
}

#######################
# Workload Identity
#######################

output "workload_identity_pool" {
  description = "Workload Identity pool for the cluster"
  value       = "${var.project_id}.svc.id.goog"
}

output "workload_identity_enabled" {
  description = "Whether Workload Identity is enabled"
  value       = true
}

#######################
# Network Outputs
#######################

output "network" {
  description = "VPC network name"
  value       = var.network_name
}

output "subnetwork" {
  description = "Subnet name"
  value       = var.subnet_name
}

output "pods_range_name" {
  description = "Name of the pods secondary IP range"
  value       = var.pods_range_name
}

output "services_range_name" {
  description = "Name of the services secondary IP range"
  value       = var.services_range_name
}

output "master_ipv4_cidr_block" {
  description = "CIDR block for the master nodes"
  value       = var.master_ipv4_cidr_block
}

#######################
# Fleet & Hub
#######################

output "fleet_membership_id" {
  description = "Fleet membership ID (if fleet registration is enabled)"
  value       = try(google_gke_hub_membership.cluster[0].membership_id, null)
}

output "fleet_membership_name" {
  description = "Fleet membership name (if fleet registration is enabled)"
  value       = try(google_gke_hub_membership.cluster[0].name, null)
}

#######################
# Backup
#######################

output "backup_plan_id" {
  description = "ID of the backup plan (if enabled)"
  value       = try(google_gke_backup_backup_plan.cluster[0].id, null)
}

output "backup_plan_name" {
  description = "Name of the backup plan (if enabled)"
  value       = try(google_gke_backup_backup_plan.cluster[0].name, null)
}

#######################
# Security
#######################

output "binary_authorization_enabled" {
  description = "Whether Binary Authorization is enabled"
  value       = var.enable_binary_authorization
}

output "security_posture_enabled" {
  description = "Whether Security Posture is enabled"
  value       = var.enable_security_posture
}

output "security_posture_mode" {
  description = "Security Posture mode"
  value       = var.enable_security_posture ? var.security_posture_mode : null
}

output "private_cluster_config" {
  description = "Private cluster configuration"
  value = {
    enable_private_nodes    = var.enable_private_nodes
    enable_private_endpoint = var.enable_private_endpoint
    master_ipv4_cidr_block  = var.master_ipv4_cidr_block
  }
}

#######################
# Features
#######################

output "dataplane_v2_enabled" {
  description = "Whether Dataplane V2 is enabled"
  value       = var.enable_dataplane_v2
}

output "network_policy_enabled" {
  description = "Whether network policy is enabled"
  value       = var.enable_network_policy
}

output "vertical_pod_autoscaling_enabled" {
  description = "Whether Vertical Pod Autoscaling is enabled"
  value       = var.enable_vertical_pod_autoscaling
}

output "managed_prometheus_enabled" {
  description = "Whether managed Prometheus is enabled"
  value       = var.enable_managed_prometheus
}

#######################
# Connection Commands
#######################

output "kubectl_config_command" {
  description = "Command to configure kubectl for this cluster"
  value       = var.regional_cluster ? "gcloud container clusters get-credentials ${google_container_cluster.autopilot.name} --region ${var.region} --project ${var.project_id}" : "gcloud container clusters get-credentials ${google_container_cluster.autopilot.name} --zone ${var.zone} --project ${var.project_id}"
}

output "console_link" {
  description = "Link to the cluster in Google Cloud Console"
  value       = "https://console.cloud.google.com/kubernetes/clusters/details/${var.regional_cluster ? var.region : var.zone}/${google_container_cluster.autopilot.name}/details?project=${var.project_id}"
}

#######################
# Summary
#######################

output "cluster_summary" {
  description = "Summary of cluster configuration"
  value = {
    name                    = google_container_cluster.autopilot.name
    location                = google_container_cluster.autopilot.location
    type                    = "autopilot"
    regional                = var.regional_cluster
    private_nodes           = var.enable_private_nodes
    private_endpoint        = var.enable_private_endpoint
    release_channel         = var.release_channel
    workload_identity       = true
    binary_authorization    = var.enable_binary_authorization
    security_posture        = var.enable_security_posture
    dataplane_v2            = var.enable_dataplane_v2
    network_policy          = var.enable_network_policy
    managed_prometheus      = var.enable_managed_prometheus
    fleet_registered        = var.enable_fleet_registration
    backup_enabled          = var.enable_backup_plan
    cost_allocation_enabled = var.enable_cost_allocation
  }
}
