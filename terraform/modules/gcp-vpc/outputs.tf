#######################
# VPC Outputs
#######################

output "network_id" {
  description = "ID of the VPC network"
  value       = google_compute_network.main.id
}

output "network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.main.name
}

output "network_self_link" {
  description = "Self link of the VPC network"
  value       = google_compute_network.main.self_link
}

output "routing_mode" {
  description = "Routing mode of the VPC"
  value       = google_compute_network.main.routing_mode
}

#######################
# Subnet Outputs
#######################

output "nodes_subnet_id" {
  description = "ID of the nodes subnet"
  value       = google_compute_subnetwork.nodes.id
}

output "nodes_subnet_name" {
  description = "Name of the nodes subnet"
  value       = google_compute_subnetwork.nodes.name
}

output "nodes_subnet_self_link" {
  description = "Self link of the nodes subnet"
  value       = google_compute_subnetwork.nodes.self_link
}

output "nodes_subnet_cidr" {
  description = "CIDR block of the nodes subnet"
  value       = google_compute_subnetwork.nodes.ip_cidr_range
}

output "pods_cidr" {
  description = "CIDR block for GKE pods (secondary range)"
  value       = google_compute_subnetwork.nodes.secondary_ip_range[0].ip_cidr_range
}

output "pods_range_name" {
  description = "Name of the pods secondary IP range"
  value       = google_compute_subnetwork.nodes.secondary_ip_range[0].range_name
}

output "services_cidr" {
  description = "CIDR block for GKE services (secondary range)"
  value       = google_compute_subnetwork.nodes.secondary_ip_range[1].ip_cidr_range
}

output "services_range_name" {
  description = "Name of the services secondary IP range"
  value       = google_compute_subnetwork.nodes.secondary_ip_range[1].range_name
}

output "public_subnet_id" {
  description = "ID of the public subnet (if created)"
  value       = try(google_compute_subnetwork.public[0].id, null)
}

output "public_subnet_name" {
  description = "Name of the public subnet (if created)"
  value       = try(google_compute_subnetwork.public[0].name, null)
}

output "public_subnet_cidr" {
  description = "CIDR block of the public subnet (if created)"
  value       = try(google_compute_subnetwork.public[0].ip_cidr_range, null)
}

output "management_subnet_id" {
  description = "ID of the management subnet (if created)"
  value       = try(google_compute_subnetwork.management[0].id, null)
}

output "management_subnet_name" {
  description = "Name of the management subnet (if created)"
  value       = try(google_compute_subnetwork.management[0].name, null)
}

output "management_subnet_cidr" {
  description = "CIDR block of the management subnet (if created)"
  value       = try(google_compute_subnetwork.management[0].ip_cidr_range, null)
}

#######################
# Cloud Router & NAT Outputs
#######################

output "cloud_router_id" {
  description = "ID of the Cloud Router"
  value       = google_compute_router.main.id
}

output "cloud_router_name" {
  description = "Name of the Cloud Router"
  value       = google_compute_router.main.name
}

output "cloud_router_self_link" {
  description = "Self link of the Cloud Router"
  value       = google_compute_router.main.self_link
}

output "cloud_nat_id" {
  description = "ID of the Cloud NAT"
  value       = google_compute_router_nat.main.id
}

output "cloud_nat_name" {
  description = "Name of the Cloud NAT"
  value       = google_compute_router_nat.main.name
}

output "nat_ip_addresses" {
  description = "List of NAT IP addresses (if manually allocated)"
  value       = google_compute_address.nat[*].address
}

output "nat_ip_self_links" {
  description = "Self links of NAT IP addresses (if manually allocated)"
  value       = google_compute_address.nat[*].self_link
}

#######################
# Firewall Outputs
#######################

output "firewall_allow_internal_id" {
  description = "ID of the allow-internal firewall rule"
  value       = google_compute_firewall.allow_internal.id
}

output "firewall_allow_internal_name" {
  description = "Name of the allow-internal firewall rule"
  value       = google_compute_firewall.allow_internal.name
}

output "firewall_iap_ssh_id" {
  description = "ID of the IAP SSH firewall rule (if enabled)"
  value       = try(google_compute_firewall.allow_iap_ssh[0].id, null)
}

output "firewall_health_checks_id" {
  description = "ID of the health checks firewall rule"
  value       = google_compute_firewall.allow_health_checks.id
}

output "custom_firewall_rule_ids" {
  description = "IDs of custom firewall rules"
  value       = { for k, v in google_compute_firewall.custom : k => v.id }
}

#######################
# Private Service Connection Outputs
#######################

output "private_service_connection_status" {
  description = "Status of private service connection"
  value       = try(google_service_networking_connection.private_services[0].service, null)
}

output "private_services_ip_range" {
  description = "IP range allocated for private services"
  value       = try(google_compute_global_address.private_services[0].address, null)
}

output "private_services_ip_range_name" {
  description = "Name of the IP range for private services"
  value       = try(google_compute_global_address.private_services[0].name, null)
}

output "private_services_prefix_length" {
  description = "Prefix length of the IP range for private services"
  value       = try(google_compute_global_address.private_services[0].prefix_length, null)
}

#######################
# Cloud Armor Outputs
#######################

output "cloud_armor_policy_id" {
  description = "ID of the Cloud Armor security policy (if enabled)"
  value       = try(google_compute_security_policy.cloud_armor[0].id, null)
}

output "cloud_armor_policy_name" {
  description = "Name of the Cloud Armor security policy (if enabled)"
  value       = try(google_compute_security_policy.cloud_armor[0].name, null)
}

output "cloud_armor_policy_self_link" {
  description = "Self link of the Cloud Armor security policy (if enabled)"
  value       = try(google_compute_security_policy.cloud_armor[0].self_link, null)
}

#######################
# Summary Outputs (for convenience)
#######################

output "gke_network_config" {
  description = "Network configuration for GKE cluster module"
  value = {
    network_name         = google_compute_network.main.name
    subnet_name          = google_compute_subnetwork.nodes.name
    pods_range_name      = google_compute_subnetwork.nodes.secondary_ip_range[0].range_name
    services_range_name  = google_compute_subnetwork.nodes.secondary_ip_range[1].range_name
  }
}

output "network_summary" {
  description = "Summary of network configuration"
  value = {
    vpc_name              = google_compute_network.main.name
    region                = var.region
    nodes_cidr            = google_compute_subnetwork.nodes.ip_cidr_range
    pods_cidr             = google_compute_subnetwork.nodes.secondary_ip_range[0].ip_cidr_range
    services_cidr         = google_compute_subnetwork.nodes.secondary_ip_range[1].ip_cidr_range
    public_subnet_created = var.create_public_subnet
    management_subnet_created = var.create_management_subnet
    private_service_connection_enabled = var.enable_private_service_connection
    cloud_armor_enabled   = var.enable_cloud_armor
    flow_logs_enabled     = var.enable_flow_logs
    nat_type              = var.nat_ip_allocate_option
  }
}
