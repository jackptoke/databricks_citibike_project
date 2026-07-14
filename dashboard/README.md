# Citibike Executive Snapshot — Streamlit dashboard

A single-page, executive-facing view of the Citibike business, built on the
medallion pipeline's **silver** and **gold** Unity Catalog tables. It connects
directly to a **Databricks SQL Warehouse** (no BI subscription needed) using an
OAuth service principal, and is packaged to deploy on **Railway** (or any
container host).

## What it shows

- **KPIs** — total trips, avg trips/day, member share, e-bike share, avg duration
  (each with a delta vs the prior equal-length period)
- **Ridership over time** — monthly trips, member vs casual
- **Demand patterns** — trips by hour of day and day of week (commuter signal)
- **Mix trends** — membership share and e-bike adoption over time
- **Network** — busiest start stations and a demand map
- **Executive takeaways** — auto-generated recommendations backed by real numbers

> Trip volume is used as the demand/revenue proxy — the public dataset contains
> no revenue or user-level data.

## Configuration

Set these (see [`.env.example`](.env.example)) — locally in a `.env`, or as
Railway variables:

| Variable | Where to find it |
|---|---|
| `DATABRICKS_SERVER_HOSTNAME` | SQL Warehouse → **Connection details** |
| `DATABRICKS_HTTP_PATH` | SQL Warehouse → **Connection details** |
| `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET` | Read-only OAuth service principal |
| `DATABRICKS_CATALOG` | `citibike_ext_dev` (default), or test/prod |

The service principal needs `USE CATALOG` / `USE SCHEMA` + `SELECT` on the
`02_silver` and `03_gold` tables, and `CAN_USE` on the SQL Warehouse.

## Run locally

This is a self-contained [uv](https://docs.astral.sh/uv/) project (its own
`pyproject.toml` + `uv.lock`), isolated from the pipeline package at the repo
root.

```bash
cd dashboard
uv sync                    # creates dashboard/.venv from the lockfile
cp .env.example .env       # fill in your values
uv run streamlit run app.py
```

`dashboard/.env` is loaded automatically (via `python-dotenv`), so no `export`
or `source` step is needed. Use `KEY=value` with no spaces around `=`.

Or with Docker (matches the Railway build):

```bash
docker build -t citibike-dashboard .
docker run --rm -p 8080:8080 --env-file .env citibike-dashboard
# open http://localhost:8080
```

## Deploy on Railway

1. **New Project → Deploy from GitHub repo**, pick this repo.
2. Set the service **Root Directory** to `dashboard/` (so Railway builds the
   `Dockerfile` here).
3. Add the `DATABRICKS_*` variables from the table above under **Variables**.
4. Deploy. Railway injects `PORT`; the container binds to it automatically.

A **serverless SQL Warehouse with a short auto-stop** keeps cost minimal — with
the dashboard's 1-hour query cache it only wakes a few times a day.
