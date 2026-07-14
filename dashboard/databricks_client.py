"""Thin Databricks SQL Warehouse client for the dashboard.

Connects via the Databricks SQL Connector using an OAuth machine-to-machine
service principal — the same auth style as the project's CI/CD, so no personal
access tokens are needed. Configuration comes entirely from environment
variables (see .env.example).
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from databricks import sql
from databricks.sdk.core import Config, oauth_service_principal
from dotenv import load_dotenv

# Load dashboard/.env for local development. On Railway (and any other host that
# injects the variables directly) the file is absent, so this is a no-op.
load_dotenv(Path(__file__).with_name(".env"))

# Unity Catalog location of the pipeline output. Catalog is configurable so the
# same dashboard can point at dev / test / prod; schema names are fixed by the
# medallion layout.
CATALOG = os.getenv("DATABRICKS_CATALOG", "citibike_ext_dev")
SILVER = f"`{CATALOG}`.`02_silver`.citibike_trips"
GOLD = f"`{CATALOG}`.`03_gold`.daily_ride_summary"


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable {name}. Set the DATABRICKS_* variables "
            "(see dashboard/.env.example) before starting the app."
        )
    return value


def _credentials():
    cfg = Config(
        host=f"https://{_required('DATABRICKS_SERVER_HOSTNAME')}",
        client_id=_required("DATABRICKS_CLIENT_ID"),
        client_secret=_required("DATABRICKS_CLIENT_SECRET"),
    )
    return oauth_service_principal(cfg)


def run_query(sql_text: str) -> pd.DataFrame:
    """Execute a read-only query on the SQL Warehouse and return a DataFrame."""
    with (
        sql.connect(
            server_hostname=_required("DATABRICKS_SERVER_HOSTNAME"),
            http_path=_required("DATABRICKS_HTTP_PATH"),
            credentials_provider=_credentials,
        ) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(sql_text)
        return cur.fetchall_arrow().to_pandas()
