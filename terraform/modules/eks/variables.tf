variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string

  validation {
    condition     = length(var.cluster_name) <= 40
    error_message = "Cluster name must be 40 characters or less."
  }
}

variable "kubernetes_version" {
  description = "Kubernetes version to use for the EKS cluster"
  type        = string
  default     = "1.28"

  validation {
    condition     = can(regex("^1\\.(2[7-9]|[3-9][0-9])$", var.kubernetes_version))
    error_message = "Kubernetes version must be 1.27 or higher."
  }
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where EKS cluster will be created"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for EKS nodes"
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "At least 2 private subnets are required for high availability."
  }
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for EKS control plane"
  type        = list(string)
  default     = []
}

#######################
# Cluster Configuration
#######################

variable "cluster_endpoint_private_access" {
  description = "Enable private API server endpoint"
  type        = bool
  default     = true
}

variable "cluster_endpoint_public_access" {
  description = "Enable public API server endpoint"
  type        = bool
  default     = true
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "List of CIDR blocks that can access the public API server endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "cluster_enabled_log_types" {
  description = "List of control plane logging types to enable"
  type        = list(string)
  default     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  validation {
    condition = alltrue([
      for log_type in var.cluster_enabled_log_types :
      contains(["api", "audit", "authenticator", "controllerManager", "scheduler"], log_type)
    ])
    error_message = "Log types must be one of: api, audit, authenticator, controllerManager, scheduler."
  }
}

variable "cluster_log_retention_days" {
  description = "Number of days to retain cluster logs"
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.cluster_log_retention_days)
    error_message = "Log retention must be a valid CloudWatch Logs retention period."
  }
}

variable "cluster_log_kms_key_id" {
  description = "KMS key ID for encrypting cluster logs"
  type        = string
  default     = null
}

variable "cluster_encryption_key_arn" {
  description = "KMS key ARN for cluster secret encryption (if null, creates new key)"
  type        = string
  default     = null
}

#######################
# General Node Group
#######################

variable "enable_general_node_group" {
  description = "Enable general-purpose node group"
  type        = bool
  default     = true
}

variable "general_node_group_desired_size" {
  description = "Desired number of nodes in general node group"
  type        = number
  default     = 3
}

variable "general_node_group_min_size" {
  description = "Minimum number of nodes in general node group"
  type        = number
  default     = 2
}

variable "general_node_group_max_size" {
  description = "Maximum number of nodes in general node group"
  type        = number
  default     = 10
}

variable "general_node_group_instance_types" {
  description = "List of instance types for general node group"
  type        = list(string)
  default     = ["t3.large", "t3a.large"]
}

variable "general_node_group_capacity_type" {
  description = "Capacity type for general node group (ON_DEMAND or SPOT)"
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.general_node_group_capacity_type)
    error_message = "Capacity type must be ON_DEMAND or SPOT."
  }
}

variable "general_node_group_disk_size" {
  description = "Disk size in GB for general node group"
  type        = number
  default     = 100
}

variable "general_node_group_labels" {
  description = "Labels for general node group"
  type        = map(string)
  default     = {}
}

variable "general_node_group_taints" {
  description = "Taints for general node group"
  type = list(object({
    key    = string
    value  = string
    effect = string
  }))
  default = []
}

variable "general_node_group_tags" {
  description = "Additional tags for general node group"
  type        = map(string)
  default     = {}
}

#######################
# Compute Node Group
#######################

variable "enable_compute_node_group" {
  description = "Enable compute-optimized node group"
  type        = bool
  default     = false
}

variable "compute_node_group_desired_size" {
  description = "Desired number of nodes in compute node group"
  type        = number
  default     = 2
}

variable "compute_node_group_min_size" {
  description = "Minimum number of nodes in compute node group"
  type        = number
  default     = 0
}

variable "compute_node_group_max_size" {
  description = "Maximum number of nodes in compute node group"
  type        = number
  default     = 20
}

