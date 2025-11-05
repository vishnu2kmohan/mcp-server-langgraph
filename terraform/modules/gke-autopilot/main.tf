# GKE Autopilot Cluster Module
# Creates a fully managed GKE Autopilot cluster with security best practices

locals {
  cluster_name = var.cluster_name

  # Workload Identity pool (for IRSA-equivalent)
  workload_identity_pool = "${var.project_id}.svc.id.goog"

  labels = merge(
    var.labels,
    {
      managed_by = "terraform"
      cluster    = local.cluster_name
      mode       = "autopilot"
    }
  )
}

#######################
# GKE Autopilot Cluster
#######################

resource "google_container_cluster" "autopilot" {
  name     = local.cluster_name
  project  = var.project_id
  location = var.regional_cluster ? var.region : var.zone

  lifecycle {
    precondition {
      condition     = !var.enable_gke_backup_agent || var.enable_backup_plan
      error_message = <<-EOT
        GKE Backup Agent addon requires a backup plan to be enabled.

        When enabling 'enable_gke_backup_agent', you must also set 'enable_backup_plan = true'.
        The backup agent is only useful when backup plans are configured.
      EOT
    }

    precondition {
      condition     = !(var.enable_config_connector && var.enable_private_endpoint)
      error_message = <<-EOT
        Config Connector cannot be used with a fully private cluster endpoint.

        Config Connector requires access to the Kubernetes API server. Either:
        1. Set 'enable_private_endpoint = false' to allow public access to the API server
        2. Or disable Config Connector with 'enable_config_connector = false'
      EOT
    }

    precondition {
      condition     = !var.enable_master_authorized_networks || length(var.master_authorized_networks_cidrs) > 0
      error_message = <<-EOT
        When master authorized networks are enabled, at least one CIDR block must be specified.

        Set at least one CIDR block in 'master_authorized_networks_cidrs' to prevent cluster lockout.
      EOT
    }

    ignore_changes = [
      # Ignore node pool changes as Autopilot manages them
      node_pool,
      # Ignore initial node count
      initial_node_count,
    ]
  }

  # Autopilot mode - Google manages nodes, scaling, and upgrades
  enable_autopilot = true

  # Network configuration
  network    = var.network_name
  subnetwork = var.subnet_name

  # Use VPC-native networking (required for Autopilot)
  ip_allocation_policy {
    cluster_secondary_range_name  = var.pods_range_name
    services_secondary_range_name = var.services_range_name
  }

  # Private cluster configuration
  private_cluster_config {
    enable_private_nodes    = var.enable_private_nodes
    enable_private_endpoint = var.enable_private_endpoint
    master_ipv4_cidr_block  = var.master_ipv4_cidr_block

    master_global_access_config {
      enabled = var.enable_master_global_access
    }
  }

  # Master authorized networks (control plane access)
  dynamic "master_authorized_networks_config" {
    for_each = var.enable_master_authorized_networks ? [1] : []
    content {
      dynamic "cidr_blocks" {
        for_each = var.master_authorized_networks_cidrs
        content {
          cidr_block   = cidr_blocks.value.cidr_block
          display_name = cidr_blocks.value.display_name
        }
      }
    }
  }

  # Workload Identity (GCP's IRSA equivalent)
  workload_identity_config {
    workload_pool = local.workload_identity_pool
  }

  # Release channel for automatic upgrades
  release_channel {
    channel = var.release_channel
  }

  # Maintenance window
  dynamic "maintenance_policy" {
    for_each = var.maintenance_start_time != null ? [1] : []
    content {
      daily_maintenance_window {
        start_time = var.maintenance_start_time
      }
    }
  }

  # Cluster autoscaling (managed automatically by Autopilot)
  # Autopilot controls all scaling decisions
  # Resource limits are enforced at the project level, not cluster level

  # Binary Authorization (image verification)
  dynamic "binary_authorization" {
    for_each = var.enable_binary_authorization ? [1] : []
    content {
      evaluation_mode = var.binary_authorization_evaluation_mode
    }
  }

  # Vertical Pod Autoscaling (not configurable in Autopilot)
  # Autopilot automatically manages VPA

  # Dataplane V2 (eBPF-based networking)
  datapath_provider = var.enable_dataplane_v2 ? "ADVANCED_DATAPATH" : "DATAPATH_PROVIDER_UNSPECIFIED"

  # Network Policy (not configurable in Autopilot)
  # Autopilot enables network policy by default

  # Security posture (vulnerability scanning)
  dynamic "security_posture_config" {
    for_each = var.enable_security_posture ? [1] : []
    content {
      mode               = var.security_posture_mode
      vulnerability_mode = var.security_posture_vulnerability_mode
    }
  }

  # DNS configuration
  dns_config {
    cluster_dns        = var.cluster_dns_provider
    cluster_dns_scope  = var.cluster_dns_scope
    cluster_dns_domain = var.cluster_dns_domain
  }

  # Monitoring and logging configuration (Cloud Operations)
  monitoring_config {
    enable_components = var.monitoring_enabled_components

    dynamic "managed_prometheus" {
      for_each = var.enable_managed_prometheus ? [1] : []
      content {
        enabled = true
      }
    }

    dynamic "advanced_datapath_observability_config" {
      for_each = var.enable_dataplane_v2 && var.enable_advanced_datapath_observability ? [1] : []
      content {
        enable_metrics = true
        relay_mode     = var.datapath_observability_relay_mode
      }
    }
  }

  logging_config {
    enable_components = var.logging_enabled_components
  }

  # Gateway API (for Ingress)
  dynamic "gateway_api_config" {
    for_each = var.enable_gateway_api ? [1] : []
    content {
      channel = var.gateway_api_channel
    }
  }

  # Addons configuration
  addons_config {
    http_load_balancing {
      disabled = !var.enable_http_load_balancing
    }

    horizontal_pod_autoscaling {
      disabled = !var.enable_horizontal_pod_autoscaling
    }

    # network_policy_config - Not configurable in Autopilot (enabled by default)
    # dns_cache_config - Not configurable in Autopilot (enabled by default)

    gce_persistent_disk_csi_driver_config {
      enabled = var.enable_gce_persistent_disk_csi_driver
    }

    # gcp_filestore_csi_driver_config - Not available in Autopilot

    gcs_fuse_csi_driver_config {
      enabled = var.enable_gcs_fuse_csi_driver
    }

    config_connector_config {
      enabled = var.enable_config_connector
    }

    gke_backup_agent_config {
      enabled = var.enable_gke_backup_agent
    }
  }

  # Notification configuration (for cluster events)
  dynamic "notification_config" {
    for_each = var.notification_config_topic != null ? [1] : []
    content {
      pubsub {
        enabled = true
        topic   = var.notification_config_topic
      }
    }
  }

  # Cost management config
  dynamic "cost_management_config" {
    for_each = var.enable_cost_allocation ? [1] : []
    content {
      enabled = true
    }
  }

  # Resource labels
  resource_labels = local.labels

  # Deletion protection
  deletion_protection = var.enable_deletion_protection

  # Timeouts
  timeouts {
    create = var.cluster_create_timeout
    update = var.cluster_update_timeout
    delete = var.cluster_delete_timeout
  }
}

