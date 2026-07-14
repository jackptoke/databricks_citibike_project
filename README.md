# Citibike Lakehouse — Databricks Medallion Pipeline with CI/CD

An end-to-end **data engineering** project that ingests ~10 years of public
[Citibike](https://citibikenyc.com/system-data) trip data, refines it through a
**Bronze → Silver → Gold medallion architecture** on the Databricks Lakehouse,
and ships it with **Databricks Asset Bundles** and a **GitHub Actions CI/CD**
pipeline across `dev` / `test` / `prod` environments.

<p>
  <a href="https://github.com/jackptoke/databricks_citibike_project/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/jackptoke/databricks_citibike_project/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/jackptoke/databricks_citibike_project/actions/workflows/deploy.yml"><img alt="Deploy" src="https://github.com/jackptoke/databricks_citibike_project/actions/workflows/deploy.yml/badge.svg"></a>
  <img alt="Databricks" src="https://img.shields.io/badge/Databricks-Asset_Bundles-FF3621?logo=databricks&logoColor=white">
  <img alt="Spark" src="https://img.shields.io/badge/Apache_Spark-Structured_Streaming-E25A1C?logo=apachespark&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
</p>

---

## What this project demonstrates

| Capability | Where it lives |
|---|---|
| **Medallion architecture** (Landing → Bronze → Silver → Gold) | [`src/notebooks/`](src/notebooks/) |
| **Incremental streaming ingestion** with Auto Loader (`cloudFiles`) | [Bronze notebook](src/notebooks/01_bronze/01_bronze_citibike.ipynb) |
| **Change Data Feed (CDC)** + idempotent `MERGE` upserts | [Silver notebook](src/notebooks/02_silver/02_silver_citibike.ipynb) |
| **Correct incremental aggregates** via affected-partition recompute | [Gold notebook](src/notebooks/03_gold/03_gold_citibike.ipynb) |
| **Schema evolution** across a decade of changing source formats | [`src/shared/canonical.py`](src/shared/canonical.py) |
| **Infrastructure as code** with multi-env Asset Bundles | [`databricks.yml`](databricks.yml), [`resources/`](resources/) |
| **CI/CD**: lint, test, validate, and gated deploys | [`.github/workflows/`](.github/workflows/) |
| **Tested code**: fast unit tests + Spark integration tests | [`tests/`](tests/) |

---

## Architecture

```mermaid
flowchart LR
    subgraph src["Public source"]
        S3["Citibike trip archives<br/>(S3 .zip → CSV)"]
    end

    subgraph lake["Databricks Lakehouse · Unity Catalog"]
        direction LR
        L["<b>00 Landing</b><br/>UC Volume<br/>raw CSV"]
        B["<b>01 Bronze</b><br/>Auto Loader ingest<br/>canonical schema<br/>+ CDF enabled"]
        SI["<b>02 Silver</b><br/>typed, deduped,<br/>validated trips<br/>(CDF → MERGE)"]
        G["<b>03 Gold</b><br/>daily_ride_summary<br/>(incremental aggregates)"]
    end

    BI["Streamlit dashboard<br/>(exec snapshot)"]

    S3 -->|download notebook| L
    L -->|file-arrival trigger| B
    B -->|readChangeFeed| SI
    SI -->|readChangeFeed| G
    G --> BI

    classDef bronze fill:#cd7f32,stroke:#333,color:#fff;
    classDef silver fill:#9ca3af,stroke:#333,color:#fff;
    classDef gold fill:#d4af37,stroke:#333,color:#fff;
    class B bronze;
    class SI silver;
    class G gold;
```

The **Bronze → Silver → Gold** stages run as a single orchestrated job
([`01_medallion_pipeline_job.yml`](resources/01_medallion_pipeline_job.yml))
that is **triggered automatically when new files land** in the source Volume, so
the pipeline is event-driven rather than scheduled.

![Medallion pipeline runs in Databricks](docs/images/pipeline-runs.png)

> Live runs of the orchestrated job. Note the run **launched _by file arrival_**
> (not on a schedule), all three tasks succeeding, and Unity Catalog **lineage**
> tracking 2 upstream and 3 downstream tables.

### Layer responsibilities

| Layer | Table | Key logic |
|---|---|---|
| **Landing** | UC Volume | Probes known Citibike archive URL variants, downloads, extracts the single CSV per month. |
| **Bronze** | `*.01_bronze.citibike_trips` | Auto Loader stream; maps ~4 historical column-naming conventions onto one canonical schema; synthesises a deterministic `ride_id` (SHA-256 of the natural key) for legacy files that lack one; enables Change Data Feed. |
| **Silver** | `*.02_silver.citibike_trips` | Parses multiple timestamp formats, derives `trip_duration_mins` (nulls out impossible >24 h trips), normalises `member_casual`, filters invalid rows, and **upserts** via CDF `MERGE` keeping the latest change per `ride_id`. |
| **Gold** | `*.03_gold.daily_ride_summary` | For each batch, recomputes **only the affected days** in full from Silver → correct `min`/`max`/`avg`/`count` even under late-arriving data and deletes. |

The gold `daily_ride_summary` table — one row per day with trip counts and
min / max / avg ride duration:

![Gold daily_ride_summary sample](docs/images/gold-daily-ride-summary.png)

---

## Engineering highlights

- **Idempotent, deterministic IDs.** Early Citibike files predate `ride_id`, so
  the bronze layer hashes the trip's natural key (`started_at` + station ids +
  bike id + duration). Re-processing the same trip yields the same id, which
  keeps the downstream `MERGE` idempotent.
