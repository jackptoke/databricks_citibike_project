output "workspace_url" {
  value = data.terraform_remote_state.azure.outputs.workspace_url
}

output "deployer_client_ids" {
  description = "OAuth client id per environment (GitHub Environment secret DATABRICKS_CLIENT_ID)."
  value       = { for env, sp in databricks_service_principal.deployer : env => sp.application_id }
}

output "deployer_client_secrets" {
  description = "OAuth secret per environment (GitHub Environment secret DATABRICKS_CLIENT_SECRET)."
  value       = { for env, s in databricks_service_principal_secret.deployer : env => s.secret }
  sensitive   = true
}

output "dashboard_env" {
  description = "Railway variables for the dashboard service."
  value = {
    DATABRICKS_SERVER_HOSTNAME = trimprefix(data.terraform_remote_state.azure.outputs.workspace_url, "https://")
    DATABRICKS_HTTP_PATH       = databricks_sql_endpoint.dashboard.odbc_params[0].path
    DATABRICKS_CLIENT_ID       = databricks_service_principal.dashboard.application_id
    DATABRICKS_CATALOG         = terraform_data.catalog[var.dashboard_environment].output
  }
}

output "dashboard_client_secret" {
  description = "Railway variable DATABRICKS_CLIENT_SECRET."
  value       = databricks_service_principal_secret.dashboard.secret
  sensitive   = true
}
