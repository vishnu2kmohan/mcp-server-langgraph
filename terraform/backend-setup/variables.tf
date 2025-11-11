variable "region" {
  description = "AWS region for the backend resources"
  type        = string
  default     = "us-east-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]{1}$", var.region))
    error_message = "Region must be a valid AWS region format (e.g., us-east-1)."
  }
}

variable "kms_key_arn" {
  description = "KMS key ARN for DynamoDB table encryption. Use Customer Managed Key (CMK) in production for compliance. Set to null for AWS-managed key."
  type        = string
  default     = null
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for DynamoDB state lock table (recommended for production)"
  type        = bool
  default     = true
}
