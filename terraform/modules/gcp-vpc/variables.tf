#######################
# General Variables
#######################

variable "project_id" {
  description = "GCP project ID"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Project ID must be 6-30 characters, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string

  validation {
    condition     = length(var.name_prefix) <= 20 && can(regex("^[a-z][a-z0-9-]*$", var.name_prefix))
    error_message = "Name prefix must be 20 characters or less, start with a letter, and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "region" {
  description = "GCP region for regional resources (subnets, Cloud NAT, etc.)"
  type        = string

  validation {
    condition = contains([
      "us-central1", "us-east1", "us-east4", "us-west1", "us-west2", "us-west3", "us-west4",
      "europe-west1", "europe-west2", "europe-west3", "europe-west4", "europe-west6",
      "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2", "asia-northeast3",
      "asia-south1", "asia-southeast1", "asia-southeast2",
      "australia-southeast1", "australia-southeast2",
      "southamerica-east1", "northamerica-northeast1"
    ], var.region)
    error_message = "Region must be a valid GCP region."
  }
}

variable "cluster_name" {
  description = "Name of the GKE cluster (used for documentation and tagging)"
  type        = string

  validation {
    condition     = length(var.cluster_name) > 0 && length(var.cluster_name) <= 40
    error_message = "Cluster name must be 1-40 characters."
  }
}

#######################
# VPC Configuration
#######################

variable "routing_mode" {
  description = "VPC routing mode (REGIONAL or GLOBAL)"
  type        = string
  default     = "REGIONAL"

  validation {
    condition     = contains(["REGIONAL", "GLOBAL"], var.routing_mode)
    error_message = "Routing mode must be either REGIONAL or GLOBAL."
  }
}

#######################
# Subnet Configuration
#######################

variable "nodes_cidr" {
  description = "CIDR block for GKE nodes subnet"
  type        = string
  default     = "10.0.0.0/20"  # 4096 IPs

  validation {
    condition     = can(cidrhost(var.nodes_cidr, 0))
    error_message = "Nodes CIDR must be a valid IPv4 CIDR block."
  }
}

variable "pods_cidr" {
  description = "Secondary CIDR block for GKE pods"
  type        = string
  default     = "10.4.0.0/14"  # 262k IPs (supports large clusters)

  validation {
    condition     = can(cidrhost(var.pods_cidr, 0))
    error_message = "Pods CIDR must be a valid IPv4 CIDR block."
  }
}

variable "services_cidr" {
  description = "Secondary CIDR block for GKE services"
  type        = string
  default     = "10.8.0.0/20"  # 4096 IPs

  validation {
    condition     = can(cidrhost(var.services_cidr, 0))
    error_message = "Services CIDR must be a valid IPv4 CIDR block."
  }
}

variable "create_public_subnet" {
  description = "Create a public subnet for load balancers and bastion hosts"
  type        = bool
  default     = false
}

variable "public_cidr" {
  description = "CIDR block for public subnet (if enabled)"
  type        = string
  default     = "10.1.0.0/24"  # 256 IPs

  validation {
    condition     = can(cidrhost(var.public_cidr, 0))
    error_message = "Public CIDR must be a valid IPv4 CIDR block."
  }
}

variable "create_management_subnet" {
  description = "Create a management subnet for operational tooling"
  type        = bool
  default     = false
}

variable "management_cidr" {
  description = "CIDR block for management subnet (if enabled)"
  type        = string
  default     = "10.2.0.0/24"  # 256 IPs

  validation {
    condition     = can(cidrhost(var.management_cidr, 0))
    error_message = "Management CIDR must be a valid IPv4 CIDR block."
  }
}

#######################
# Cloud Router & NAT
#######################

variable "cloud_router_asn" {
  description = "ASN for Cloud Router BGP"
  type        = number
  default     = 64512  # Private ASN range

  validation {
    condition     = (var.cloud_router_asn >= 64512 && var.cloud_router_asn <= 65534) || (var.cloud_router_asn >= 4200000000 && var.cloud_router_asn <= 4294967294)
    error_message = "ASN must be in private range: 64512-65534 or 4200000000-4294967294."
  }
}

variable "advertised_ip_ranges" {
  description = "List of IP ranges to advertise via BGP"
  type = list(object({
    range       = string
    description = string
  }))
  default = []
}

variable "nat_ip_allocate_option" {
  description = "NAT IP allocation mode (AUTO_ONLY or MANUAL_ONLY)"
  type        = string
  default     = "AUTO_ONLY"

  validation {
    condition     = contains(["AUTO_ONLY", "MANUAL_ONLY"], var.nat_ip_allocate_option)
    error_message = "NAT IP allocate option must be AUTO_ONLY or MANUAL_ONLY."
  }
}

variable "nat_ip_count" {
  description = "Number of static NAT IPs to allocate (only if nat_ip_allocate_option is MANUAL_ONLY)"
  type        = number
  default     = 1

  validation {
    condition     = var.nat_ip_count >= 1 && var.nat_ip_count <= 10
    error_message = "NAT IP count must be between 1 and 10."
  }
}

variable "enable_dynamic_port_allocation" {
  description = "Enable dynamic port allocation for Cloud NAT"
  type        = bool
  default     = true
}

variable "nat_min_ports_per_vm" {
  description = "Minimum ports allocated per VM for NAT"
  type        = number
  default     = 64

  validation {
    condition     = var.nat_min_ports_per_vm >= 64 && var.nat_min_ports_per_vm <= 65536
    error_message = "Minimum ports per VM must be between 64 and 65536."
  }
}

variable "nat_max_ports_per_vm" {
  description = "Maximum ports allocated per VM for NAT (only with dynamic allocation)"
  type        = number
  default     = 32768

  validation {
    condition     = var.nat_max_ports_per_vm >= 64 && var.nat_max_ports_per_vm <= 65536
    error_message = "Maximum ports per VM must be between 64 and 65536."
  }
}

variable "enable_nat_logging" {
  description = "Enable logging for Cloud NAT"
  type        = bool
  default     = true
}

variable "nat_logging_filter" {
  description = "Filter for NAT logging (ERRORS_ONLY, TRANSLATIONS_ONLY, or ALL)"
  type        = string
  default     = "ERRORS_ONLY"

  validation {
    condition     = contains(["ERRORS_ONLY", "TRANSLATIONS_ONLY", "ALL"], var.nat_logging_filter)
    error_message = "NAT logging filter must be ERRORS_ONLY, TRANSLATIONS_ONLY, or ALL."
  }
}

variable "nat_tcp_established_idle_timeout" {
  description = "Timeout for TCP established connections (seconds)"
  type        = number
  default     = 1200  # 20 minutes

  validation {
    condition     = var.nat_tcp_established_idle_timeout >= 30 && var.nat_tcp_established_idle_timeout <= 7200
    error_message = "TCP established idle timeout must be between 30 and 7200 seconds."
  }
}

variable "nat_tcp_time_wait_timeout" {
  description = "Timeout for TCP connections in TIME_WAIT state (seconds)"
  type        = number
  default     = 120  # 2 minutes

  validation {
    condition     = var.nat_tcp_time_wait_timeout >= 30 && var.nat_tcp_time_wait_timeout <= 7200
    error_message = "TCP time wait timeout must be between 30 and 7200 seconds."
  }
}

variable "nat_tcp_transitory_idle_timeout" {
  description = "Timeout for TCP transitory connections (seconds)"
  type        = number
  default     = 30

  validation {
    condition     = var.nat_tcp_transitory_idle_timeout >= 30 && var.nat_tcp_transitory_idle_timeout <= 7200
    error_message = "TCP transitory idle timeout must be between 30 and 7200 seconds."
  }
}

variable "nat_udp_idle_timeout" {
  description = "Timeout for UDP connections (seconds)"
  type        = number
  default     = 30

  validation {
    condition     = var.nat_udp_idle_timeout >= 30 && var.nat_udp_idle_timeout <= 7200
    error_message = "UDP idle timeout must be between 30 and 7200 seconds."
  }
}

#######################
# VPC Flow Logs
#######################

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs on subnets"
  type        = bool
  default     = true
}

