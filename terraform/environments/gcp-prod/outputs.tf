##############################
# VPC Outputs
#######################

output "vpc_name" {
  description = "Name of the VPC"
  value       = module.vpc.network_name
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.network_id
}

output "nodes_subnet_name" {
  description = "Name of the nodes subnet"
  value       = module.vpc.nodes_subnet_name
}

output "nat_ip_addresses" {
  description = "Static NAT IP addresses"
  value       = module.vpc.nat_ip_addresses
}

#######################
# GKE Outputs
#######################

output "cluster_name" {
  description = "Name of the GKE cluster"
  value       = module.gke.cluster_name
}

output "cluster_location" {
  description = "Location of the GKE cluster"
  value       = module.gke.cluster_location
}

output "cluster_endpoint" {
  description = "Endpoint for the GKE cluster"
  value       = module.gke.cluster_endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "CA certificate for the GKE cluster"
  value       = module.gke.cluster_ca_certificate
  sensitive   = true
}

output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = module.gke.kubectl_config_command
}

output "console_link" {
  description = "Link to cluster in Google Cloud Console"
  value       = module.gke.console_link
}

output "workload_identity_pool" {
  description = "Workload Identity pool"
  value       = module.gke.workload_identity_pool
}

#######################
# Cloud SQL Outputs
#######################

output "cloudsql_instance_name" {
  description = "Name of the Cloud SQL instance"
  value       = module.cloudsql.instance_name
}

output "cloudsql_connection_name" {
  description = "Connection name for Cloud SQL Proxy"
  value       = module.cloudsql.instance_connection_name
}

output "cloudsql_private_ip" {
  description = "Private IP address of Cloud SQL"
  value       = module.cloudsql.instance_private_ip
}

output "cloudsql_database_name" {
  description = "Name of the default database"
  value       = module.cloudsql.default_database_name
}

output "cloudsql_user_name" {
  description = "Name of the default database user"
  value       = module.cloudsql.default_user_name
}

output "cloudsql_user_password" {
  description = "Password of the default database user"
  value       = module.cloudsql.default_user_password
  sensitive   = true
}

output "cloudsql_read_replica_connection_names" {
  description = "Connection names for Cloud SQL read replicas"
  value       = module.cloudsql.read_replica_connection_names
}

#######################
# Memorystore Outputs
#######################

output "redis_instance_name" {
  description = "Name of the Redis instance"
  value       = module.memorystore.instance_name
}

output "redis_host" {
  description = "Hostname of the Redis instance"
  value       = module.memorystore.instance_host
}

output "redis_port" {
  description = "Port of the Redis instance"
  value       = module.memorystore.instance_port
}

output "redis_auth_string" {
  description = "AUTH string for Redis"
  value       = module.memorystore.auth_string
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string with AUTH"
  value       = module.memorystore.connection_string_with_auth
  sensitive   = true
}

#######################
# Workload Identity Outputs
#######################

output "service_account_emails" {
  description = "GCP service account emails for Workload Identity"
  value       = module.workload_identity.service_account_emails
}

output "kubernetes_service_account_annotations" {
  description = "Annotations to add to Kubernetes ServiceAccounts"
  value       = module.workload_identity.kubernetes_service_account_annotations
}

#######################
# Summary Output
#######################

output "deployment_summary" {
  description = "Summary of deployed infrastructure"
  value = {
    environment = "production"
    region      = var.region
    cluster = {
      name     = module.gke.cluster_name
      location = module.gke.cluster_location
      type     = "autopilot"
    }
    database = {
      type       = "cloudsql-postgresql"
      instance   = module.cloudsql.instance_name
      private_ip = module.cloudsql.instance_private_ip
      replicas   = var.cloudsql_read_replica_count
    }
    cache = {
      type = "memorystore-redis"
      host = module.memorystore.instance_host
      port = module.memorystore.instance_port
      tier = "STANDARD_HA"
    }
    network = {
      vpc           = module.vpc.network_name
      private_nodes = true
      nat_ips       = module.vpc.nat_ip_addresses
    }
  }
}

output "connection_info" {
  description = "Connection information for services"
  value = {
    gke = {
      command      = module.gke.kubectl_config_command
      console_link = module.gke.console_link
    }
    cloudsql = {
      connection_name = module.cloudsql.instance_connection_name
      private_ip      = module.cloudsql.instance_private_ip
      database        = module.cloudsql.default_database_name
    }
    redis = {
      host = module.memorystore.instance_host
      port = module.memorystore.instance_port
    }
  }
  sensitive = true
}
