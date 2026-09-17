# Databricks-managed service principals with OAuth (M2M) secrets.
#   deployer[env] -> GitHub Environment <env>: DATABRICKS_CLIENT_ID / _SECRET
#   dashboard     -> Railway service variables

resource "databricks_service_principal" "deployer" {
  for_each = local.environments

  display_name     = "citibike-${each.key}-deployer"
  workspace_access = true
}

resource "databricks_service_principal_secret" "deployer" {
  for_each = local.environments

  service_principal_id = databricks_service_principal.deployer[each.key].id
}

resource "databricks_service_principal" "dashboard" {
  display_name          = "citibike-dashboard-reader"
  workspace_access      = true
  databricks_sql_access = true
}

resource "databricks_service_principal_secret" "dashboard" {
  service_principal_id = databricks_service_principal.dashboard.id
}
