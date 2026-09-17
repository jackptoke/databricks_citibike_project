# One catalog per environment, all in the same workspace, on the serverless
# workspace's default storage and bound to this workspace only (so the other
# workspaces sharing the regional metastore can't see them). Created via SQL —
# see scripts/create_catalog.sh for why this isn't a databricks_catalog.
#
# Destroying this resource does NOT drop the catalog, so `terraform destroy`
# can't take the data with it; drop catalogs by hand if you really mean to.
resource "terraform_data" "catalog" {
  for_each = local.environments

  input = "${var.catalog_prefix}_${each.key}"

  provisioner "local-exec" {
    command = "${path.module}/scripts/create_catalog.sh"
    environment = {
      DATABRICKS_HOST      = data.terraform_remote_state.azure.outputs.workspace_url
      DATABRICKS_AUTH_TYPE = "azure-cli"
      WAREHOUSE_ID         = databricks_sql_endpoint.dashboard.id
      WORKSPACE_ID         = data.terraform_remote_state.azure.outputs.workspace_id
      CATALOG              = "${var.catalog_prefix}_${each.key}"
    }
  }
}

resource "databricks_schema" "layer" {
  for_each = local.catalog_schemas

  catalog_name = terraform_data.catalog[each.value.env].output
  name         = each.value.schema
}

resource "databricks_volume" "managed" {
  for_each = local.catalog_volumes

  catalog_name = terraform_data.catalog[each.value.env].output
  schema_name  = databricks_schema.layer["${each.value.env}/${each.value.schema}"].name
  name         = each.value.name
  volume_type  = "MANAGED"
}

# Each environment's CI/CD service principal fully manages only its own catalog.
resource "databricks_grants" "catalog" {
  for_each = local.environments

  catalog = terraform_data.catalog[each.key].output

  grant {
    principal  = databricks_service_principal.deployer[each.key].application_id
    privileges = ["ALL_PRIVILEGES"]
  }

  dynamic "grant" {
    for_each = each.key == var.dashboard_environment ? [1] : []
    content {
      principal  = databricks_service_principal.dashboard.application_id
      privileges = ["USE_CATALOG"]
    }
  }
}

# The dashboard only reads the silver and gold layers of its environment.
resource "databricks_grants" "dashboard_schema" {
  for_each = toset(["02_silver", "03_gold"])

  schema = "${terraform_data.catalog[var.dashboard_environment].output}.${databricks_schema.layer["${var.dashboard_environment}/${each.key}"].name}"

  grant {
    principal  = databricks_service_principal.dashboard.application_id
    privileges = ["USE_SCHEMA", "SELECT"]
  }
}
