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

data "databricks_current_user" "me" {}

# test/prod are deployed by a person but run as their deployer SP (run_as in
# databricks.yml). Binding an SP to run_as requires servicePrincipal.user on it.
# The rule set is authoritative, so it also keeps the manager grant Databricks
# gave the SP's creator.
resource "databricks_access_control_rule_set" "deployer" {
  for_each = var.runner_sp_environments

  name = "accounts/${var.account_id}/servicePrincipals/${databricks_service_principal.deployer[each.key].application_id}/ruleSets/default"

  grant_rules {
    principals = ["users/${data.databricks_current_user.me.user_name}"]
    role       = "roles/servicePrincipal.manager"
  }

  grant_rules {
    principals = ["users/${data.databricks_current_user.me.user_name}"]
    role       = "roles/servicePrincipal.user"
  }
}
