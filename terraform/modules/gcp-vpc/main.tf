# VPC Module for GKE
# Creates a VPC with regional subnets optimized for GKE Autopilot/Standard

# VPC (Global in GCP)
resource "google_compute_network" "main" {
  name                            = "${var.name_prefix}-vpc"
  project                         = var.project_id
  auto_create_subnetworks         = false  # We'll create custom subnets
  routing_mode                    = var.routing_mode
  delete_default_routes_on_create = false
  mtu                             = 1460  # Recommended for GCP

  description = "VPC for ${var.name_prefix} - GKE ${var.cluster_name}"
}

#######################
# Subnets (Regional)
#######################

# Primary subnet for GKE nodes
resource "google_compute_subnetwork" "nodes" {
  name    = "${var.name_prefix}-nodes-${var.region}"
  project = var.project_id
  region  = var.region
  network = google_compute_network.main.id

  ip_cidr_range = var.nodes_cidr

  # Secondary IP ranges for GKE pods and services
  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }

  # Enable private Google Access (access Google APIs without public IPs)
  private_ip_google_access = true

  # Enable VPC Flow Logs
  dynamic "log_config" {
    for_each = var.enable_flow_logs ? [1] : []
    content {
      aggregation_interval = var.flow_logs_aggregation_interval
      flow_sampling        = var.flow_logs_sampling
      metadata             = var.flow_logs_metadata
      filter_expr          = var.flow_logs_filter
    }
  }

  description = "GKE nodes subnet for ${var.cluster_name}"
}

# Optional: Public subnet for load balancers, bastion hosts, etc.
resource "google_compute_subnetwork" "public" {
  count = var.create_public_subnet ? 1 : 0

  name    = "${var.name_prefix}-public-${var.region}"
  project = var.project_id
  region  = var.region
  network = google_compute_network.main.id

  ip_cidr_range = var.public_cidr

  private_ip_google_access = true

  dynamic "log_config" {
    for_each = var.enable_flow_logs ? [1] : []
    content {
      aggregation_interval = var.flow_logs_aggregation_interval
      flow_sampling        = var.flow_logs_sampling
      metadata             = var.flow_logs_metadata
    }
  }

  description = "Public subnet for load balancers and bastion hosts"
}

# Optional: Management subnet for operational tooling
resource "google_compute_subnetwork" "management" {
  count = var.create_management_subnet ? 1 : 0

  name    = "${var.name_prefix}-management-${var.region}"
  project = var.project_id
  region  = var.region
  network = google_compute_network.main.id

  ip_cidr_range = var.management_cidr

  private_ip_google_access = true

  dynamic "log_config" {
    for_each = var.enable_flow_logs ? [1] : []
    content {
      aggregation_interval = var.flow_logs_aggregation_interval
      flow_sampling        = var.flow_logs_sampling
      metadata             = var.flow_logs_metadata
    }
  }

  description = "Management subnet for operational tooling"
}

#######################
# Cloud Router
#######################

# Cloud Router for Cloud NAT
resource "google_compute_router" "main" {
  name    = "${var.name_prefix}-router-${var.region}"
  project = var.project_id
  region  = var.region
  network = google_compute_network.main.id

  description = "Cloud Router for NAT and dynamic routing"

  bgp {
    asn               = var.cloud_router_asn
    advertise_mode    = "CUSTOM"
    advertised_groups = ["ALL_SUBNETS"]

    # Advertise custom IP ranges if needed
    dynamic "advertised_ip_ranges" {
      for_each = var.advertised_ip_ranges
      content {
        range       = advertised_ip_ranges.value.range
        description = advertised_ip_ranges.value.description
      }
    }
  }
}

#######################
# Cloud NAT
#######################

