output "key_vault_id" {
  description = "Key Vault ID"
  value       = azurerm_key_vault.main.id
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.main.vault_uri
}

output "secret_ids" {
  description = "Map of secret names to IDs"
  value = {
    for k, v in azurerm_key_vault_secret.secrets : k => v.id
  }
}
