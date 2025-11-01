output "db_instance_id" {
  description = "RDS instance ID"
  value       = aws_db_instance.main.id
}

output "db_instance_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.main.arn
}

output "db_instance_endpoint" {
  description = "RDS instance connection endpoint"
  value       = aws_db_instance.main.endpoint
}

output "db_instance_address" {
  description = "RDS instance hostname"
  value       = aws_db_instance.main.address
}

output "db_instance_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "db_instance_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "db_instance_username" {
  description = "Master username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_instance_password" {
  description = "Master password (generated if not provided)"
  value       = var.master_password != "" ? var.master_password : random_password.master.result
  sensitive   = true
}

output "db_instance_engine_version" {
  description = "Running engine version"
  value       = aws_db_instance.main.engine_version_actual
}

output "db_instance_resource_id" {
  description = "RDS resource ID"
  value       = aws_db_instance.main.resource_id
}

output "db_instance_status" {
  description = "RDS instance status"
  value       = aws_db_instance.main.status
}

output "db_subnet_group_id" {
  description = "DB subnet group ID"
  value       = aws_db_subnet_group.main.id
}

output "db_subnet_group_arn" {
  description = "DB subnet group ARN"
  value       = aws_db_subnet_group.main.arn
}

output "db_parameter_group_id" {
  description = "DB parameter group ID"
  value       = aws_db_parameter_group.main.id
}

output "db_parameter_group_arn" {
  description = "DB parameter group ARN"
  value       = aws_db_parameter_group.main.arn
}

output "db_option_group_id" {
  description = "DB option group ID"
  value       = aws_db_option_group.main.id
}

output "db_option_group_arn" {
  description = "DB option group ARN"
  value       = aws_db_option_group.main.arn
}

output "security_group_id" {
  description = "Security group ID for RDS instance"
  value       = aws_security_group.rds.id
}

output "security_group_arn" {
  description = "Security group ARN for RDS instance"
  value       = aws_security_group.rds.arn
}

output "kms_key_id" {
  description = "KMS key ID used for encryption"
  value       = var.kms_key_id != null ? var.kms_key_id : try(aws_kms_key.rds[0].id, "")
}

output "kms_key_arn" {
  description = "KMS key ARN used for encryption"
  value       = var.kms_key_id != null ? var.kms_key_id : try(aws_kms_key.rds[0].arn, "")
}

output "monitoring_role_arn" {
  description = "Enhanced monitoring IAM role ARN"
  value       = try(aws_iam_role.rds_monitoring[0].arn, "")
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    for log_type, log_group in aws_cloudwatch_log_group.postgresql :
    log_type => log_group.name
  }
}

# Connection strings
output "connection_string" {
  description = "PostgreSQL connection string (without password)"
  value       = "postgresql://${aws_db_instance.main.username}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

output "jdbc_connection_string" {
  description = "JDBC connection string"
  value       = "jdbc:postgresql://${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
}

# Kubernetes secret data
output "kubernetes_secret_data" {
  description = "Data for Kubernetes secret (base64 encoded)"
  value = {
    host     = base64encode(aws_db_instance.main.address)
    port     = base64encode(tostring(aws_db_instance.main.port))
    database = base64encode(aws_db_instance.main.db_name)
    username = base64encode(aws_db_instance.main.username)
    password = base64encode(var.master_password != "" ? var.master_password : random_password.master.result)
  }
  sensitive = true
}

# Alarm ARNs
output "cloudwatch_alarm_arns" {
  description = "CloudWatch alarm ARNs"
  value = {
    cpu_alarm         = try(aws_cloudwatch_metric_alarm.database_cpu[0].arn, "")
    memory_alarm      = try(aws_cloudwatch_metric_alarm.database_memory[0].arn, "")
    storage_alarm     = try(aws_cloudwatch_metric_alarm.database_storage[0].arn, "")
    connections_alarm = try(aws_cloudwatch_metric_alarm.database_connections[0].arn, "")
  }
}
