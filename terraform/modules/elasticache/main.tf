# ElastiCache Redis Cluster Module
# Creates a Redis cluster in cluster mode with Multi-AZ support for high availability

locals {
  cluster_id = var.cluster_id != "" ? var.cluster_id : "${var.name_prefix}-redis"

  # Cluster mode requires replication_group_id
  replication_group_id = var.cluster_mode_enabled ? local.cluster_id : null

  common_tags = merge(
    var.tags,
    {
      ManagedBy = "Terraform"
      Module    = "elasticache"
    }
  )
}

#######################
# Subnet Group
#######################

resource "aws_elasticache_subnet_group" "main" {
  name        = "${local.cluster_id}-subnet-group"
  description = "Subnet group for ${local.cluster_id}"
  subnet_ids  = var.subnet_ids

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_id}-subnet-group"
    }
  )
}

#######################
# Parameter Group
#######################

resource "aws_elasticache_parameter_group" "main" {
  name        = "${local.cluster_id}-params"
  family      = var.parameter_group_family
  description = "Parameter group for ${local.cluster_id}"

  # Cluster mode parameters
  dynamic "parameter" {
    for_each = var.cluster_mode_enabled ? [1] : []
    content {
      name  = "cluster-enabled"
      value = "yes"
    }
  }

  # Custom parameters
  dynamic "parameter" {
    for_each = var.parameters
    content {
      name  = parameter.value.name
      value = parameter.value.value
    }
  }

  # Performance tuning
  parameter {
    name  = "timeout"
    value = var.timeout
  }

  parameter {
    name  = "tcp-keepalive"
    value = "300"
  }

  parameter {
    name  = "maxmemory-policy"
    value = var.maxmemory_policy
  }

  # Persistence settings
  dynamic "parameter" {
    for_each = var.enable_snapshot ? [1] : []
    content {
      name  = "appendonly"
      value = "yes"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_id}-params"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

#######################
# Security Group
#######################

resource "aws_security_group" "redis" {
  name_prefix = "${local.cluster_id}-"
  description = "Security group for ${local.cluster_id} ElastiCache"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_id}-redis-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "redis_ingress_cidr" {
  count = length(var.allowed_cidr_blocks) > 0 ? 1 : 0

  type              = "ingress"
  description       = "Redis access from allowed CIDR blocks"
  from_port         = var.port
  to_port           = var.port
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  security_group_id = aws_security_group.redis.id
}

resource "aws_security_group_rule" "redis_ingress_security_groups" {
  for_each = toset(var.allowed_security_group_ids)

  type                     = "ingress"
  description              = "Redis access from security group ${each.value}"
  from_port                = var.port
  to_port                  = var.port
  protocol                 = "tcp"
  source_security_group_id = each.value
  security_group_id        = aws_security_group.redis.id
}

#######################
# Replication Group (Cluster Mode)
#######################

resource "aws_elasticache_replication_group" "cluster_mode" {
  count = var.cluster_mode_enabled ? 1 : 0

  replication_group_id = local.cluster_id
  description          = "Redis cluster mode for ${local.cluster_id}"

  engine               = "redis"
  engine_version       = var.engine_version
  port                 = var.port
  parameter_group_name = aws_elasticache_parameter_group.main.name
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = concat([aws_security_group.redis.id], var.additional_security_group_ids)

  # Node configuration
  node_type            = var.node_type
  num_node_groups      = var.num_node_groups
  replicas_per_node_group = var.replicas_per_node_group

  # Multi-AZ and automatic failover
  multi_az_enabled           = var.multi_az_enabled
  automatic_failover_enabled = var.automatic_failover_enabled

  # Encryption
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token                 = var.transit_encryption_enabled ? (var.auth_token != "" ? var.auth_token : random_password.auth_token[0].result) : null
  auth_token_update_strategy = var.transit_encryption_enabled ? "ROTATE" : null
  kms_key_id                 = var.at_rest_encryption_enabled ? (var.kms_key_id != null ? var.kms_key_id : aws_kms_key.redis[0].arn) : null

  # Maintenance
  maintenance_window       = var.maintenance_window
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  apply_immediately        = var.apply_immediately

  # Backup
  snapshot_retention_limit = var.enable_snapshot ? var.snapshot_retention_limit : 0
  snapshot_window          = var.enable_snapshot ? var.snapshot_window : null
  final_snapshot_identifier = var.enable_final_snapshot ? "${local.cluster_id}-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Notifications
  notification_topic_arn = var.notification_topic_arn

  # Logging
  dynamic "log_delivery_configuration" {
    for_each = var.enable_slow_log ? [1] : []
    content {
      destination      = aws_cloudwatch_log_group.slow_log[0].name
      destination_type = "cloudwatch-logs"
      log_format       = "json"
      log_type         = "slow-log"
    }
  }

  dynamic "log_delivery_configuration" {
    for_each = var.enable_engine_log ? [1] : []
    content {
      destination      = aws_cloudwatch_log_group.engine_log[0].name
      destination_type = "cloudwatch-logs"
      log_format       = "json"
      log_type         = "engine-log"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = local.cluster_id
    }
  )

  lifecycle {
    ignore_changes = [
      final_snapshot_identifier,
      auth_token, # Prevent recreation on token rotation
    ]
  }
}

#######################
# Replication Group (Non-Cluster Mode)
#######################

resource "aws_elasticache_replication_group" "standard" {
  count = var.cluster_mode_enabled ? 0 : 1

  replication_group_id = local.cluster_id
  description          = "Redis replication group for ${local.cluster_id}"

  engine               = "redis"
  engine_version       = var.engine_version
  port                 = var.port
  parameter_group_name = aws_elasticache_parameter_group.main.name
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = concat([aws_security_group.redis.id], var.additional_security_group_ids)

  # Node configuration (non-cluster mode uses num_cache_clusters)
  node_type         = var.node_type
  num_cache_clusters = var.num_cache_clusters

  # Multi-AZ and automatic failover
  multi_az_enabled           = var.multi_az_enabled
  automatic_failover_enabled = var.automatic_failover_enabled

  # Encryption
  at_rest_encryption_enabled = var.at_rest_encryption_enabled
  transit_encryption_enabled = var.transit_encryption_enabled
  auth_token                 = var.transit_encryption_enabled ? (var.auth_token != "" ? var.auth_token : random_password.auth_token[0].result) : null
  auth_token_update_strategy = var.transit_encryption_enabled ? "ROTATE" : null
  kms_key_id                 = var.at_rest_encryption_enabled ? (var.kms_key_id != null ? var.kms_key_id : aws_kms_key.redis[0].arn) : null

  # Maintenance
  maintenance_window       = var.maintenance_window
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  apply_immediately        = var.apply_immediately

  # Backup
  snapshot_retention_limit = var.enable_snapshot ? var.snapshot_retention_limit : 0
  snapshot_window          = var.enable_snapshot ? var.snapshot_window : null
  final_snapshot_identifier = var.enable_final_snapshot ? "${local.cluster_id}-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}" : null

  # Notifications
  notification_topic_arn = var.notification_topic_arn

  # Logging
  dynamic "log_delivery_configuration" {
    for_each = var.enable_slow_log ? [1] : []
    content {
      destination      = aws_cloudwatch_log_group.slow_log[0].name
      destination_type = "cloudwatch-logs"
      log_format       = "json"
      log_type         = "slow-log"
    }
  }

  dynamic "log_delivery_configuration" {
    for_each = var.enable_engine_log ? [1] : []
    content {
      destination      = aws_cloudwatch_log_group.engine_log[0].name
      destination_type = "cloudwatch-logs"
      log_format       = "json"
      log_type         = "engine-log"
    }
  }

  tags = merge(
    local.common_tags,
    {
      Name = local.cluster_id
    }
  )

  lifecycle {
    ignore_changes = [
      final_snapshot_identifier,
      auth_token,
    ]
  }
}

#######################
# KMS Key
#######################

resource "aws_kms_key" "redis" {
  count = var.at_rest_encryption_enabled && var.kms_key_id == null ? 1 : 0

  description             = "ElastiCache encryption key for ${local.cluster_id}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.cluster_id}-kms"
    }
  )
}

