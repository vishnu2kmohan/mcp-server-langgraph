#######################
# General
#######################

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "team" {
  description = "Team name for labeling"
  type        = string
  default     = "platform"
}

variable "cost_center" {
  description = "Cost center for billing allocation"
  type        = string
  default     = "engineering"
}

#######################
# VPC Configuration
#######################

variable "nodes_cidr" {
  description = "CIDR block for GKE nodes"
  type        = string
  default     = "10.0.0.0/20" # 4096 IPs
}

variable "pods_cidr" {
  description = "CIDR block for GKE pods"
  type        = string
  default     = "10.4.0.0/14" # 262k IPs
}

variable "services_cidr" {
  description = "CIDR block for GKE services"
  type        = string
  default     = "10.8.0.0/20" # 4096 IPs
}

variable "enable_cloud_armor" {
  description = "Enable Cloud Armor for DDoS protection"
  type        = bool
  default     = true
}

#######################
# GKE Configuration
#######################

variable "enable_private_endpoint" {
  description = "Enable private endpoint (control plane only accessible via VPC)"
  type        = bool
  default     = true # Enabled for production security
}

variable "master_ipv4_cidr_block" {
  description = "CIDR block for GKE master nodes"
  type        = string
  default     = "172.16.0.0/28"
}

variable "enable_master_authorized_networks" {
  description = "Enable master authorized networks"
  type        = bool
  default     = true
}

variable "master_authorized_networks_cidrs" {
  description = "CIDR blocks authorized to access the control plane - restrict to specific VPC subnets"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  # TODO: Replace with your actual VPC CIDR blocks (specific /16 or /24 ranges)
  # Restricted from 10.0.0.0/8 to specific VPC subnet for better security
  default = [
    {
      cidr_block   = "10.0.0.0/16"
      display_name = "VPC Primary Subnet"
    }
  ]
}

variable "max_cluster_cpu" {
  description = "Maximum CPU cores for the cluster"
  type        = number
  default     = 1000
}

variable "max_cluster_memory" {
  description = "Maximum memory in GB for the cluster"
  type        = number
  default     = 10000
}

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization for image signing"
  type        = bool
  default     = false # Enable after setting up attestors
}

variable "enable_fleet_registration" {
  description = "Register cluster with GKE Fleet for Anthos features"
  type        = bool
  default     = false
}

variable "enable_gateway_api" {
  description = "Enable Gateway API for advanced ingress"
  type        = bool
  default     = false
}

#######################
# Cloud SQL Configuration
#######################

variable "cloudsql_tier" {
  description = "Cloud SQL machine type"
  type        = string
  default     = "db-custom-4-15360" # 4 vCPU, 15 GB RAM
}

variable "cloudsql_disk_size_gb" {
  description = "Initial disk size in GB"
  type        = number
  default     = 100
}

variable "cloudsql_disk_autoresize_limit_gb" {
  description = "Maximum disk size for autoresize (0 = unlimited)"
  type        = number
  default     = 1000
}

variable "additional_databases" {
  description = "Additional databases to create"
  type        = list(string)
  default     = []
}

variable "cloudsql_additional_users" {
  description = "Additional PostgreSQL users"
  type = map(object({
    password = optional(string)
    type     = optional(string)
  }))
  default   = {}
  sensitive = true
}

variable "cloudsql_read_replica_count" {
  description = "Number of read replicas"
  type        = number
  default     = 1
}

variable "cloudsql_read_replica_regions" {
  description = "Regions for read replicas"
  type        = list(string)
  default     = ["us-east1"]
}

#######################
# Memorystore Configuration
#######################

variable "redis_memory_size_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 5
}

variable "redis_create_cross_region_replica" {
  description = "Create cross-region read replicas for Redis"
  type        = bool
  default     = false
}

variable "redis_read_replica_regions" {
  description = "Regions for Redis read replicas"
  type        = list(string)
  default     = []
}

#######################
# Workload Identity Configuration
#######################

variable "app_namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "production-mcp-server-langgraph"
}

variable "app_secret_ids" {
  description = "Secret Manager secret IDs for application access"
  type        = list(string)
  default     = []
}

variable "app_storage_bucket" {
  description = "GCS bucket for application storage"
  type        = string
  default     = ""
}

variable "worker_pubsub_topics" {
  description = "Pub/Sub topics for worker access"
  type = list(object({
    topic = string
    role  = string
  }))
  default = []
}

variable "worker_pubsub_subscriptions" {
  description = "Pub/Sub subscriptions for worker access"
  type = list(object({
    subscription = string
    role         = string
  }))
  default = []
}

#######################
# Monitoring
#######################

variable "monitoring_notification_channels" {
  description = "Cloud Monitoring notification channel IDs"
  type        = list(string)
  default     = []
}
