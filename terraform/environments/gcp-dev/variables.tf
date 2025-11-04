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

variable "app_namespace" {
  description = "Kubernetes namespace for the application"
  type        = string
  default     = "dev-mcp-server-langgraph"
}

variable "enable_monitoring_alerts" {
  description = "Enable monitoring alerts (set to false to save costs in dev)"
  type        = bool
  default     = false
}
