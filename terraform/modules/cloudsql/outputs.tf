output "instance_name" {
  description = "Name of the Cloud SQL instance"
  value       = google_sql_database_instance.main.name
}

output "instance_connection_name" {
  description = "Connection name for Cloud SQL Proxy"
  value       = google_sql_database_instance.main.connection_name
}

output "instance_self_link" {
  description = "Self link of the instance"
  value       = google_sql_database_instance.main.self_link
}

output "instance_private_ip" {
  description = "Private IP address of the instance"
  value       = try(google_sql_database_instance.main.private_ip_address, null)
}

output "instance_public_ip" {
  description = "Public IP address of the instance (if enabled)"
  value       = var.enable_public_ip ? try(google_sql_database_instance.main.public_ip_address, null) : null
}

output "instance_service_account_email" {
  description = "Service account email address for the instance"
  value       = google_sql_database_instance.main.service_account_email_address
}

output "default_database_name" {
  description = "Name of the default database"
  value       = google_sql_database.default.name
}

output "default_user_name" {
  description = "Name of the default user"
  value       = var.create_default_user ? google_sql_user.default[0].name : null
}

output "default_user_password" {
  description = "Password of the default user (auto-generated if not provided)"
  value       = var.create_default_user && var.default_user_password == null ? random_password.default_user[0].result : var.default_user_password
  sensitive   = true
}

output "read_replica_connection_names" {
  description = "Connection names for read replicas"
  value       = google_sql_database_instance.read_replicas[*].connection_name
}

output "read_replica_private_ips" {
  description = "Private IP addresses of read replicas"
  value       = google_sql_database_instance.read_replicas[*].private_ip_address
}

output "cloud_sql_proxy_command" {
  description = "Example Cloud SQL Proxy command for connection"
  value       = "cloud-sql-proxy ${google_sql_database_instance.main.connection_name}"
}

output "psql_connection_string" {
  description = "PostgreSQL connection string (using private IP)"
  value       = "postgresql://${var.create_default_user ? google_sql_user.default[0].name : "USER"}@${try(google_sql_database_instance.main.private_ip_address, "IP")}:5432/${google_sql_database.default.name}"
  sensitive   = true
}
