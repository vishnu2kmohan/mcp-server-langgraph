# ============================================================================
# AWS Secrets Manager - Application Secrets Module
# ============================================================================

locals {
  secrets = {
    "${var.environment}-anthropic-api-key"    = { description = "Anthropic API key for Claude LLM" }
    "${var.environment}-google-api-key"       = { description = "Google AI API key" }
    "${var.environment}-jwt-secret"           = { description = "JWT signing secret" }
    "${var.environment}-postgres-username"    = { description = "PostgreSQL username" }
    "${var.environment}-keycloak-db-password" = { description = "Keycloak database password" }
    "${var.environment}-openfga-db-password"  = { description = "OpenFGA database password" }
    "${var.environment}-gdpr-db-password"     = { description = "GDPR database password" }
    "${var.environment}-redis-host"           = { description = "Redis host address" }
    "${var.environment}-redis-password"       = { description = "Redis password" }
  }
}

resource "aws_secretsmanager_secret" "secrets" {
  for_each = local.secrets

  name        = each.key
  description = each.value.description

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

# IAM policy for External Secrets Operator (IRSA)
resource "aws_iam_policy" "external_secrets" {
  name        = "${var.environment}-mcp-external-secrets-policy"
  description = "Allow External Secrets Operator to read secrets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [for s in aws_secretsmanager_secret.secrets : s.arn]
      }
    ]
  })
}

resource "aws_iam_role" "external_secrets" {
  count = var.create_irsa_role ? 1 : 0

  name = "${var.environment}-mcp-external-secrets-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = var.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${replace(var.oidc_provider_arn, "/^(.*provider/)/", "")}:sub" = "system:serviceaccount:${var.kubernetes_namespace}:external-secrets-operator"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "external_secrets" {
  count = var.create_irsa_role ? 1 : 0

  role       = aws_iam_role.external_secrets[0].name
  policy_arn = aws_iam_policy.external_secrets.arn
}
