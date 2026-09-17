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
