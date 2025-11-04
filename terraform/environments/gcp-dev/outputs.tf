output "cluster_name" {
  description = "Name of the GKE cluster"
  value       = module.gke.cluster_name
}

output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = module.gke.kubectl_config_command
}

output "console_link" {
  description = "Link to cluster in Google Cloud Console"
  value       = module.gke.console_link
}

output "cloudsql_connection_name" {
  description = "Connection name for Cloud SQL Proxy"
  value       = module.cloudsql.instance_connection_name
}

output "cloudsql_private_ip" {
  description = "Private IP address of Cloud SQL"
  value       = module.cloudsql.instance_private_ip
}

output "redis_host" {
  description = "Hostname of the Redis instance"
  value       = module.memorystore.instance_host
}

output "redis_port" {
  description = "Port of the Redis instance"
  value       = module.memorystore.instance_port
}

output "deployment_summary" {
  description = "Summary of deployed infrastructure"
  value = {
    environment = "development"
    region      = var.region
    cluster = {
      name     = module.gke.cluster_name
      location = module.gke.cluster_location
      type     = "autopilot-zonal"
    }
    database = {
      type = "cloudsql-postgresql"
      tier = "db-custom-1-3840"
      ha   = false
    }
    cache = {
      type   = "memorystore-redis"
      tier   = "BASIC"
      memory = "1GB"
    }
    estimated_monthly_cost = "$100-150"
  }
}
