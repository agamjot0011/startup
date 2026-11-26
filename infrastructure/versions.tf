terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  # ---------------------------------------------------------------------------
  # TODO(HUMAN - Platform/DevOps): enable remote state BEFORE any shared apply.
  # Required by G1 exit evidence ("reviewed infrastructure plan and separated
  # accounts"). Create a state account in the separated management subscription,
  # enable versioning, soft-delete and encryption at rest, restrict network
  # access, and use AAD/OIDC authentication. Never commit state or credentials.
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-wzdm-tfstate"
  #   storage_account_name = "stgzdmtfstate00000"
  #   container_name       = "tfstate"
  #   key                  = "wzdm/dev/terraform.tfstate"
  #   use_azuread_auth     = true
  # }
  # ---------------------------------------------------------------------------
}

# No credentials or subscription IDs in source: authenticate at runtime with
# ARM_SUBSCRIPTION_ID and an OIDC-federated CI principal (human-owned setup).
provider "azurerm" {
  features {}
}
