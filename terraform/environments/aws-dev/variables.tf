variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

#######################
# VPC Configuration
#######################

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.2.0.0/16"
}

#######################
# EKS Configuration
#######################

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "cluster_endpoint_public_access" {
  description = "Enable public access to EKS API endpoint"
  type        = bool
  default     = true
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDR blocks allowed to access public API endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Open for dev convenience
}

variable "general_node_instance_types" {
  description = "Instance types for general node group"
  type        = list(string)
  default     = ["t3.medium", "t3a.medium"] # Smallest for dev
}

variable "enable_spot_nodes" {
  description = "Enable spot instance node group"
  type        = bool
  default     = true
}

#######################
# RDS Configuration
#######################

variable "postgres_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16.4"
}

variable "postgres_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro" # Smallest for dev
}

variable "postgres_allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 20 # Minimal for dev
}

variable "postgres_max_allocated_storage" {
  description = "Maximum storage for autoscaling"
  type        = number
  default     = 50 # Minimal for dev
}

variable "postgres_database_name" {
  description = "Name of the initial database"
  type        = string
  default     = "mcp_langgraph_dev"
}

variable "postgres_master_username" {
  description = "Master username for PostgreSQL"
  type        = string
  default     = "postgres"
}

#######################
# Redis Configuration
#######################

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.1"
}

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro" # Smallest for dev
}

#######################
# Monitoring
#######################

variable "alarm_sns_topic_arns" {
  description = "SNS topic ARNs for CloudWatch alarms"
  type        = list(string)
  default     = []
}
