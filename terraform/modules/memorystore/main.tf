# Memorystore Redis Module
# Creates a highly available Redis instance with optional read replicas

locals {
  instance_name = var.instance_name != "" ? var.instance_name : "${var.name_prefix}-redis"

  labels = merge(
    var.labels,
    {
      managed_by = "terraform"
      database   = "redis"
    }
  )
}

#######################
# Memorystore Redis Instance
#######################

resource "google_redis_instance" "main" {
  name           = local.instance_name
  project        = var.project_id
  region         = var.region
  tier           = var.tier
  memory_size_gb = var.memory_size_gb

  # Redis version
  redis_version = var.redis_version

  # Network configuration
  authorized_network      = var.vpc_network_id
  connect_mode            = var.connect_mode
  reserved_ip_range       = var.reserved_ip_range
  customer_managed_key    = var.customer_managed_key

  # High availability configuration
  replica_count       = var.tier == "STANDARD_HA" ? var.replica_count : 0
  read_replicas_mode  = var.tier == "STANDARD_HA" && var.replica_count > 0 ? var.read_replicas_mode : null

  # Maintenance policy
  dynamic "maintenance_policy" {
    for_each = var.maintenance_window_day != null ? [1] : []
    content {
      dynamic "weekly_maintenance_window" {
        for_each = var.maintenance_window_day != null ? [1] : []
        content {
          day = var.maintenance_window_day
          start_time {
            hours   = var.maintenance_window_hour
            minutes = var.maintenance_window_minute
          }
        }
      }
    }
  }

  # Persistence configuration (RDB or AOF)
  dynamic "persistence_config" {
    for_each = var.enable_persistence ? [1] : []
    content {
      persistence_mode    = var.persistence_mode
      rdb_snapshot_period = var.persistence_mode == "RDB" ? var.rdb_snapshot_period : null
      rdb_snapshot_start_time = var.persistence_mode == "RDB" && var.rdb_snapshot_start_time != null ? var.rdb_snapshot_start_time : null
    }
  }

  # Redis configuration parameters
  redis_configs = merge(
    var.redis_configs,
    {
      # Security
      "notify-keyspace-events" = var.enable_notifications ? var.notification_events : ""

      # Performance
      "maxmemory-policy" = var.maxmemory_policy
      "timeout"          = tostring(var.timeout_seconds)
    }
  )

  # Transit encryption (TLS)
  transit_encryption_mode = var.enable_transit_encryption ? "SERVER_AUTHENTICATION" : "DISABLED"
  auth_enabled            = var.enable_auth

  # Display name
  display_name = var.display_name != "" ? var.display_name : local.instance_name

  # Labels
  labels = local.labels

  # Maintenance version
  maintenance_version = var.maintenance_version

  # Lifecycle
  lifecycle {
    prevent_destroy = var.enable_deletion_protection
    ignore_changes = [
      maintenance_version,  # Allow automatic minor version upgrades
    ]
  }

  # Timeouts
  timeouts {
    create = var.instance_create_timeout
    update = var.instance_update_timeout
    delete = var.instance_delete_timeout
  }
}

#######################
# Read Replicas (Additional regions)
#######################

resource "google_redis_instance" "read_replicas" {
  count = var.create_cross_region_replica ? length(var.read_replica_regions) : 0

  name           = "${local.instance_name}-replica-${var.read_replica_regions[count.index]}"
  project        = var.project_id
  region         = var.read_replica_regions[count.index]
  tier           = "STANDARD_HA"
  memory_size_gb = var.read_replica_memory_size_gb != null ? var.read_replica_memory_size_gb : var.memory_size_gb

  redis_version = var.redis_version

  # Network - must be in same network
  authorized_network = var.vpc_network_id
  connect_mode       = var.connect_mode

  # Link to primary instance
  replica_count      = 0
  read_replicas_mode = "READ_REPLICAS_DISABLED"

  # Security
  transit_encryption_mode = var.enable_transit_encryption ? "SERVER_AUTHENTICATION" : "DISABLED"
  auth_enabled            = var.enable_auth

  # Redis configs (inherit from primary)
  redis_configs = google_redis_instance.main.redis_configs

  display_name = "${var.display_name != "" ? var.display_name : local.instance_name} Read Replica (${var.read_replica_regions[count.index]})"

  labels = merge(
    local.labels,
    {
      replica_of = google_redis_instance.main.name
      region     = var.read_replica_regions[count.index]
    }
  )

  lifecycle {
    prevent_destroy = var.enable_deletion_protection
  }

  depends_on = [google_redis_instance.main]
}

#######################
# Monitoring Alert Policies
#######################

# Alert for high memory usage
resource "google_monitoring_alert_policy" "high_memory" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.instance_name} - High Memory Usage"
  combiner     = "OR"

  conditions {
    display_name = "Memory usage above ${var.alert_memory_threshold}%"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type=\"redis_instance\"",
        "resource.labels.instance_id=\"${google_redis_instance.main.id}\"",
        "metric.type=\"redis.googleapis.com/stats/memory/usage_ratio\""
      ])
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
    auto_close = "86400s"  # 24 hours
  }

  enabled = true
}

# Alert for high CPU usage
resource "google_monitoring_alert_policy" "high_cpu" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.instance_name} - High CPU Usage"
  combiner     = "OR"

  conditions {
    display_name = "CPU usage above ${var.alert_cpu_threshold}%"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type=\"redis_instance\"",
        "resource.labels.instance_id=\"${google_redis_instance.main.id}\"",
        "metric.type=\"redis.googleapis.com/stats/cpu_utilization\""
      ])
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
    auto_close = "86400s"
  }

  enabled = true
}

# Alert for high connection count
resource "google_monitoring_alert_policy" "high_connections" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.instance_name} - High Connection Count"
  combiner     = "OR"

  conditions {
    display_name = "Connections above ${var.alert_connections_threshold}"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type=\"redis_instance\"",
        "resource.labels.instance_id=\"${google_redis_instance.main.id}\"",
        "metric.type=\"redis.googleapis.com/clients/connected\""
      ])
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.alert_connections_threshold

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

# Alert for instance unavailable
resource "google_monitoring_alert_policy" "instance_down" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.instance_name} - Instance Unavailable"
  combiner     = "OR"

  conditions {
    display_name = "Redis instance is down or unavailable"

    condition_threshold {
      filter = join(" AND ", [
        "resource.type=\"redis_instance\"",
        "resource.labels.instance_id=\"${google_redis_instance.main.id}\"",
        "metric.type=\"redis.googleapis.com/stats/uptime\""
      ])
      duration        = "300s"  # 5 minutes
      comparison      = "COMPARISON_LT"
      threshold_value = 1

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "3600s"  # 1 hour
  }

  enabled = true
}
