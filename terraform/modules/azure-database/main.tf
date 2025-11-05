# Azure Database for PostgreSQL Flexible Server Module
# Creates a highly available PostgreSQL instance with automated backups, encryption, and monitoring

locals {
  server_name = var.server_name != "" ? var.server_name : "${var.name_prefix}-postgres"

  common_tags = merge(
    var.tags,
    {
      managed_by = "terraform"
      database   = "postgres"
    }
  )
}

#######################
# Azure Database for PostgreSQL Flexible Server
#######################

resource "azurerm_postgresql_flexible_server" "main" {
  name                = local.server_name
  resource_group_name = var.resource_group_name
  location            = var.location

  # Version
  version = var.postgres_version

  # SKU (compute tier)
  sku_name = var.sku_name

  # Storage
  storage_mb        = var.storage_mb
  storage_tier      = var.storage_tier
  auto_grow_enabled = var.auto_grow_enabled

  # High Availability
  dynamic "high_availability" {
    for_each = var.enable_high_availability ? [1] : []
    content {
      mode                      = var.high_availability_mode
      standby_availability_zone = var.standby_availability_zone
    }
  }

  # Backup configuration
  backup_retention_days        = var.backup_retention_days
  geo_redundant_backup_enabled = var.geo_redundant_backup_enabled

  # Authentication
  administrator_login    = var.admin_username
  administrator_password = var.admin_password != "" ? var.admin_password : random_password.admin.result

  # Networking
  delegated_subnet_id = var.delegated_subnet_id
  private_dns_zone_id = var.private_dns_zone_id

  # Public access
  public_network_access_enabled = var.public_network_access_enabled

  # Zone (for non-HA deployments)
  zone = var.enable_high_availability ? null : var.availability_zone

  # Maintenance window
  dynamic "maintenance_window" {
    for_each = var.maintenance_window != null ? [var.maintenance_window] : []
    content {
      day_of_week  = maintenance_window.value.day_of_week
      start_hour   = maintenance_window.value.start_hour
      start_minute = maintenance_window.value.start_minute
    }
  }

  # Azure AD Authentication
  dynamic "authentication" {
    for_each = var.enable_azure_ad_auth ? [1] : []
    content {
      active_directory_auth_enabled = true
      password_auth_enabled         = var.enable_password_auth
      tenant_id                     = var.tenant_id
    }
  }

  # Customer-managed encryption key (optional)
  dynamic "customer_managed_key" {
    for_each = var.cmk_key_vault_key_id != null ? [1] : []
    content {
      key_vault_key_id                  = var.cmk_key_vault_key_id
      primary_user_assigned_identity_id = var.primary_user_assigned_identity_id
    }
  }

  # Identity (for customer-managed keys)
  dynamic "identity" {
    for_each = var.cmk_key_vault_key_id != null ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.primary_user_assigned_identity_id]
    }
  }

  tags = local.common_tags

  lifecycle {
    ignore_changes = [
      administrator_password, # Don't update password through Terraform
      zone,                   # Don't change zone after creation
    ]
  }
}

#######################
# PostgreSQL Configurations (Server Parameters)
#######################

resource "azurerm_postgresql_flexible_server_configuration" "configurations" {
  for_each = merge(
    var.postgresql_configurations,
    {
      # Performance and monitoring defaults
      "log_connections"            = var.enable_query_insights ? "on" : "off"
      "log_disconnections"         = var.enable_query_insights ? "on" : "off"
      "log_duration"               = var.enable_slow_query_log ? "on" : "off"
      "log_min_duration_statement" = tostring(var.slow_query_threshold_ms)
      "log_lock_waits"             = "on"
      "shared_preload_libraries"   = "pg_stat_statements"
      "track_activity_query_size"  = "4096"
      "track_io_timing"            = "on"
    }
  )

  name      = each.key
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = each.value
}

#######################
# Databases
#######################

resource "azurerm_postgresql_flexible_server_database" "default" {
  name      = var.default_database_name
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = var.database_charset
  collation = var.database_collation
}

resource "azurerm_postgresql_flexible_server_database" "additional" {
  for_each = toset(var.additional_databases)

  name      = each.value
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = var.database_charset
  collation = var.database_collation
}

#######################
# Random Password
#######################

