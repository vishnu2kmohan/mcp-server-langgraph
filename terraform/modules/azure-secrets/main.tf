# ============================================================================
# Azure Key Vault - Application Secrets Module
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

resource "azurerm_key_vault" "main" {
  name                = "${var.environment}-mcp-kv"
  location            = var.location
  resource_group_name = var.resource_group_name
  tenant_id           = var.tenant_id
  sku_name            = var.sku_name

  enable_rbac_authorization = true
  purge_protection_enabled  = var.enable_purge_protection

  network_acls {
    bypass         = "AzureServices"
    default_action = var.network_default_action
  }

  tags = merge(
    var.tags,
    {
      environment = var.environment
      managed_by  = "terraform"
    }
  )
}

resource "azurerm_key_vault_secret" "secrets" {
  for_each = local.secrets

  name         = each.key
  value        = "PLACEHOLDER" # Set actual values separately
  key_vault_id = azurerm_key_vault.main.id

  tags = {
    description = each.value.description
  }
}

# Grant External Secrets Operator access via Managed Identity
resource "azurerm_role_assignment" "external_secrets" {
  count = var.external_secrets_principal_id != "" ? 1 : 0

  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = var.external_secrets_principal_id
}
