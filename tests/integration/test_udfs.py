"""Integration tests for Spark transforms.

Marked ``integration`` — they run only when a Databricks workspace is configured
(via Databricks Connect) and are skipped otherwise. See ``tests/conftest.py``.
"""

import pytest

from shared.udfs import get_trip_duration_mins, timestamp_to_date_col

pytestmark = pytest.mark.integration


def test_trip_duration_mins_computes_minutes(spark):
    df = spark.createDataFrame(
        [("2025-09-01 10:00:00", "2025-09-01 10:30:00")],
        ["started_at", "ended_at"],
    ).selectExpr("CAST(started_at AS timestamp) AS started_at", "CAST(ended_at AS timestamp) AS ended_at")

    out = get_trip_duration_mins(spark, df, "started_at", "ended_at", "trip_duration_mins")
    assert out.collect()[0]["trip_duration_mins"] == pytest.approx(30.0)


def test_timestamp_to_date_col_extracts_date(spark):
    df = spark.createDataFrame([("2025-09-01 10:00:00",)], ["started_at"]).selectExpr(
        "CAST(started_at AS timestamp) AS started_at"
    )

    out = timestamp_to_date_col(spark, df, "started_at", "trip_start_date")
    assert str(out.collect()[0]["trip_start_date"]) == "2025-09-01"
