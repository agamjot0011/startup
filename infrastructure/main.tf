# --- Baseline resource group -------------------------------------------------
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# --- Synthetic artifact storage ----------------------------------------------
# Only synthetic build artifacts / SBOMs belong here. Never store PHI here.
resource "azurerm_storage_account" "artifacts" {
  name                            = var.storage_account_name
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  https_only                      = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = false

  # TODO(HUMAN - Security): review private endpoints / network ACLs and, for
  # regulated environments, customer-managed keys before any real deployment.
  blob_properties {
    versioning_enabled = true
  }

  tags = var.tags
}

resource "azurerm_storage_container" "artifacts" {
  name                  = "g1-artifacts"
  storage_account_name  = azurerm_storage_account.artifacts.name
  container_access_type = "private"
}

# --- Logging baseline (PHI-free telemetry only) ------------------------------
resource "azurerm_log_analytics_workspace" "main" {
  name                = var.log_analytics_workspace_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  # TODO(HUMAN - Security): confirm diagnostic settings and retention meet the
  # approved threat model. Do NOT log request bodies, patient identifiers or keys.
  tags = var.tags
}

# --- IAM-ish placeholder -----------------------------------------------------
# Least-privilege identity placeholder. The actual identity, federated
# credentials and SEPARATED accounts are human-owned; this only wires a role
# assignment when a principal ID is explicitly supplied.
resource "azurerm_user_assigned_identity" "ci" {
  name                = "id-wzdm-${var.environment}-ci"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  tags                = var.tags
}

resource "azurerm_role_assignment" "ci_blob_reader" {
  count                = var.ci_principal_id == "" ? 0 : 1
  scope                = azurerm_storage_account.artifacts.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = var.ci_principal_id
}
