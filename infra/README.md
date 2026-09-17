# Infrastructure (Terraform)

Everything the pipeline and dashboard need, in two Terraform layers that are
applied in order:

| Layer | Creates |
|---|---|
| [`azure/`](azure/) | Resource group `citibike-rg` with a `CanNotDelete` lock, and a **serverless** Azure Databricks workspace `citibike-workspace` (australiaeast) |
| [`databricks/`](databricks/) | Catalogs `citibike_dev` / `citibike_test` / `citibike_prod` on default storage, bound to this workspace only · schemas `00_landing`–`03_gold` and the managed volumes the notebooks use · one CI/CD service principal per environment (`ALL_PRIVILEGES` on its own catalog only) · a read-only dashboard service principal · a serverless SQL warehouse |

Serverless workspaces come with Databricks-managed default storage, so there
are no storage accounts, access connectors or VNets to manage.

## Prerequisites

- Terraform ≥ 1.9, the Azure CLI and the Databricks CLI
- `az login` as a subscription Owner/Contributor who is also a Databricks
  **account admin**. Both layers authenticate through the Azure CLI.

## Apply

```bash
export ARM_SUBSCRIPTION_ID=$(az account show --query id -o tsv)

terraform -chdir=infra/azure init
terraform -chdir=infra/azure apply
```

Creating a serverless workspace doesn't necessarily make your `az login`
identity a workspace admin. If the next step fails with
`Unauthorized access to Org`, grant it in the account console (**Workspaces →
citibike-workspace → Permissions → Add → Admin**) or with the CLI:

```bash
databricks account workspace-assignment update <workspace-id> <user-principal-id> \
  --json '{"permissions":["ADMIN"]}' --profile <account-profile>
```

```bash
terraform -chdir=infra/databricks init
terraform -chdir=infra/databricks apply
```

Catalog names must be unique across the regional metastore, which this
workspace shares with others in the account. If a `citibike_*` catalog from an
earlier workspace still exists, drop it first.

## Wire up CI/CD and the dashboard

State files contain the service-principal secrets and are git-ignored. Pipe the
outputs straight into their destinations instead of copying them around:

```bash
out() { terraform -chdir=infra/databricks output -json "$1"; }

# GitHub Environments dev / test / prod
for env in dev test prod; do
  out deployer_client_ids     | jq -r ".$env" | gh secret set DATABRICKS_CLIENT_ID     --env "$env"
  out deployer_client_secrets | jq -r ".$env" | gh secret set DATABRICKS_CLIENT_SECRET --env "$env"
done

# Railway dashboard service (run where the service is linked: `railway link`)
railway variable set --skip-deploys $(out dashboard_env | jq -r 'to_entries[] | "\(.key)=\(.value)"')
out dashboard_client_secret | jq -r . | railway variable set DATABRICKS_CLIENT_SECRET --stdin
```

Secrets expire after two years; `terraform apply` rotates them once expired.
Re-run the commands above afterwards.

## Tearing down

The resource-group lock blocks deletion from both the portal and Terraform.
Remove it first (`enable_delete_lock = false`, then apply). The catalogs are
created through SQL (see
[`databricks/scripts/create_catalog.sh`](databricks/scripts/create_catalog.sh)),
so `terraform destroy` leaves them and their data in place; drop them by hand if
you really mean to.
