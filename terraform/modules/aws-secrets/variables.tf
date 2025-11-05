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

variable "tags" {
  description = "Tags to apply to all secrets"
  type        = map(string)
  default     = {}
}
