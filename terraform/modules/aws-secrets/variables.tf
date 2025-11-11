variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "kubernetes_namespace" {
  description = "Kubernetes namespace for External Secrets Operator"
  type        = string
}

variable "create_irsa_role" {
  description = "Create IAM role for IRSA (EKS Workload Identity)"
  type        = bool
  default     = true
}

variable "oidc_provider_arn" {
  description = "EKS OIDC provider ARN for IRSA"
  type        = string
  default     = ""
}

variable "kms_key_id" {
  description = "KMS key ID for Customer Managed Key (CMK) encryption. Use in production for compliance. Set to null for AWS-managed keys in dev/staging."
  type        = string
  default     = null
}

variable "recovery_window_in_days" {
  description = "Number of days AWS Secrets Manager waits before permanently deleting a secret (0-30). Set to 0 for immediate deletion (not recommended)."
  type        = number
  default     = 30
  validation {
    condition     = var.recovery_window_in_days >= 0 && var.recovery_window_in_days <= 30
    error_message = "recovery_window_in_days must be between 0 and 30."
  }
}

variable "tags" {
  description = "Tags to apply to all secrets"
  type        = map(string)
  default     = {}
}