#######################
# Fleet Registration
# (For Anthos/multi-cluster management)
#######################

resource "google_gke_hub_membership" "cluster" {
  count = var.enable_fleet_registration ? 1 : 0

  project       = var.project_id
  membership_id = "${local.cluster_name}-membership"

  endpoint {
    gke_cluster {
      resource_link = "//container.googleapis.com/${google_container_cluster.autopilot.id}"
    }
  }

  labels = local.labels
}

#######################
# Backup Plan for GKE
#######################

resource "google_gke_backup_backup_plan" "cluster" {
  count = var.enable_backup_plan ? 1 : 0

  project  = var.project_id
  name     = "${local.cluster_name}-backup-plan"
  location = var.region
  cluster  = google_container_cluster.autopilot.id

  lifecycle {
    precondition {
      condition     = !var.enable_backup_plan || var.enable_backup_plan
      error_message = <<-EOT
        GKE Backup requires the gkebackup.googleapis.com API to be enabled.

        Before enabling backup_plan, ensure that:
        1. The gkebackup.googleapis.com API is enabled in your project
        2. A gcp-project-services module is wired in with enable_gke_backup_api = true

        To enable the API manually:
          gcloud services enable gkebackup.googleapis.com --project=${var.project_id}
      EOT
    }
  }

  retention_policy {
    backup_delete_lock_days = var.backup_delete_lock_days
    backup_retain_days      = var.backup_retain_days
  }

  backup_schedule {
    cron_schedule = var.backup_schedule_cron
  }

  backup_config {
    include_volume_data = var.backup_include_volume_data
    include_secrets     = var.backup_include_secrets

    selected_applications {
      namespaced_names {
        namespace = var.backup_namespace
        name      = "*"
      }
    }

    dynamic "encryption_key" {
      for_each = var.backup_encryption_key != null ? [1] : []
      content {
        gcp_kms_encryption_key = var.backup_encryption_key
      }
    }
  }

  labels = local.labels
}

#######################
# Security Scanning
#######################

#######################
# Cloud Logging Sink
# (Export cluster logs to BigQuery for analysis)
#######################

resource "google_logging_project_sink" "gke_cluster" {
  count = var.enable_log_export ? 1 : 0

  name        = "${local.cluster_name}-log-sink"
  project     = var.project_id
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${var.log_export_dataset_id}"

  filter = <<-EOT
    resource.type="k8s_cluster"
    resource.labels.cluster_name="${local.cluster_name}"
    resource.labels.location="${var.regional_cluster ? var.region : var.zone}"
  EOT

  unique_writer_identity = true
}

