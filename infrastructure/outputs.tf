output "resource_group_name" {
  description = "Resource group created for the G1 baseline."
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "Storage account for synthetic artifacts (no PHI)."
  value       = azurerm_storage_account.artifacts.name
}

output "artifacts_container_name" {
  description = "Private container name for build artifacts and SBOMs."
  value       = azurerm_storage_container.artifacts.name
}

output "log_analytics_workspace_id" {
  description = "Resource ID of the PHI-free logging workspace."
  value       = azurerm_log_analytics_workspace.main.id
}

output "ci_identity_principal_id" {
  description = "Principal ID of the placeholder CI managed identity."
  value       = azurerm_user_assigned_identity.ci.principal_id
}

output "human_owned_gates" {
  description = "G1 evidence that cannot be produced by this skeleton."
  value = [
    "signed ADRs",
    "reviewed threat model",
    "separated accounts and reviewed infrastructure plan",
  ]
}