- **Correct incremental gold.** Naively summing CDF deltas breaks `min`/`max`
  and deletes. Instead the gold layer collects the *distinct affected days* in a
  micro-batch and **recomputes those days from live Silver**, so aggregates stay
  exact without a full rebuild.
- **Schema canonicalization is pure and tested.** The column-mapping rules live
  in [`src/shared/canonical.py`](src/shared/canonical.py) as plain Python so they
  can be unit-tested without a Spark cluster; the notebook applies them with
  `coalesce`/`select`.
- **Two-tier testing.** Fast **unit tests** run anywhere (incl. CI); **Spark
  integration tests** are marked and auto-skip when no workspace is configured.

---

## Project structure

```
.
├── databricks.yml                 # Bundle definition: dev / test / prod targets + variables
├── resources/
│   ├── 00_download_trips_data_job.yml     # Landing: download & extract source archives
│   └── 01_medallion_pipeline_job.yml      # Bronze → Silver → Gold (file-arrival triggered)
├── src/
│   ├── notebooks/                 # One notebook per medallion layer
│   │   ├── 00_landing/ 01_bronze/ 02_silver/ 03_gold/
│   └── shared/
│       ├── canonical.py           # Pure, unit-tested column-canonicalization rules
│       ├── utils.py               # Download/extract helpers (pure funcs + I/O wrapper)
│       └── udfs.py                # Reusable Spark column transforms
├── tests/
│   ├── unit/                      # No Spark/network — run in CI
│   └── integration/               # Databricks Connect (Spark) — auto-skipped in CI
├── fixtures/                      # Sample data for tests
└── .github/workflows/             # CI (validate/lint/test) + CD (deploy)
```

---

## CI/CD

Three GitHub Actions workflows implement a promote-through-environments flow:

- **`ci.yml`** — on every pull request / push: `ruff` lint + format check,
  `pytest` unit tests, and `databricks bundle validate` for each target.
- **`deploy.yml`** — on push to `main`, deploy to **dev**; **test** / **prod**
  deploy via manual dispatch, with `prod` gated behind a GitHub Environment
  approval.
- **`run-job.yml`** — manually dispatch a bundle job (`download_citibike_data_job`
  or `citibike_medallion_job`) in a chosen environment. Deploy only *creates* the
  job; this *runs* it — as that environment's service principal.

Each of `dev` / `test` / `prod` is a **separate Azure Databricks workspace**.
Environment-specific *config* (host, catalog, cluster, volume path) lives in the
[`databricks.yml`](databricks.yml) targets, while environment-specific
*credentials* live in **GitHub Environments** of the same name — each holding its
own workspace's OAuth service-principal `DATABRICKS_CLIENT_ID` /
`DATABRICKS_CLIENT_SECRET`. A job that declares `environment: <target>`
automatically picks up the right secrets (and `prod` can require a manual
approval). No personal tokens live in the repo. See
[`.github/workflows/`](.github/workflows/).