resource "random_password" "admin" {
  length  = 32
  special = true
  # Exclude characters that might cause issues
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

#######################
# Firewall Rules (if public access enabled)
#######################

resource "azurerm_postgresql_flexible_server_firewall_rule" "allowed_ips" {
  for_each = var.public_network_access_enabled ? var.allowed_ip_ranges : {}

  name             = each.key
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = each.value.start_ip
  end_ip_address   = each.value.end_ip
}

# Allow Azure services (if enabled)
resource "azurerm_postgresql_flexible_server_firewall_rule" "azure_services" {
  count = var.public_network_access_enabled && var.allow_azure_services ? 1 : 0

  name             = "AllowAllAzureServicesAndResourcesWithinAzureIps"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

#######################
# Azure Monitor Diagnostic Settings
#######################

resource "azurerm_monitor_diagnostic_setting" "postgres" {
  count = var.enable_diagnostic_settings ? 1 : 0

  name                       = "${local.server_name}-diagnostics"
  target_resource_id         = azurerm_postgresql_flexible_server.main.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  # Metrics
  dynamic "metric" {
    for_each = var.diagnostic_metrics
    content {
      category = metric.value
      enabled  = true
    }
  }

  # Logs
  dynamic "enabled_log" {
    for_each = var.diagnostic_logs
    content {
      category = enabled_log.value
    }
  }
}

#######################
# Azure Monitor Alerts
#######################

# Alert for high CPU usage
resource "azurerm_monitor_metric_alert" "cpu_high" {
  count = var.enable_monitoring_alerts ? 1 : 0

  name                = "${local.server_name}-high-cpu"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_postgresql_flexible_server.main.id]
  description         = "Alert when CPU usage exceeds ${var.alert_cpu_threshold}%"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.DBforPostgreSQL/flexibleServers"
    metric_name      = "cpu_percent"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.alert_cpu_threshold
  }

  action {
    action_group_id = var.action_group_id
  }

  tags = local.common_tags
}

# Alert for high memory usage
resource "azurerm_monitor_metric_alert" "memory_high" {
  count = var.enable_monitoring_alerts ? 1 : 0

  name                = "${local.server_name}-high-memory"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_postgresql_flexible_server.main.id]
  description         = "Alert when memory usage exceeds ${var.alert_memory_threshold}%"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.DBforPostgreSQL/flexibleServers"
    metric_name      = "memory_percent"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.alert_memory_threshold
  }

  action {
    action_group_id = var.action_group_id
  }

  tags = local.common_tags
}

# Alert for storage usage
resource "azurerm_monitor_metric_alert" "storage_high" {
  count = var.enable_monitoring_alerts ? 1 : 0

  name                = "${local.server_name}-high-storage"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_postgresql_flexible_server.main.id]
  description         = "Alert when storage usage exceeds ${var.alert_storage_threshold}%"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.DBforPostgreSQL/flexibleServers"
    metric_name      = "storage_percent"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = var.alert_storage_threshold
  }

  action {
    action_group_id = var.action_group_id
  }

  tags = local.common_tags
}

# Alert for connection failures
resource "azurerm_monitor_metric_alert" "connections_failed" {
  count = var.enable_monitoring_alerts ? 1 : 0

  name                = "${local.server_name}-connection-failures"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_postgresql_flexible_server.main.id]
  description         = "Alert when connection failures exceed threshold"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.DBforPostgreSQL/flexibleServers"
    metric_name      = "connections_failed"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = var.alert_connection_failures_threshold
  }

  action {
    action_group_id = var.action_group_id
  }

  tags = local.common_tags
}

#######################
# Read Replicas
#######################

resource "azurerm_postgresql_flexible_server" "read_replicas" {
  count = var.read_replica_count

  name                = "${local.server_name}-replica-${count.index + 1}"
  resource_group_name = var.resource_group_name
  location            = var.read_replica_locations[count.index % length(var.read_replica_locations)]

  # Source server for replication
  create_mode      = "Replica"
  source_server_id = azurerm_postgresql_flexible_server.main.id

  # SKU (can be different from primary)
  sku_name = var.read_replica_sku_name != "" ? var.read_replica_sku_name : var.sku_name

  # Storage
  storage_mb = var.storage_mb

  # Zone
  zone = var.read_replica_zones != null ? var.read_replica_zones[count.index % length(var.read_replica_zones)] : null

  tags = local.common_tags

  depends_on = [azurerm_postgresql_flexible_server.main]
}
