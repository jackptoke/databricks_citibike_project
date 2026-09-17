variable "location" {
  description = "Azure region for the resource group and workspace."
  type        = string
  default     = "australiaeast"
}

variable "resource_group_name" {
  description = "Resource group holding the workspace."
  type        = string
  default     = "citibike-rg"
}

variable "workspace_name" {
  description = "Azure Databricks workspace name."
  type        = string
  default     = "citibike-workspace"
}

variable "enable_delete_lock" {
  description = "Put a CanNotDelete lock on the resource group."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to every Azure resource."
  type        = map(string)
  default = {
    project    = "citibike-lakehouse"
    managed_by = "terraform"
  }
}
