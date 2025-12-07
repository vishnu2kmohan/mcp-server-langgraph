# Cloud SQL PostgreSQL Module
# Creates a highly available PostgreSQL instance with automated backups, encryption, and monitoring

locals {
  instance_name    = var.instance_name != "" ? var.instance_name : "${var.name_prefix}-postgres"
  database_version = var.postgres_major_version != null ? "POSTGRES_${var.postgres_major_version}" : var.database_version

  labels = merge(
    var.labels,
    {
      managed_by = "terraform"
      database   = "postgres"
    }
  )
}

#######################
# Cloud SQL Instance
#######################

resource "google_sql_database_instance" "main" {
  name             = local.instance_name
  project          = var.project_id
  region           = var.region
  database_version = local.database_version

  # Deletion protection
  deletion_protection = var.enable_deletion_protection

  settings {
    tier                  = var.tier
    availability_type     = var.high_availability ? "REGIONAL" : "ZONAL"
    disk_type             = var.disk_type
    disk_size             = var.disk_size_gb
    disk_autoresize       = var.enable_disk_autoresize
    disk_autoresize_limit = var.disk_autoresize_limit_gb

    # IP configuration (private IP)
    ip_configuration {
      ipv4_enabled                                  = var.enable_public_ip
      private_network                               = var.vpc_network_self_link
      enable_private_path_for_google_cloud_services = true
      ssl_mode                                      = var.ssl_mode

      # Authorized networks (if public IP is enabled)
      dynamic "authorized_networks" {
        for_each = var.authorized_networks
        content {
          name  = authorized_networks.value.name
          value = authorized_networks.value.cidr
        }
      }
    }

    # Backup configuration
    backup_configuration {
      enabled                        = var.enable_backups
      start_time                     = var.backup_start_time
      point_in_time_recovery_enabled = var.enable_point_in_time_recovery
      transaction_log_retention_days = var.transaction_log_retention_days
      backup_retention_settings {
        retained_backups = var.backup_retention_count
        retention_unit   = "COUNT"
      }

      # Backup location
      location = var.backup_location
    }

    # Maintenance window
    maintenance_window {
      day          = var.maintenance_window_day
      hour         = var.maintenance_window_hour
      update_track = var.maintenance_window_update_track
    }

    # Database flags (PostgreSQL configuration)
    # Only apply default flags when enable_default_database_flags is true
    # This prevents invalidFlagName errors on instance creation
    dynamic "database_flags" {
      for_each = var.enable_default_database_flags ? merge(
        var.database_flags,
        {
          # Performance and monitoring defaults (only when enabled)
          "log_connections"            = var.enable_query_insights ? "on" : "off"
          "log_disconnections"         = var.enable_query_insights ? "on" : "off"
          "log_duration"               = var.enable_slow_query_log ? "on" : "off"
          "log_min_duration_statement" = var.slow_query_threshold_ms
          "log_lock_waits"             = "on"
          "log_statement"              = var.log_statement_level
          "shared_preload_libraries"   = "pg_stat_statements"
          "track_activity_query_size"  = "4096"
          "track_io_timing"            = "on"
        }
      ) : var.database_flags
      content {
        name  = database_flags.key
        value = database_flags.value
      }
    }

    # Insights configuration (Performance Insights)
    insights_config {
      query_insights_enabled  = var.enable_query_insights
      query_plans_per_minute  = var.query_insights_plans_per_minute
      query_string_length     = var.query_insights_string_length
      record_application_tags = var.query_insights_record_app_tags
      record_client_address   = var.query_insights_record_client_address
    }

    # Active Directory configuration (if enabled)
    dynamic "active_directory_config" {
      for_each = var.active_directory_domain != null ? [1] : []
      content {
        domain = var.active_directory_domain
      }
    }

    # Deny maintenance period (optional)
    dynamic "deny_maintenance_period" {
      for_each = var.deny_maintenance_period != null ? [1] : []
      content {
        start_date = var.deny_maintenance_period.start_date
        end_date   = var.deny_maintenance_period.end_date
        time       = var.deny_maintenance_period.time
      }
    }

    # Password validation policy
    dynamic "password_validation_policy" {
      for_each = var.enable_password_validation ? [1] : []
      content {
        min_length                  = var.password_min_length
        complexity                  = var.password_complexity
        reuse_interval              = var.password_reuse_interval
        disallow_username_substring = var.password_disallow_username
        enable_password_policy      = true
      }
    }

    # Data cache (for read replicas)
    dynamic "data_cache_config" {
      for_each = var.enable_data_cache ? [1] : []
      content {
        data_cache_enabled = true
      }
    }
  }

  # Encryption at rest (automatic with Google-managed keys)
  # For customer-managed encryption keys (CMEK):
  encryption_key_name = var.kms_key_name

  # Timeouts
  timeouts {
    create = var.instance_create_timeout
    update = var.instance_update_timeout
    delete = var.instance_delete_timeout
  }

  # Prevent accidental deletion via terraform destroy
  lifecycle {
    ignore_changes = [
      settings[0].disk_size, # Ignore disk size changes (autoresize handles this)
    ]
  }

  # Dependency on private service connection
  depends_on = [var.private_service_connection_dependency]
}