---

## Running it yourself

### Prerequisites
- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- The [Databricks CLI](https://docs.databricks.com/dev-tools/cli/) (`v0.2+`)
- A Databricks workspace with Unity Catalog (for actual deployment)

### Local development

```bash
uv sync --dev            # install dependencies

uv run ruff check .      # lint
uv run ruff format .     # format
uv run pytest            # unit tests (integration tests skip without a workspace)
uv run pytest -m integration   # run Spark tests against a configured workspace
```

### Deploy & run via the CLI

```bash
databricks bundle validate -t dev
databricks bundle deploy   -t dev                        # create/update job definitions
databricks bundle run download_citibike_data_job -t dev  # backfill the landing volume
databricks bundle run citibike_medallion_job     -t dev  # run bronze → silver → gold
```

`dev` deploys an isolated, user-prefixed copy with triggers paused; `test` /
`prod` deploy production-mode copies. Jobs run on **serverless compute**, so
there is no cluster to provision per environment — only each target's
workspace `host` and `source_volume_path` in
[`databricks.yml`](databricks.yml).

> **Deploy ≠ run.** `bundle deploy` only creates/updates the job *definitions*;
> `bundle run` (or the trigger, or the workflow below) actually *executes* them.

### Trigger through the CI/CD pipeline (recommended)

Deploys happen automatically, and jobs are launched from the **Actions** tab —
each running as the target environment's service principal, never a personal
token.

| Workflow | Trigger | What it does |
|---|---|---|
| **CI** | pull request / push | `ruff` lint + format, `pytest` unit tests, `bundle validate` |
| **Deploy** | push to `main` → `dev`; manual dispatch → `test` / `prod` | `bundle deploy` |
| **Run job** | manual dispatch | `bundle run` for a chosen job in a chosen environment |

**Run a job from the UI:** Actions → **Run job** → *Run workflow* → choose the
environment (`dev` / `test` / `prod`) and job
(`download_citibike_data_job` or `citibike_medallion_job`) → *Run workflow*.

**Run a job from the terminal** (still executes in CI, as the service principal):

```bash
gh workflow run "Run job" -f target=dev -f job=download_citibike_data_job
gh workflow run "Run job" -f target=dev -f job=citibike_medallion_job
```

The **Run job** workflow waits for the Databricks run to finish and fails if the
job fails, so pass/fail shows directly in the Actions run.

> The `download_citibike_data_job` backfills every month from **2016 to the
> present** into the landing volume — a large one-off download that then
> file-arrival-triggers the medallion pipeline.

#### One-time setup for CI/CD

1. Create GitHub **Environments** `dev` / `test` / `prod`; add each workspace's
   OAuth service-principal `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET`.
2. Set repo variables `DATABRICKS_CI_ENABLED=true` and `DEPLOY_ENABLED=true`.
3. Grant each service principal access in its workspace's Unity Catalog, e.g.
   ```bash
   databricks grants update catalog <catalog> \
     --json '{"changes":[{"principal":"<sp-application-id>","add":["ALL_PRIVILEGES"]}]}'
   ```
4. Optionally add required reviewers to the `prod` Environment for a deploy gate.

---

## Analytics dashboard

A **Streamlit executive dashboard** in [`dashboard/`](dashboard/) reads the
silver/gold tables directly from a **Databricks SQL Warehouse** (via an OAuth
service principal — no BI subscription) and presents a single-page business
snapshot: KPIs, ridership trends, member vs casual mix, commuter demand
patterns, e-bike adoption, busiest stations, and auto-generated executive
takeaways. It ships with a `Dockerfile` for one-click deployment to Railway.
See [`dashboard/README.md`](dashboard/README.md).

## Possible extensions

- Add data-quality expectations (Lakeflow Declarative Pipelines / DLT or
  Great Expectations) between layers.
- Add automated data-lineage / freshness monitoring and alerting.

---

## License

[MIT](LICENSE) · Built by Jack Toke as a data-engineering portfolio project.
Citibike data © Lyft, used under the
[Citibike Data License Agreement](https://citibikenyc.com/data-sharing-policy).
