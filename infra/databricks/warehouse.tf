# Smallest serverless SQL warehouse, stopping quickly when idle. With the
# dashboard's 1-hour query cache it only wakes a few times a day.
resource "databricks_sql_endpoint" "dashboard" {
  name                      = "citibike-dashboard"
  cluster_size              = "2X-Small"
  min_num_clusters          = 1
  max_num_clusters          = 1
  auto_stop_mins            = 5
  enable_serverless_compute = true
  warehouse_type            = "PRO"
}

resource "databricks_permissions" "dashboard_warehouse" {
  sql_endpoint_id = databricks_sql_endpoint.dashboard.id

  access_control {
    service_principal_name = databricks_service_principal.dashboard.application_id
    permission_level       = "CAN_USE"
  }
}