#######################
# Databases
#######################

resource "google_sql_database" "databases" {
  for_each = toset(var.additional_databases)

  name            = each.value
  project         = var.project_id
  instance        = google_sql_database_instance.main.name
  charset         = var.database_charset
  collation       = var.database_collation
  deletion_policy = var.database_deletion_policy
}

# Default database
resource "google_sql_database" "default" {
  name            = var.default_database_name
  project         = var.project_id
  instance        = google_sql_database_instance.main.name
  charset         = var.database_charset
  collation       = var.database_collation
  deletion_policy = var.database_deletion_policy
}

#######################
# Users
#######################

# Default admin user
resource "google_sql_user" "default" {
  count = var.create_default_user ? 1 : 0

  name     = var.default_user_name
  project  = var.project_id
  instance = google_sql_database_instance.main.name
  password = var.default_user_password != null ? var.default_user_password : random_password.default_user[0].result

  deletion_policy = var.user_deletion_policy
}

# Random password for default user (if not provided)
resource "random_password" "default_user" {
  count = var.create_default_user && var.default_user_password == null ? 1 : 0

  length  = 32
  special = true
}

# Additional users
resource "google_sql_user" "additional" {
  for_each = nonsensitive(var.additional_users)

  name     = each.key
  project  = var.project_id
  instance = google_sql_database_instance.main.name
  password = sensitive(each.value.password != null ? each.value.password : random_password.additional_users[each.key].result)
  type     = lookup(each.value, "type", "BUILT_IN")

  deletion_policy = var.user_deletion_policy
}

# Random passwords for additional users (if not provided)
resource "random_password" "additional_users" {
  for_each = nonsensitive({
    for name, user in var.additional_users : name => user
    if user.password == null
  })

  length  = 32
  special = true
}

#######################
# Read Replicas
#######################

resource "google_sql_database_instance" "read_replicas" {
  count = var.read_replica_count

  name             = "${local.instance_name}-replica-${count.index + 1}"
  project          = var.project_id
  region           = var.read_replica_regions[count.index % length(var.read_replica_regions)]
  database_version = local.database_version

  master_instance_name = google_sql_database_instance.main.name

  replica_configuration {
    failover_target = false
  }

  settings {
    tier              = var.read_replica_tier != null ? var.read_replica_tier : var.tier
    availability_type = "ZONAL" # Read replicas are always zonal
    disk_type         = var.disk_type
    disk_autoresize   = var.enable_disk_autoresize

    # IP configuration (inherit from master)
    ip_configuration {
      ipv4_enabled    = var.enable_public_ip
      private_network = var.vpc_network_self_link
      ssl_mode        = var.ssl_mode
    }

    # Insights configuration
    insights_config {
      query_insights_enabled = var.enable_query_insights
    }

    # Data cache for read replicas
    dynamic "data_cache_config" {
      for_each = var.enable_data_cache ? [1] : []
      content {
        data_cache_enabled = true
      }
    }
  }

  deletion_protection = var.enable_deletion_protection

  depends_on = [google_sql_database_instance.main]
}

#######################
# Cloud SQL Proxy User (for GKE connectivity)
#######################

resource "google_sql_user" "proxy" {
  count = var.create_proxy_user ? 1 : 0

  name     = var.proxy_user_name
  project  = var.project_id
  instance = google_sql_database_instance.main.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"

  # This is a special type of user for Cloud SQL Proxy with Workload Identity
  # Format: SERVICE_ACCOUNT_EMAIL
  deletion_policy = var.user_deletion_policy
}

#######################
# Monitoring Alert Policies
#######################

# Alert for high CPU usage
resource "google_monitoring_alert_policy" "high_cpu" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.instance_name} - High CPU Usage"
  combiner     = "OR"

  conditions {
    display_name = "CPU usage above ${var.alert_cpu_threshold}%"

    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.main.name}\" AND metric.type=\"cloudsql.googleapis.com/database/cpu/utilization\""
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.alert_cpu_threshold / 100

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "86400s" # 24 hours
  }

  enabled = true
}

# Alert for high memory usage
resource "google_monitoring_alert_policy" "high_memory" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.instance_name} - High Memory Usage"
  combiner     = "OR"

  conditions {
    display_name = "Memory usage above ${var.alert_memory_threshold}%"

    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.main.name}\" AND metric.type=\"cloudsql.googleapis.com/database/memory/utilization\""
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.alert_memory_threshold / 100

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "86400s"
  }

  enabled = true
}

# Alert for disk usage
resource "google_monitoring_alert_policy" "high_disk" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.instance_name} - High Disk Usage"
  combiner     = "OR"

  conditions {
    display_name = "Disk usage above ${var.alert_disk_threshold}%"

    condition_threshold {
      filter          = "resource.type=\"cloudsql_database\" AND resource.labels.database_id=\"${var.project_id}:${google_sql_database_instance.main.name}\" AND metric.type=\"cloudsql.googleapis.com/database/disk/utilization\""
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.alert_disk_threshold / 100

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "86400s"
  }

  enabled = true
}
