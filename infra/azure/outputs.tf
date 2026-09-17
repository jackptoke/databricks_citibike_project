output "workspace_resource_id" {
  description = "ARM resource id of the workspace (used by the databricks layer to authenticate)."
  value       = azapi_resource.workspace.id
}

output "workspace_url" {
  description = "Workspace URL, e.g. https://adb-xxxx.x.azuredatabricks.net"
  value       = "https://${azapi_resource.workspace.output.properties.workspaceUrl}"
}

output "workspace_id" {
  description = "Numeric Databricks workspace id."
  value       = azapi_resource.workspace.output.properties.workspaceId
}
