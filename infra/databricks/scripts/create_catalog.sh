#!/usr/bin/env bash
# Creates a Unity Catalog catalog on the serverless workspace's default storage,
# then binds it to this workspace only. Idempotent — safe to re-run.
#
# The Unity Catalog REST API (and so the Terraform provider) refuses to create
# default-storage catalogs ("Please use the UI"), but SQL `CREATE CATALOG` with
# no location works in serverless workspaces, so run it on the SQL warehouse.
#
# Uses `databricks api` only: higher-level CLI commands pick up the workspace
# host from the repo's databricks.yml instead of DATABRICKS_HOST.
#
# Required env: DATABRICKS_HOST, DATABRICKS_AUTH_TYPE, WAREHOUSE_ID,
#               WORKSPACE_ID, CATALOG
set -euo pipefail

run_sql() {
  databricks api post /api/2.0/sql/statements --json "$(printf \
    '{"warehouse_id":"%s","statement":"%s","wait_timeout":"50s","on_wait_timeout":"CANCEL"}' \
    "$WAREHOUSE_ID" "$1")" |
    python3 -c 'import json,sys; s=json.load(sys.stdin)["status"]; sys.exit(0) if s["state"]=="SUCCEEDED" else sys.exit(f"SQL failed: {s}")'
}

run_sql "CREATE CATALOG IF NOT EXISTS \`${CATALOG}\` COMMENT 'Citibike medallion lakehouse'"

# Bind before isolating, otherwise the catalog becomes inaccessible from here.
databricks api patch "/api/2.1/unity-catalog/bindings/catalog/${CATALOG}" --json "$(printf \
  '{"add":[{"workspace_id":%s,"binding_type":"BINDING_TYPE_READ_WRITE"}]}' "$WORKSPACE_ID")" >/dev/null

databricks api patch "/api/2.1/unity-catalog/catalogs/${CATALOG}" \
  --json '{"isolation_mode":"ISOLATED"}' >/dev/null

echo "catalog ${CATALOG} ready (default storage, bound to workspace ${WORKSPACE_ID})"
