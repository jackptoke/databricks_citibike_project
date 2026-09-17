# Databricks layer: everything inside the workspace created by ../azure —
# Unity Catalog objects, CI/CD + dashboard service principals, and the SQL
# warehouse the dashboard queries. Apply ../azure first.

terraform {
  required_version = ">= 1.9"

  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.132"
    }
  }
}

data "terraform_remote_state" "azure" {
  backend = "local"
  config = {
    path = "${path.module}/../azure/terraform.tfstate"
  }
}

# Authenticates as the Azure CLI identity (`az login`), which must be a workspace
# admin (see ../README.md). Don't set azure_workspace_resource_id: that switches
# to ARM-based auth, which serverless workspaces reject.
provider "databricks" {
  host      = data.terraform_remote_state.azure.outputs.workspace_url
  auth_type = "azure-cli"
}

locals {
  environments = toset(["dev", "test", "prod"])

  # Schemas are fixed across environments; the notebooks address them by name.
  schemas = toset(["00_landing", "01_bronze", "02_silver", "03_gold"])

  # Managed volumes the notebooks read and write (landing files, Auto Loader
  # schema tracking, and streaming checkpoints), as schema => volume names.
  volumes = {
    "00_landing/source_data" = { schema = "00_landing", name = "source_data" }
    "01_bronze/_checkpoint"  = { schema = "01_bronze", name = "_checkpoint" }
    "01_bronze/_schema"      = { schema = "01_bronze", name = "_schema" }
    "02_silver/_checkpoint"  = { schema = "02_silver", name = "_checkpoint" }
    "03_gold/_checkpoint"    = { schema = "03_gold", name = "_checkpoint" }
  }

  catalog_schemas = {
    for pair in setproduct(local.environments, local.schemas) :
    "${pair[0]}/${pair[1]}" => { env = pair[0], schema = pair[1] }
  }

  catalog_volumes = {
    for pair in setproduct(local.environments, keys(local.volumes)) :
    "${pair[0]}/${pair[1]}" => merge(local.volumes[pair[1]], { env = pair[0] })
  }
}
