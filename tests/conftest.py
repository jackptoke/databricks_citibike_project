"""Pytest configuration and shared fixtures.

Two tiers of tests live in this project:

* **unit** (``tests/unit/``) — pure Python, no Spark or network. These run
  anywhere, including CI, and are the default.
* **integration** (``tests/integration/``) — exercise real Spark transforms via
  Databricks Connect against a live workspace. They are marked ``integration``
  and are automatically skipped when no Databricks compute is configured, so a
  plain ``pytest`` run stays green on a laptop or in CI.
"""

import csv
import json
import os
import pathlib
import sys
from contextlib import contextmanager

import pytest


def _databricks_available() -> bool:
    """True only when a Databricks Connect session can plausibly be created."""
    try:
        from databricks.sdk import WorkspaceClient

        conf = WorkspaceClient().config
        return bool(conf.serverless_compute_id or conf.cluster_id or os.environ.get("SPARK_REMOTE"))
    except Exception:
        return False


@pytest.fixture()
def spark():
    """Provide a Databricks Connect SparkSession (integration tests only)."""
    from databricks.connect import DatabricksSession

    return DatabricksSession.builder.getOrCreate()


@pytest.fixture()
def load_fixture(spark):
    """Load a JSON or CSV file from ``fixtures/`` into a Spark DataFrame."""

    def _loader(filename: str):
        path = pathlib.Path(__file__).parent.parent / "fixtures" / filename
        suffix = path.suffix.lower()
        if suffix == ".json":
            rows = json.loads(path.read_text())
            return spark.createDataFrame(rows)
        if suffix == ".csv":
            with path.open(newline="") as f:
                rows = list(csv.DictReader(f))
            return spark.createDataFrame(rows)
        raise ValueError(f"Unsupported fixture type for: {filename}")

    return _loader


@contextmanager
def _allow_stderr_output(config: pytest.Config):
    capman = config.pluginmanager.get_plugin("capturemanager")
    if capman:
        with capman.global_and_fixture_disabled():
            yield
    else:
        yield


def pytest_configure(config: pytest.Config):
    """Register markers and eagerly warm up Databricks Connect when available."""
    config.addinivalue_line("markers", "integration: requires a live Databricks workspace (Spark)")

    if not _databricks_available():
        return

    with _allow_stderr_output(config):
        try:
            from databricks.connect import DatabricksSession

            if hasattr(DatabricksSession.builder, "validateSession"):
                DatabricksSession.builder.validateSession().getOrCreate()
            else:
                DatabricksSession.builder.getOrCreate()
        except Exception as exc:  # pragma: no cover - environment dependent
            print(f"⚠️ Databricks Connect unavailable, integration tests will skip: {exc}", file=sys.stderr)


def pytest_collection_modifyitems(config: pytest.Config, items):
    """Skip integration-marked tests when no Databricks compute is configured."""
    if _databricks_available():
        return
    skip = pytest.mark.skip(reason="no Databricks workspace configured (set DATABRICKS_* or SPARK_REMOTE)")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
