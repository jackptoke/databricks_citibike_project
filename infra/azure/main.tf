# Azure layer: the resource group and a Serverless Azure Databricks workspace.
#
# Serverless workspaces come with Databricks-managed default storage, so there is
# no storage account, access connector or managed resource group to provision.
# `azurerm_databricks_workspace` can't create a serverless workspace yet, so the
# workspace itself goes through `azapi`.

terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.5"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.12"
    }
  }
}

# Both providers authenticate through the Azure CLI (`az login`). The target
# subscription comes from ARM_SUBSCRIPTION_ID so it isn't committed to the repo.
provider "azurerm" {
  features {}
}

provider "azapi" {}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azapi_resource" "workspace" {
  type      = "Microsoft.Databricks/workspaces@2026-01-01"
  name      = var.workspace_name
  parent_id = azurerm_resource_group.this.id
  location  = var.location
  tags      = var.tags

  body = {
    sku = {
      name = "premium"
    }
    properties = {
      computeMode         = "Serverless"
      publicNetworkAccess = "Enabled"
    }
  }

  response_export_values = ["properties.workspaceUrl", "properties.workspaceId"]
}

# Guards against the accidental deletion that prompted this rebuild. Remove the
# lock first (or `terraform destroy -target` it) before tearing anything down.
resource "azurerm_management_lock" "resource_group" {
  count = var.enable_delete_lock ? 1 : 0

  name       = "${var.resource_group_name}-cannot-delete"
  scope      = azurerm_resource_group.this.id
  lock_level = "CanNotDelete"
  notes      = "Protects the Citibike Databricks workspace from accidental deletion."

  depends_on = [azapi_resource.workspace]
}
