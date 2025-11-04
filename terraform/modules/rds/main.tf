# RDS PostgreSQL Module
# Creates a Multi-AZ PostgreSQL database with automated backups, encryption, and monitoring

locals {
  db_identifier = var.db_identifier != "" ? var.db_identifier : "${var.name_prefix}-postgres"

  common_tags = merge(
    var.tags,
    {
      ManagedBy = "Terraform"
      Module    = "rds"
    }
  )
}

#######################
# DB Subnet Group
#######################

resource "aws_db_subnet_group" "main" {
  name_prefix = "${local.db_identifier}-"
  description = "Database subnet group for ${local.db_identifier}"
  subnet_ids  = var.subnet_ids

  tags = merge(
    local.common_tags,
    {
      Name = "${local.db_identifier}-subnet-group"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

#######################
# Parameter Group
#######################

resource "aws_db_parameter_group" "main" {
  name_prefix = "${local.db_identifier}-"
  family      = var.parameter_group_family
  description = "Custom parameter group for ${local.db_identifier}"

  # Performance and logging parameters
  dynamic "parameter" {
    for_each = var.db_parameters
    content {
      name         = parameter.value.name
      value        = parameter.value.value
      apply_method = lookup(parameter.value, "apply_method", "immediate")
    }
  }

  # Default parameters for better observability
  parameter {
    name  = "log_connections"
    value = var.enable_enhanced_monitoring ? "1" : "0"
  }

  parameter {
    name  = "log_disconnections"
    value = var.enable_enhanced_monitoring ? "1" : "0"
  }

  parameter {
    name  = "log_duration"
    value = var.enable_slow_query_log ? "1" : "0"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = var.slow_query_threshold_ms
  }

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.db_identifier}-params"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

#######################
# Option Group
#######################

resource "aws_db_option_group" "main" {
  name_prefix              = "${local.db_identifier}-"
  option_group_description = "Option group for ${local.db_identifier}"
  engine_name              = "postgres"
  major_engine_version     = split(".", var.engine_version)[0]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.db_identifier}-options"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

#######################
# KMS Key for Encryption
#######################

resource "aws_kms_key" "rds" {
  count = var.kms_key_id == null ? 1 : 0

  description             = "RDS encryption key for ${local.db_identifier}"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = merge(
    local.common_tags,
    {
      Name = "${local.db_identifier}-kms"
    }
  )
}

resource "aws_kms_alias" "rds" {
  count = var.kms_key_id == null ? 1 : 0

  name          = "alias/${local.db_identifier}-rds"
  target_key_id = aws_kms_key.rds[0].key_id
}

#######################
# RDS Instance
#######################

resource "aws_db_instance" "main" {
  identifier     = local.db_identifier
  engine         = "postgres"
  engine_version = var.engine_version

  # Instance configuration
  instance_class        = var.instance_class
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = var.storage_type
  iops                  = var.storage_type == "io1" || var.storage_type == "io2" ? var.iops : null
  storage_throughput    = var.storage_type == "gp3" ? var.storage_throughput : null
  storage_encrypted     = true
  kms_key_id            = var.kms_key_id != null ? var.kms_key_id : aws_kms_key.rds[0].arn

  # Database configuration
  db_name  = var.database_name
  username = var.master_username
  password = var.master_password != "" ? var.master_password : random_password.master.result
  port     = var.database_port

  # High availability
  multi_az               = var.multi_az
  availability_zone      = var.multi_az ? null : var.availability_zone
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = concat([aws_security_group.rds.id], var.additional_security_group_ids)

  # Parameter and option groups
  parameter_group_name = aws_db_parameter_group.main.name
  option_group_name    = aws_db_option_group.main.name

  # Backup configuration
  backup_retention_period   = var.backup_retention_period
  backup_window             = var.backup_window
  copy_tags_to_snapshot     = true
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.db_identifier}-final-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  delete_automated_backups  = var.delete_automated_backups

  # Maintenance
  maintenance_window              = var.maintenance_window
  auto_minor_version_upgrade      = var.auto_minor_version_upgrade
  allow_major_version_upgrade     = var.allow_major_version_upgrade
  apply_immediately               = var.apply_immediately
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports

  # Monitoring
  monitoring_interval                   = var.enable_enhanced_monitoring ? var.monitoring_interval : 0
  monitoring_role_arn                   = var.enable_enhanced_monitoring ? aws_iam_role.rds_monitoring[0].arn : null
  performance_insights_enabled          = var.enable_performance_insights
  performance_insights_kms_key_id       = var.enable_performance_insights ? (var.kms_key_id != null ? var.kms_key_id : aws_kms_key.rds[0].arn) : null
  performance_insights_retention_period = var.enable_performance_insights ? var.performance_insights_retention_period : null

  # Security
  publicly_accessible                 = var.publicly_accessible
  deletion_protection                 = var.deletion_protection
  iam_database_authentication_enabled = var.enable_iam_database_authentication

  tags = merge(
    local.common_tags,
    {
      Name = local.db_identifier
    }
  )

  lifecycle {
    ignore_changes = [
      password, # Don't update password through Terraform
      final_snapshot_identifier,
    ]
  }

  depends_on = [aws_cloudwatch_log_group.postgresql]
}

#######################
# Security Group
#######################

resource "aws_security_group" "rds" {
  name_prefix = "${local.db_identifier}-"
  description = "Security group for ${local.db_identifier} RDS instance"
  vpc_id      = var.vpc_id

  tags = merge(
    local.common_tags,
    {
      Name = "${local.db_identifier}-rds-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_security_group_rule" "rds_ingress_cidr" {
  count = length(var.allowed_cidr_blocks) > 0 ? 1 : 0

  type              = "ingress"
  description       = "PostgreSQL access from allowed CIDR blocks"
  from_port         = var.database_port
  to_port           = var.database_port
  protocol          = "tcp"
  cidr_blocks       = var.allowed_cidr_blocks
  security_group_id = aws_security_group.rds.id
}

resource "aws_security_group_rule" "rds_ingress_security_groups" {
  for_each = toset(var.allowed_security_group_ids)

  type                     = "ingress"
  description              = "PostgreSQL access from security group ${each.value}"
  from_port                = var.database_port
  to_port                  = var.database_port
  protocol                 = "tcp"
  source_security_group_id = each.value
  security_group_id        = aws_security_group.rds.id
}

# No egress rules needed for RDS (AWS manages this)

#######################
# Random Password
#######################

resource "random_password" "master" {
  length  = 32
  special = true
  # Exclude characters that might cause issues in connection strings
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

#######################
# CloudWatch Log Groups
#######################

resource "aws_cloudwatch_log_group" "postgresql" {
  for_each = toset(var.enabled_cloudwatch_logs_exports)

  name              = "/aws/rds/instance/${local.db_identifier}/${each.value}"
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = var.cloudwatch_log_kms_key_id

  tags = local.common_tags
}

#######################
# Enhanced Monitoring IAM Role
#######################

resource "aws_iam_role" "rds_monitoring" {
  count = var.enable_enhanced_monitoring ? 1 : 0

  name_prefix = "${local.db_identifier}-mon-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"]

  tags = merge(
    local.common_tags,
    {
      Name = "${local.db_identifier}-monitoring-role"
    }
  )
}

#######################
# CloudWatch Alarms
#######################

resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.db_identifier}-high-cpu"
  alarm_description   = "Database CPU utilization is too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_cpu_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "database_memory" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.db_identifier}-low-memory"
  alarm_description   = "Database freeable memory is too low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_memory_threshold_bytes
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "database_storage" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.db_identifier}-low-storage"
  alarm_description   = "Database free storage space is too low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_storage_threshold_bytes
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  count = var.create_cloudwatch_alarms ? 1 : 0

  alarm_name          = "${local.db_identifier}-high-connections"
  alarm_description   = "Database connection count is too high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = var.alarm_connections_threshold
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  alarm_actions = var.alarm_sns_topic_arns

  tags = local.common_tags
}