variable "compute_node_group_instance_types" {
  description = "List of instance types for compute node group"
  type        = list(string)
  default     = ["c6i.2xlarge", "c6a.2xlarge"]
}

variable "compute_node_group_capacity_type" {
  description = "Capacity type for compute node group"
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.compute_node_group_capacity_type)
    error_message = "Capacity type must be ON_DEMAND or SPOT."
  }
}

variable "compute_node_group_disk_size" {
  description = "Disk size in GB for compute node group"
  type        = number
  default     = 100
}

variable "compute_node_group_labels" {
  description = "Labels for compute node group"
  type        = map(string)
  default     = {}
}

variable "compute_node_group_taints" {
  description = "Taints for compute node group"
  type = list(object({
    key    = string
    value  = string
    effect = string
  }))
  default = []
}

variable "compute_node_group_tags" {
  description = "Additional tags for compute node group"
  type        = map(string)
  default     = {}
}

#######################
# Spot Node Group
#######################

variable "enable_spot_node_group" {
  description = "Enable spot instance node group"
  type        = bool
  default     = false
}

variable "spot_node_group_desired_size" {
  description = "Desired number of nodes in spot node group"
  type        = number
  default     = 2
}

variable "spot_node_group_min_size" {
  description = "Minimum number of nodes in spot node group"
  type        = number
  default     = 0
}

variable "spot_node_group_max_size" {
  description = "Maximum number of nodes in spot node group"
  type        = number
  default     = 20
}

variable "spot_node_group_instance_types" {
  description = "List of instance types for spot node group (diversified for interruption resilience)"
  type        = list(string)
  default     = ["t3.large", "t3a.large", "t3.xlarge", "t3a.xlarge"]
}

variable "spot_node_group_disk_size" {
  description = "Disk size in GB for spot node group"
  type        = number
  default     = 100
}

variable "spot_node_group_labels" {
  description = "Labels for spot node group"
  type        = map(string)
  default     = {}
}

variable "spot_node_group_taints" {
  description = "Additional taints for spot node group (spot taint is added automatically)"
  type = list(object({
    key    = string
    value  = string
    effect = string
  }))
  default = []
}

variable "spot_node_group_tags" {
  description = "Additional tags for spot node group"
  type        = map(string)
  default     = {}
}

#######################
# EKS Addons
#######################

variable "vpc_cni_addon_version" {
  description = "Version of VPC CNI addon"
  type        = string
  default     = null # Uses latest compatible version
}

variable "coredns_addon_version" {
  description = "Version of CoreDNS addon"
  type        = string
  default     = null
}

variable "kube_proxy_addon_version" {
  description = "Version of kube-proxy addon"
  type        = string
  default     = null
}

variable "enable_ebs_csi_driver" {
  description = "Enable EBS CSI driver addon"
  type        = bool
  default     = true
}

variable "ebs_csi_driver_version" {
  description = "Version of EBS CSI driver addon"
  type        = string
  default     = null
}

#######################
# IRSA Configuration
#######################

variable "enable_cluster_autoscaler_irsa" {
  description = "Create IRSA role for Cluster Autoscaler"
  type        = bool
  default     = true
}

variable "create_application_irsa_role" {
  description = "Create IRSA role for application pods"
  type        = bool
  default     = true
}

variable "application_service_account_name" {
  description = "Name of the application service account"
  type        = string
  default     = "mcp-server-langgraph"
}

variable "application_service_account_namespace" {
  description = "Namespace of the application service account"
  type        = string
  default     = "mcp-server-langgraph"
}

variable "application_secrets_arns" {
  description = "List of Secrets Manager ARNs the application can access"
  type        = list(string)
  default     = ["*"]
}

variable "application_kms_key_arns" {
  description = "List of KMS key ARNs the application can use for decryption"
  type        = list(string)
  default     = ["*"]
}

variable "enable_xray" {
  description = "Enable X-Ray permissions for application"
  type        = bool
  default     = true
}

#######################
# Additional Features
#######################

variable "enable_ssm_access" {
  description = "Enable SSM access to nodes for debugging"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
