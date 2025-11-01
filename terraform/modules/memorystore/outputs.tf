output "instance_id" {
  description = "ID of the Redis instance"
  value       = google_redis_instance.main.id
}

output "instance_name" {
  description = "Name of the Redis instance"
  value       = google_redis_instance.main.name
}

output "instance_host" {
  description = "Hostname/IP of the Redis instance"
  value       = google_redis_instance.main.host
}

output "instance_port" {
  description = "Port of the Redis instance"
  value       = google_redis_instance.main.port
}

output "instance_current_location_id" {
  description = "Current zone where the instance is located"
  value       = google_redis_instance.main.current_location_id
}

output "instance_persistence_iam_identity" {
  description = "IAM identity for persistence"
  value       = google_redis_instance.main.persistence_iam_identity
}

output "auth_string" {
  description = "AUTH string for Redis (if auth is enabled)"
  value       = var.enable_auth ? google_redis_instance.main.auth_string : null
  sensitive   = true
}

output "server_ca_certs" {
  description = "Server CA certificates for TLS connections"
  value       = var.enable_transit_encryption ? google_redis_instance.main.server_ca_certs : []
  sensitive   = true
}

output "connection_string" {
  description = "Redis connection string"
  value       = "redis://${google_redis_instance.main.host}:${google_redis_instance.main.port}"
  sensitive   = true
}

output "connection_string_with_auth" {
  description = "Redis connection string with AUTH (if enabled)"
  value       = var.enable_auth ? "redis://:${google_redis_instance.main.auth_string}@${google_redis_instance.main.host}:${google_redis_instance.main.port}" : "redis://${google_redis_instance.main.host}:${google_redis_instance.main.port}"
  sensitive   = true
}

output "read_replica_hosts" {
  description = "Hostnames of read replicas"
  value       = google_redis_instance.read_replicas[*].host
}

output "read_replica_ports" {
  description = "Ports of read replicas"
  value       = google_redis_instance.read_replicas[*].port
}

output "read_replica_ids" {
  description = "IDs of read replicas"
  value       = google_redis_instance.read_replicas[*].id
}

output "instance_summary" {
  description = "Summary of instance configuration"
  value = {
    name                    = google_redis_instance.main.name
    region                  = var.region
    tier                    = var.tier
    memory_size_gb          = var.memory_size_gb
    redis_version           = var.redis_version
    replica_count           = var.replica_count
    transit_encryption      = var.enable_transit_encryption
    auth_enabled            = var.enable_auth
    persistence_enabled     = var.enable_persistence
    persistence_mode        = var.enable_persistence ? var.persistence_mode : null
    cross_region_replicas   = var.create_cross_region_replica ? length(var.read_replica_regions) : 0
  }
}