# Cloud NAT for outbound internet access from private instances
resource "google_compute_router_nat" "main" {
  name    = "${var.name_prefix}-nat-${var.region}"
  project = var.project_id
  region  = var.region
  router  = google_compute_router.main.name

  nat_ip_allocate_option = var.nat_ip_allocate_option

  # Static NAT IPs (if specified)
  nat_ips = var.nat_ip_allocate_option == "MANUAL_ONLY" ? google_compute_address.nat[*].self_link : []

  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  # Enable endpoint-independent mapping for better NAT behavior
  enable_endpoint_independent_mapping = true

  # Enable dynamic port allocation for high connection scenarios
  enable_dynamic_port_allocation = var.enable_dynamic_port_allocation
  min_ports_per_vm               = var.nat_min_ports_per_vm
  max_ports_per_vm               = var.nat_max_ports_per_vm

  # Logging configuration
  log_config {
    enable = var.enable_nat_logging
    filter = var.nat_logging_filter
  }

  # TCP configurations
  tcp_established_idle_timeout_sec = var.nat_tcp_established_idle_timeout
  tcp_time_wait_timeout_sec        = var.nat_tcp_time_wait_timeout
  tcp_transitory_idle_timeout_sec  = var.nat_tcp_transitory_idle_timeout

  # UDP configuration
  udp_idle_timeout_sec = var.nat_udp_idle_timeout
}

# Static NAT IP addresses (if using manual allocation)
resource "google_compute_address" "nat" {
  count = var.nat_ip_allocate_option == "MANUAL_ONLY" ? var.nat_ip_count : 0

  name         = "${var.name_prefix}-nat-ip-${count.index + 1}"
  project      = var.project_id
  region       = var.region
  address_type = "EXTERNAL"

  description = "Static NAT IP ${count.index + 1} for ${var.name_prefix}"
}

#######################
# Firewall Rules
#######################

# Allow internal communication within the VPC
resource "google_compute_firewall" "allow_internal" {
  name    = "${var.name_prefix}-allow-internal"
  project = var.project_id
  network = google_compute_network.main.id

  description = "Allow internal communication within VPC"

  priority  = 65534
  direction = "INGRESS"

  allow {
    protocol = "tcp"
  }

  allow {
    protocol = "udp"
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [
    var.nodes_cidr,
    var.pods_cidr,
    var.services_cidr,
  ]
}

# Allow SSH from IAP (Identity-Aware Proxy) for bastion access
resource "google_compute_firewall" "allow_iap_ssh" {
  count = var.enable_iap_ssh ? 1 : 0

  name    = "${var.name_prefix}-allow-iap-ssh"
  project = var.project_id
  network = google_compute_network.main.id

  description = "Allow SSH from IAP (35.235.240.0/20)"

  priority  = 1000
  direction = "INGRESS"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["35.235.240.0/20"]  # IAP IP range
  target_tags   = ["iap-ssh"]
}

# Allow health checks from Google Cloud health check ranges
resource "google_compute_firewall" "allow_health_checks" {
  name    = "${var.name_prefix}-allow-health-checks"
  project = var.project_id
  network = google_compute_network.main.id

  description = "Allow health checks from Google Cloud"

  priority  = 1000
  direction = "INGRESS"

  allow {
    protocol = "tcp"
  }

  source_ranges = [
    "35.191.0.0/16",  # Google Cloud health check ranges
    "130.211.0.0/22",
  ]

  target_tags = ["allow-health-checks"]
}

# Deny all ingress by default (best practice)
resource "google_compute_firewall" "deny_all_ingress" {
  count = var.enable_deny_all_ingress ? 1 : 0

  name    = "${var.name_prefix}-deny-all-ingress"
  project = var.project_id
  network = google_compute_network.main.id

  description = "Deny all ingress traffic by default"

  priority  = 65534
  direction = "INGRESS"

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
}

# Custom firewall rules
resource "google_compute_firewall" "custom" {
  for_each = var.custom_firewall_rules

  name    = "${var.name_prefix}-${each.key}"
  project = var.project_id
  network = google_compute_network.main.id

  description = each.value.description
  priority    = each.value.priority
  direction   = each.value.direction

  dynamic "allow" {
    for_each = each.value.allow != null ? each.value.allow : []
    content {
      protocol = allow.value.protocol
      ports    = lookup(allow.value, "ports", null)
    }
  }

  dynamic "deny" {
    for_each = each.value.deny != null ? each.value.deny : []
    content {
      protocol = deny.value.protocol
      ports    = lookup(deny.value, "ports", null)
    }
  }

  source_ranges      = lookup(each.value, "source_ranges", null)
  destination_ranges = lookup(each.value, "destination_ranges", null)
  source_tags        = lookup(each.value, "source_tags", null)
  target_tags        = lookup(each.value, "target_tags", null)
}

#######################
# Private Service Connection
# (For Cloud SQL, Memorystore, etc.)
#######################

# Allocate IP range for private services
resource "google_compute_global_address" "private_services" {
  count = var.enable_private_service_connection ? 1 : 0

  name          = "${var.name_prefix}-private-services"
  project       = var.project_id
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = var.private_services_prefix_length
  network       = google_compute_network.main.id

  description = "IP range for private service connections (Cloud SQL, Memorystore, etc.)"
}

# Create private VPC connection for Google services
resource "google_service_networking_connection" "private_services" {
  count = var.enable_private_service_connection ? 1 : 0

  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services[0].name]
}

