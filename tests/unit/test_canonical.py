"""Unit tests for the pure column-canonicalization logic (no Spark)."""

from shared.canonical import (
    canonical_name,
    missing_columns,
    resolve_column_groups,
)


def test_legacy_lowercase_names_map_to_canonical():
    assert canonical_name("starttime") == "started_at"
    assert canonical_name("stoptime") == "ended_at"
    assert canonical_name("bikeid") == "bike_id"


def test_title_case_names_map_to_canonical():
    assert canonical_name("Start Station Name") == "start_station_name"
    assert canonical_name("End Station Longitude") == "end_lng"


def test_unknown_column_is_identity():
    # Modern snake_case names are not in the map and fall through unchanged.
    assert canonical_name("ride_id") == "ride_id"
    assert canonical_name("rideable_type") == "rideable_type"


def test_resolve_groups_merges_variants_to_one_canonical():
    # A mixed batch where two source spellings both mean started_at.
    groups = resolve_column_groups(["starttime", "Start Time", "ride_id"])
    assert groups["started_at"] == ["starttime", "Start Time"]
    assert groups["ride_id"] == ["ride_id"]


def test_resolve_groups_preserves_first_appearance_order():
    groups = resolve_column_groups(["Bike ID", "bikeid"])
    assert list(groups.keys()) == ["bike_id"]
    assert groups["bike_id"] == ["Bike ID", "bikeid"]


def test_missing_columns_reports_absent_expected_columns():
    present = ["ride_id", "started_at", "rideable_type"]
    missing = missing_columns(present)
    assert "rideable_type" not in missing  # already present
    assert missing["bike_id"] == "string"
    assert missing["gender"] == "string"


def test_missing_columns_empty_when_all_present():
    present = ["birth_year", "gender", "bike_id", "trip_duration", "rideable_type"]
    assert missing_columns(present) == {}
