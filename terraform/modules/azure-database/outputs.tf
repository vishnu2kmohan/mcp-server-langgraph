# Azure Database for PostgreSQL Flexible Server - Outputs

output "server_id" {
  description = "ID of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.id
}

output "server_name" {
  description = "Name of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.name
}

output "server_fqdn" {
  description = "FQDN of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

output "administrator_login" {
  description = "Administrator username"
  value       = azurerm_postgresql_flexible_server.main.administrator_login
}

output "administrator_password" {
  description = "Administrator password (sensitive)"
  value       = var.admin_password != "" ? var.admin_password : random_password.admin.result
  sensitive   = true
}

output "database_name" {
  description = "Name of the default database"
  value       = azurerm_postgresql_flexible_server_database.default.name
}

output "connection_string" {
  description = "PostgreSQL connection string (without password)"
  value       = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.default.name}?sslmode=require"
  sensitive   = false
}

output "connection_string_full" {
  description = "PostgreSQL connection string (with password)"
  value       = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}:${var.admin_password != "" ? var.admin_password : random_password.admin.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.default.name}?sslmode=require"
  sensitive   = true
}

output "high_availability_enabled" {
  description = "Whether high availability is enabled"
  value       = var.enable_high_availability
}

output "high_availability_mode" {
  description = "High availability mode"
  value       = var.enable_high_availability ? var.high_availability_mode : null
}

output "backup_retention_days" {
  description = "Backup retention period in days"
  value       = azurerm_postgresql_flexible_server.main.backup_retention_days
}

output "geo_redundant_backup_enabled" {
  description = "Whether geo-redundant backup is enabled"
  value       = azurerm_postgresql_flexible_server.main.geo_redundant_backup_enabled
}

output "postgres_version" {
  description = "PostgreSQL version"
  value       = azurerm_postgresql_flexible_server.main.version
}

output "sku_name" {
  description = "SKU name"
  value       = azurerm_postgresql_flexible_server.main.sku_name
}

output "storage_mb" {
  description = "Storage size in MB"
  value       = azurerm_postgresql_flexible_server.main.storage_mb
}

output "read_replica_ids" {
  description = "IDs of read replicas"
  value       = azurerm_postgresql_flexible_server.read_replicas[*].id
}

output "read_replica_fqdns" {
  description = "FQDNs of read replicas"
  value       = azurerm_postgresql_flexible_server.read_replicas[*].fqdn
}

output "additional_databases" {
  description = "Names of additional databases created"
  value       = [for db in azurerm_postgresql_flexible_server_database.additional : db.name]
}

# Kubernetes secret data (for easy integration)
output "k8s_secret_data" {
  description = "Data for Kubernetes secret"
  value = {
    POSTGRES_HOST     = azurerm_postgresql_flexible_server.main.fqdn
    POSTGRES_PORT     = "5432"
    POSTGRES_DB       = azurerm_postgresql_flexible_server_database.default.name
    POSTGRES_USER     = azurerm_postgresql_flexible_server.main.administrator_login
    POSTGRES_PASSWORD = var.admin_password != "" ? var.admin_password : random_password.admin.result
    DATABASE_URL      = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}:${var.admin_password != "" ? var.admin_password : random_password.admin.result}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.default.name}?sslmode=require"
  }
  sensitive = true
}