variable "flow_logs_aggregation_interval" {
  description = "Aggregation interval for VPC Flow Logs"
  type        = string
  default     = "INTERVAL_5_SEC"

  validation {
    condition     = contains(["INTERVAL_5_SEC", "INTERVAL_30_SEC", "INTERVAL_1_MIN", "INTERVAL_5_MIN", "INTERVAL_10_MIN", "INTERVAL_15_MIN"], var.flow_logs_aggregation_interval)
    error_message = "Flow logs aggregation interval must be a valid interval."
  }
}

variable "flow_logs_sampling" {
  description = "Sampling rate for VPC Flow Logs (0.0-1.0)"
  type        = number
  default     = 0.5

  validation {
    condition     = var.flow_logs_sampling >= 0.0 && var.flow_logs_sampling <= 1.0
    error_message = "Flow logs sampling must be between 0.0 and 1.0."
  }
}

variable "flow_logs_metadata" {
  description = "Metadata to include in VPC Flow Logs"
  type        = string
  default     = "INCLUDE_ALL_METADATA"

  validation {
    condition     = contains(["EXCLUDE_ALL_METADATA", "INCLUDE_ALL_METADATA", "CUSTOM_METADATA"], var.flow_logs_metadata)
    error_message = "Flow logs metadata must be EXCLUDE_ALL_METADATA, INCLUDE_ALL_METADATA, or CUSTOM_METADATA."
  }
}

