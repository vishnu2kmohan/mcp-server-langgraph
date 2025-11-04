output "replication_group_id" {
  description = "Replication group ID"
  value       = var.cluster_mode_enabled ? aws_elasticache_replication_group.cluster_mode[0].id : aws_elasticache_replication_group.standard[0].id
}

output "replication_group_arn" {
  description = "Replication group ARN"
  value       = var.cluster_mode_enabled ? aws_elasticache_replication_group.cluster_mode[0].arn : aws_elasticache_replication_group.standard[0].arn
}

output "primary_endpoint_address" {
  description = "Primary endpoint address"
  value       = var.cluster_mode_enabled ? aws_elasticache_replication_group.cluster_mode[0].configuration_endpoint_address : aws_elasticache_replication_group.standard[0].primary_endpoint_address
}

output "reader_endpoint_address" {
  description = "Reader endpoint address (non-cluster mode only)"
  value       = var.cluster_mode_enabled ? null : aws_elasticache_replication_group.standard[0].reader_endpoint_address
}

output "port" {
  description = "Redis port"
  value       = var.port
}

output "configuration_endpoint_address" {
  description = "Configuration endpoint address (cluster mode only)"
  value       = var.cluster_mode_enabled ? aws_elasticache_replication_group.cluster_mode[0].configuration_endpoint_address : null
}

output "engine_version_actual" {
  description = "Actual engine version"
  value       = var.cluster_mode_enabled ? aws_elasticache_replication_group.cluster_mode[0].engine_version_actual : aws_elasticache_replication_group.standard[0].engine_version_actual
}

output "auth_token" {
  description = "Redis auth token (if transit encryption enabled)"
  value       = var.transit_encryption_enabled ? (var.auth_token != "" ? var.auth_token : try(random_password.auth_token[0].result, "")) : null
  sensitive   = true
}

output "subnet_group_name" {
  description = "Subnet group name"
  value       = aws_elasticache_subnet_group.main.name
}

output "parameter_group_name" {
  description = "Parameter group name"
  value       = aws_elasticache_parameter_group.main.name
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.redis.id
}

output "security_group_arn" {
  description = "Security group ARN"
  value       = aws_security_group.redis.arn
}

output "kms_key_id" {
  description = "KMS key ID used for encryption"
  value       = var.at_rest_encryption_enabled ? (var.kms_key_id != null ? var.kms_key_id : try(aws_kms_key.redis[0].id, "")) : null
}

output "kms_key_arn" {
  description = "KMS key ARN used for encryption"
  value       = var.at_rest_encryption_enabled ? (var.kms_key_id != null ? var.kms_key_id : try(aws_kms_key.redis[0].arn, "")) : null
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    slow_log   = try(aws_cloudwatch_log_group.slow_log[0].name, "")
    engine_log = try(aws_cloudwatch_log_group.engine_log[0].name, "")
  }
}

# Connection strings
output "connection_string" {
  description = "Redis connection string"
  value = var.cluster_mode_enabled ? (
    var.transit_encryption_enabled ?
    "rediss://:${try(random_password.auth_token[0].result, var.auth_token)}@${aws_elasticache_replication_group.cluster_mode[0].configuration_endpoint_address}:${var.port}" :
    "redis://${aws_elasticache_replication_group.cluster_mode[0].configuration_endpoint_address}:${var.port}"
    ) : (
    var.transit_encryption_enabled ?
    "rediss://:${try(random_password.auth_token[0].result, var.auth_token)}@${aws_elasticache_replication_group.standard[0].primary_endpoint_address}:${var.port}" :
    "redis://${aws_elasticache_replication_group.standard[0].primary_endpoint_address}:${var.port}"
  )
  sensitive = true
}

output "redis_url" {
  description = "Redis URL for connection"
  value = var.cluster_mode_enabled ? (
    var.transit_encryption_enabled ?
    "rediss://${aws_elasticache_replication_group.cluster_mode[0].configuration_endpoint_address}:${var.port}" :
    "redis://${aws_elasticache_replication_group.cluster_mode[0].configuration_endpoint_address}:${var.port}"
    ) : (
    var.transit_encryption_enabled ?
    "rediss://${aws_elasticache_replication_group.standard[0].primary_endpoint_address}:${var.port}" :
    "redis://${aws_elasticache_replication_group.standard[0].primary_endpoint_address}:${var.port}"
  )
}

# Kubernetes secret data
output "kubernetes_secret_data" {
  description = "Data for Kubernetes secret (base64 encoded)"
  value = {
    host = base64encode(var.cluster_mode_enabled ?
      aws_elasticache_replication_group.cluster_mode[0].configuration_endpoint_address :
    aws_elasticache_replication_group.standard[0].primary_endpoint_address)
    port     = base64encode(tostring(var.port))
    password = var.transit_encryption_enabled ? base64encode(var.auth_token != "" ? var.auth_token : try(random_password.auth_token[0].result, "")) : base64encode("")
    tls      = base64encode(var.transit_encryption_enabled ? "true" : "false")
  }
  sensitive = true
}

# Cluster information
output "cluster_info" {
  description = "Redis cluster information"
  value = {
    mode                 = var.cluster_mode_enabled ? "cluster" : "standard"
    node_type            = var.node_type
    engine_version       = var.engine_version
    num_shards           = var.cluster_mode_enabled ? var.num_node_groups : null
    replicas_per_shard   = var.cluster_mode_enabled ? var.replicas_per_node_group : null
    num_nodes            = var.cluster_mode_enabled ? null : var.num_cache_clusters
    multi_az             = var.multi_az_enabled
    encrypted_at_rest    = var.at_rest_encryption_enabled
    encrypted_in_transit = var.transit_encryption_enabled
  }
}

# Alarm ARNs
output "cloudwatch_alarm_arns" {
  description = "CloudWatch alarm ARNs"
  value = {
    cpu_alarm             = try(aws_cloudwatch_metric_alarm.cpu[0].arn, "")
    memory_alarm          = try(aws_cloudwatch_metric_alarm.memory[0].arn, "")
    evictions_alarm       = try(aws_cloudwatch_metric_alarm.evictions[0].arn, "")
    replication_lag_alarm = try(aws_cloudwatch_metric_alarm.replication_lag[0].arn, "")
  }
}
