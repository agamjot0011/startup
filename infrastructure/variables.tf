variable "environment" {
  description = "Deployment environment name (dev/stage/prod)."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for all resources in this environment."
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Name of the resource group that holds G1 baseline resources."
  type        = string
  default     = "rg-wzdm-dev"
}

variable "storage_account_name" {
  description = "Globally unique storage account name for synthetic artifacts. No real patient data."
  type        = string
  # No default: supply a unique value per environment in the tfvars file.
}

variable "log_analytics_workspace_name" {
  description = "Log Analytics workspace for PHI-free operational telemetry only."
  type        = string
  default     = "log-wzdm-dev"
}

variable "log_retention_days" {
  description = "Retention in days for PHI-free platform logs."
  type        = number
  default     = 30
}

variable "ci_principal_id" {
  description = "Object ID of a least-privilege CI identity in a SEPARATED account. Empty disables the role assignment placeholder."
  type        = string
  default     = ""
}

variable "tags" {
  description = "Common tags. Must not contain patient data or secrets."
  type        = map(string)
  default = {
    project     = "wzdm-liverecord"
    phase       = "g1"
    data_class  = "synthetic-no-phi"
    managed_by  = "terraform-skeleton"
  }
}