variable "flow_logs_filter" {
  description = "Filter expression for VPC Flow Logs (empty string means no filter)"
  type        = string
  default     = ""
}

#######################
# Firewall Rules
#######################

variable "enable_iap_ssh" {
  description = "Enable SSH access via Identity-Aware Proxy"
  type        = bool
  default     = true
}

variable "enable_deny_all_ingress" {
  description = "Add a deny-all ingress rule (lowest priority)"
  type        = bool
  default     = false
}

variable "custom_firewall_rules" {
  description = "Map of custom firewall rules"
  type = map(object({
    description        = string
    priority           = number
    direction          = string
    allow              = optional(list(object({
      protocol = string
      ports    = optional(list(string))
    })))
    deny               = optional(list(object({
      protocol = string
      ports    = optional(list(string))
    })))
    source_ranges      = optional(list(string))
    destination_ranges = optional(list(string))
    source_tags        = optional(list(string))
    target_tags        = optional(list(string))
  }))
  default = {}
}

#######################
# Private Service Connection
#######################

variable "enable_private_service_connection" {
  description = "Enable private service connection for Cloud SQL, Memorystore, etc."
  type        = bool
  default     = true
}

variable "private_services_prefix_length" {
  description = "Prefix length for private services IP range"
  type        = number
  default     = 16  # /16 = 65k IPs

  validation {
    condition     = var.private_services_prefix_length >= 16 && var.private_services_prefix_length <= 24
    error_message = "Private services prefix length must be between 16 and 24."
  }
}

#######################
# Cloud Armor
#######################

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor security policy"
  type        = bool
  default     = false
}

variable "cloud_armor_rate_limit_threshold" {
  description = "Rate limit threshold (requests per interval, 0 = disabled)"
  type        = number
  default     = 0

  validation {
    condition     = var.cloud_armor_rate_limit_threshold >= 0
    error_message = "Cloud Armor rate limit threshold must be non-negative."
  }
}

variable "cloud_armor_rate_limit_interval" {
  description = "Rate limit interval in seconds"
  type        = number
  default     = 60

  validation {
    condition     = contains([60, 120, 180, 240, 300, 600], var.cloud_armor_rate_limit_interval)
    error_message = "Rate limit interval must be 60, 120, 180, 240, 300, or 600 seconds."
  }
}

variable "cloud_armor_ban_duration_sec" {
  description = "Ban duration in seconds for rate-limited IPs"
  type        = number
  default     = 600  # 10 minutes

  validation {
    condition     = var.cloud_armor_ban_duration_sec >= 60 && var.cloud_armor_ban_duration_sec <= 86400
    error_message = "Ban duration must be between 60 and 86400 seconds (1 minute to 1 day)."
  }
}

variable "cloud_armor_rules" {
  description = "Custom Cloud Armor rules"
  type = list(object({
    action             = string
    priority           = number
    description        = string
    versioned_expr     = optional(string)
    src_ip_ranges      = optional(list(string))
    rate_limit_options = optional(object({
      conform_action   = string
      exceed_action    = string
      enforce_on_key   = string
      ban_duration_sec = optional(number)
      rate_limit_threshold = object({
        count        = number
        interval_sec = number
      })
    }))
  }))
  default = []
}

variable "enable_cloud_armor_adaptive_protection" {
  description = "Enable Cloud Armor adaptive protection (ML-based DDoS detection)"
  type        = bool
  default     = false
}

#######################
# Labels
#######################

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for k, v in var.labels : can(regex("^[a-z][a-z0-9_-]{0,62}$", k))
    ])
    error_message = "Label keys must start with a lowercase letter and contain only lowercase letters, numbers, underscores, and hyphens (max 63 characters)."
  }
}