resource "aws_kms_alias" "redis" {
  count = var.at_rest_encryption_enabled && var.kms_key_id == null ? 1 : 0

  name          = "alias/${local.cluster_id}-redis"
  target_key_id = aws_kms_key.redis[0].key_id
}

#######################
# Auth Token
#######################

resource "random_password" "auth_token" {
  count = var.transit_encryption_enabled && var.auth_token == "" ? 1 : 0

  length  = 32
  special = true
  # Redis auth token restrictions
  override_special = "!&#$^<>-"
}

#######################
# CloudWatch Log Groups
#######################

resource "aws_cloudwatch_log_group" "slow_log" {
  count = var.enable_slow_log ? 1 : 0

  name              = "/aws/elasticache/${local.cluster_id}/slow-log"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.cloudwatch_log_kms_key_id

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "engine_log" {
  count = var.enable_engine_log ? 1 : 0

  name              = "/aws/elasticache/${local.cluster_id}/engine-log"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.cloudwatch_log_kms_key_id

  tags = local.common_tags
}

#######################
# CloudWatch Alarms
#######################

resource "aws_cloudwatch_metric_alarm" "cpu" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.cluster_id}-high-cpu"
  alarm_description   = "Redis CPU utilization is too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_cpu_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    CacheClusterId = local.cluster_id
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "memory" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.cluster_id}-high-memory"
  alarm_description   = "Redis memory utilization is too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_memory_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    CacheClusterId = local.cluster_id
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "evictions" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.cluster_id}-evictions"
  alarm_description   = "Redis is evicting keys due to memory pressure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alarm_evictions_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    CacheClusterId = local.cluster_id
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "replication_lag" {
  count = var.create_cloudwatch_alarms && (var.automatic_failover_enabled || var.replicas_per_node_group > 0) ? 1 : 0

  alarm_name          = "${local.cluster_id}-replication-lag"
  alarm_description   = "Redis replication lag is too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReplicationLag"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_replication_lag_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    CacheClusterId = local.cluster_id
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = local.common_tags
}
