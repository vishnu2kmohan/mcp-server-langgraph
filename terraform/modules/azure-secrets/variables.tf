variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}

variable "sku_name" {
  description = "Key Vault SKU (standard or premium)"
  type        = string
  default     = "standard"
}

variable "enable_purge_protection" {
  description = "Enable purge protection"
  type        = bool
  default     = false
}

variable "network_default_action" {
  description = "Default network action (Allow or Deny)"
  type        = string
  default     = "Allow"
}

variable "external_secrets_principal_id" {
  description = "Managed Identity principal ID for External Secrets Operator"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
