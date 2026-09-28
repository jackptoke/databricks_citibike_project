variable "catalog_prefix" {
  description = "Catalogs are named <prefix>_<env>; must match the notebooks."
  type        = string
  default     = "citibike"
}

variable "dashboard_environment" {
  description = "Environment whose catalog the Railway dashboard reads."
  type        = string
  default     = "prod"

  validation {
    condition     = contains(["dev", "test", "prod"], var.dashboard_environment)
    error_message = "dashboard_environment must be dev, test or prod."
  }
}

variable "account_id" {
  description = "Databricks account ID (account console → user menu). Needed for service-principal rule sets; set it in the git-ignored terraform.tfvars."
  type        = string
}

variable "runner_sp_environments" {
  description = "Environments whose jobs run as their deployer service principal (bundle run_as), so whoever applies Terraform can deploy them."
  type        = set(string)
  default     = ["test", "prod"]
}
