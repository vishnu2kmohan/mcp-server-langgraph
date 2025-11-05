output "secret_arns" {
  description = "Map of secret names to ARNs"
  value = {
    for k, v in aws_secretsmanager_secret.secrets : k => v.arn
  }
}

output "external_secrets_role_arn" {
  description = "IAM role ARN for External Secrets Operator"
  value       = var.create_irsa_role ? aws_iam_role.external_secrets[0].arn : ""
}

output "external_secrets_policy_arn" {
  description = "IAM policy ARN for External Secrets access"
  value       = aws_iam_policy.external_secrets.arn
}
