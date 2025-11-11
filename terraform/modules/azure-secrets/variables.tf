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
  description = "Enable purge protection (recommended for production to prevent accidental deletion)"
  type        = bool
  default     = true # Changed from false - BREAKING CHANGE for security compliance
}

variable "network_default_action" {
  description = "Default network action - Deny enforces zero-trust networking (requires allowed_ip_ranges)"
  type        = string
  default     = "Deny" # Changed from "Allow" - BREAKING CHANGE for security compliance
  validation {
    condition     = contains(["Allow", "Deny"], var.network_default_action)
    error_message = "network_default_action must be either 'Allow' or 'Deny'."
  }
}

variable "allowed_ip_ranges" {
  description = "IP ranges allowed to access Key Vault (CIDR notation, e.g., ['203.0.113.0/24']). Required when network_default_action is 'Deny'."
  type        = list(string)
  default     = []
  validation {
    condition     = alltrue([for cidr in var.allowed_ip_ranges : can(regex("^([0-9]{1,3}\\.){3}[0-9]{1,3}/[0-9]{1,2}$", cidr))])
    error_message = "allowed_ip_ranges must be valid CIDR notation (e.g., '203.0.113.0/24')."
  }
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
