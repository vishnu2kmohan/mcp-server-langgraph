# Cloud DNS Staging Module - Outputs

output "dns_zone_name" {
  description = "Name of the created Cloud DNS managed zone"
  value       = google_dns_managed_zone.staging_internal.name
}

output "dns_zone_dns_name" {
  description = "DNS name of the zone (staging.internal.)"
  value       = google_dns_managed_zone.staging_internal.dns_name
}

output "dns_zone_id" {
  description = "Identifier of the managed zone"
  value       = google_dns_managed_zone.staging_internal.id
}

output "dns_zone_name_servers" {
  description = "List of name servers for the zone"
  value       = google_dns_managed_zone.staging_internal.name_servers
}

output "cloudsql_dns_name" {
  description = "DNS name for Cloud SQL instance"
  value       = google_dns_record_set.cloudsql_staging.name
}

output "cloudsql_ip" {
  description = "IP address configured for Cloud SQL DNS record"
  value       = var.cloud_sql_private_ip
}

output "redis_dns_name" {
  description = "DNS name for primary Memorystore Redis instance"
  value       = google_dns_record_set.redis_staging.name
}

output "redis_ip" {
  description = "IP address configured for Redis DNS record"
  value       = var.memorystore_redis_host
}

output "redis_session_dns_name" {
  description = "DNS name for Memorystore Redis session store"
  value       = google_dns_record_set.redis_session_staging.name
}

output "redis_session_ip" {
  description = "IP address configured for Redis session DNS record"
  value       = var.memorystore_redis_session_host
}

output "verification_command" {
  description = "Command to verify DNS resolution from within GKE cluster"
  value       = <<-EOT
    kubectl run -it --rm dns-test \
      --image=gcr.io/google.com/cloudsdktool/cloud-sdk:slim \
      --namespace=staging-mcp-server-langgraph \
      --restart=Never \
      -- bash -c "nslookup cloudsql-staging.internal && nslookup redis-staging.internal && nslookup redis-session-staging.internal"
  EOT
}