# Grant BigQuery Data Editor role to the log sink service account
resource "google_bigquery_dataset_iam_member" "log_sink" {
  count = var.enable_log_export ? 1 : 0

  project    = var.project_id
  dataset_id = var.log_export_dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.gke_cluster[0].writer_identity
}

#######################
# Monitoring Alert Policies
#######################

# Alert for cluster upgrade available
resource "google_monitoring_alert_policy" "cluster_upgrade_available" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.cluster_name} - Upgrade Available"
  combiner     = "OR"

  conditions {
    display_name = "GKE cluster upgrade available"

    condition_threshold {
      filter          = "resource.type=\"k8s_cluster\" AND resource.labels.cluster_name=\"${local.cluster_name}\" AND metric.type=\"container.googleapis.com/cluster/control_plane/upgrade_event\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "604800s" # 7 days
  }

  enabled = true
}

# Alert for high CPU usage
resource "google_monitoring_alert_policy" "high_cpu" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.cluster_name} - High CPU Usage"
  combiner     = "OR"

  conditions {
    display_name = "CPU utilization above ${var.cpu_alert_threshold * 100}%"

    condition_threshold {
      filter          = "resource.type=\"k8s_container\" AND resource.labels.cluster_name=\"${local.cluster_name}\" AND metric.type=\"kubernetes.io/container/cpu/limit_utilization\""
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.cpu_alert_threshold

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.cluster_name", "resource.namespace_name"]
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
  display_name = "${local.cluster_name} - High Memory Usage"
  combiner     = "OR"

  conditions {
    display_name = "Memory utilization above ${var.memory_alert_threshold * 100}%"

    condition_threshold {
      filter          = "resource.type=\"k8s_container\" AND resource.labels.cluster_name=\"${local.cluster_name}\" AND metric.type=\"kubernetes.io/container/memory/limit_utilization\""
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.memory_alert_threshold

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.cluster_name", "resource.namespace_name"]
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "86400s" # 24 hours
  }

  enabled = true
}

# Alert for high ephemeral storage usage
resource "google_monitoring_alert_policy" "high_ephemeral_storage" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.cluster_name} - High Ephemeral Storage Usage"
  combiner     = "OR"

  conditions {
    display_name = "Ephemeral storage utilization above ${var.ephemeral_storage_alert_threshold * 100}%"

    condition_threshold {
      filter          = "resource.type=\"k8s_container\" AND resource.labels.cluster_name=\"${local.cluster_name}\" AND metric.type=\"kubernetes.io/container/ephemeral_storage/limit_utilization\""
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.ephemeral_storage_alert_threshold

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MEAN"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.cluster_name", "resource.namespace_name"]
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "86400s" # 24 hours
  }

  enabled = true
}

# Alert for pod crash loops (high restart rate)
resource "google_monitoring_alert_policy" "pod_crash_loop" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.cluster_name} - Pod Crash Loop Detected"
  combiner     = "OR"

  conditions {
    display_name = "Pod restart count above ${var.pod_restart_threshold}"

    condition_threshold {
      filter          = "resource.type=\"k8s_container\" AND resource.labels.cluster_name=\"${local.cluster_name}\" AND metric.type=\"kubernetes.io/container/restart_count\""
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.pod_restart_threshold

      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields      = ["resource.cluster_name", "resource.namespace_name", "resource.pod_name"]
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "86400s" # 24 hours
  }

  enabled = true
}

# Alert for nodes not ready
resource "google_monitoring_alert_policy" "node_not_ready" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.cluster_name} - Node Not Ready"
  combiner     = "OR"

  conditions {
    display_name = "Node is not in ready state"

    condition_threshold {
      filter          = "resource.type=\"k8s_node\" AND resource.labels.cluster_name=\"${local.cluster_name}\" AND metric.type=\"kubernetes.io/node/ready\""
      duration        = "${var.alert_duration_seconds}s"
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
    auto_close = "86400s" # 24 hours
  }

  enabled = true
}

# Alert for pods pending/unschedulable
resource "google_monitoring_alert_policy" "pods_pending" {
  count = var.enable_monitoring_alerts ? 1 : 0

  project      = var.project_id
  display_name = "${local.cluster_name} - Pods Pending/Unschedulable"
  combiner     = "OR"

  conditions {
    display_name = "Pods stuck in pending state"

    condition_threshold {
      filter          = "resource.type=\"k8s_pod\" AND resource.labels.cluster_name=\"${local.cluster_name}\" AND metric.type=\"kubernetes.io/pod/phase\" AND metric.labels.phase=\"Pending\""
      duration        = "${var.alert_duration_seconds}s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MAX"
        cross_series_reducer = "REDUCE_COUNT"
        group_by_fields      = ["resource.cluster_name", "resource.namespace_name"]
      }
    }
  }

  notification_channels = var.monitoring_notification_channels

  alert_strategy {
    auto_close = "86400s" # 24 hours
  }

  enabled = true
}