#######################
# VPC Peering DNS (for private services)
#######################

# Enable DNS for private service peering
resource "google_compute_network_peering_routes_config" "private_services_dns" {
  count = var.enable_private_service_connection ? 1 : 0

  project = var.project_id
  peering = google_service_networking_connection.private_services[0].peering
  network = google_compute_network.main.name

  import_custom_routes = true
  export_custom_routes = true
}

#######################
# Cloud Armor Security Policy
# (Optional - for DDoS protection)
#######################

resource "google_compute_security_policy" "cloud_armor" {
  count = var.enable_cloud_armor ? 1 : 0

  name    = "${var.name_prefix}-cloud-armor-policy"
  project = var.project_id

  description = "Cloud Armor security policy for ${var.name_prefix}"

  # Default rule
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default rule - allow all"
  }

  # Rate limiting rule
  dynamic "rule" {
    for_each = var.cloud_armor_rate_limit_threshold > 0 ? [1] : []
    content {
      action   = "rate_based_ban"
      priority = "1000"
      match {
        versioned_expr = "SRC_IPS_V1"
        config {
          src_ip_ranges = ["*"]
        }
      }
      rate_limit_options {
        conform_action = "allow"
        exceed_action  = "deny(429)"
        enforce_on_key = "IP"
        ban_duration_sec = var.cloud_armor_ban_duration_sec
        rate_limit_threshold {
          count        = var.cloud_armor_rate_limit_threshold
          interval_sec = var.cloud_armor_rate_limit_interval
        }
      }
      description = "Rate limit: ${var.cloud_armor_rate_limit_threshold} requests per ${var.cloud_armor_rate_limit_interval}s"
    }
  }

  # Custom Cloud Armor rules
  dynamic "rule" {
    for_each = var.cloud_armor_rules
    content {
      action      = rule.value.action
      priority    = rule.value.priority
      description = rule.value.description

      match {
        versioned_expr = lookup(rule.value, "versioned_expr", "SRC_IPS_V1")
        config {
          src_ip_ranges = lookup(rule.value, "src_ip_ranges", ["*"])
        }
      }

      dynamic "rate_limit_options" {
        for_each = lookup(rule.value, "rate_limit_options", null) != null ? [rule.value.rate_limit_options] : []
        content {
          conform_action   = rate_limit_options.value.conform_action
          exceed_action    = rate_limit_options.value.exceed_action
          enforce_on_key   = rate_limit_options.value.enforce_on_key
          ban_duration_sec = lookup(rate_limit_options.value, "ban_duration_sec", 600)

          rate_limit_threshold {
            count        = rate_limit_options.value.rate_limit_threshold.count
            interval_sec = rate_limit_options.value.rate_limit_threshold.interval_sec
          }
        }
      }
    }
  }

  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = var.enable_cloud_armor_adaptive_protection
    }
  }
}
