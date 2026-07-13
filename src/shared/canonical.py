"""Column canonicalization for Citibike source files.

Citibike has published trip data under several different column-naming
conventions over the years (Title Case with spaces, lowercase no-space legacy
names, and the modern snake_case schema). This module maps any known variant
onto a single canonical schema. The logic is intentionally pure Python — no
Spark — so the mapping rules can be unit-tested in isolation. The bronze
notebook applies these decisions with `coalesce`/`select`.
"""

# Canonical name (value) keyed by every known source variant (key).
# Modern snake_case names map to themselves and can be omitted — callers should
# fall through to the original name when a column is not found here.
RENAME: dict[str, str] = {
    "Start Time": "started_at",
    "starttime": "started_at",
    "Start Station ID": "start_station_id",
    "start station id": "start_station_id",
    "Start Station Name": "start_station_name",
    "start station name": "start_station_name",
    "Stop Time": "ended_at",
    "stoptime": "ended_at",
    "End Station ID": "end_station_id",
    "end station id": "end_station_id",
    "End Station Name": "end_station_name",
    "end station name": "end_station_name",
    "Start Station Latitude": "start_lat",
    "start station latitude": "start_lat",
    "Start Station Longitude": "start_lng",
    "start station longitude": "start_lng",
    "End Station Latitude": "end_lat",
    "end station latitude": "end_lat",
    "End Station Longitude": "end_lng",
    "end station longitude": "end_lng",
    "User Type": "member_casual",
    "usertype": "member_casual",
    "Birth Year": "birth_year",
    "birth year": "birth_year",
    "Gender": "gender",
    "gender": "gender",
    "Trip Duration": "trip_duration",
    "tripduration": "trip_duration",
    "Bike ID": "bike_id",
    "bikeid": "bike_id",
}

# Columns the bronze table must always expose, with their Spark type, even when
# the source file does not provide them (older/newer schema variants differ).
EXPECTED_NULLABLE: dict[str, str] = {
    "birth_year": "string",
    "gender": "string",
    "bike_id": "string",
    "trip_duration": "string",
    "rideable_type": "string",
}


def canonical_name(column: str) -> str:
    """Map a single source column name to its canonical name (identity if unknown)."""
    return RENAME.get(column, column)


def resolve_column_groups(columns: list[str]) -> dict[str, list[str]]:
    """Group source columns by the canonical name they map to.

    A canonical name may be produced by more than one source column across a
    mixed batch of files (e.g. both ``starttime`` and ``Start Time``); the
    caller coalesces those sources. Order of first appearance is preserved.
    """
    groups: dict[str, list[str]] = {}
    for c in columns:
        groups.setdefault(canonical_name(c), []).append(c)
    return groups


def missing_columns(existing: list[str]) -> dict[str, str]:
    """Return the expected-but-absent columns (name -> Spark type) to add as nulls."""
    return {c: t for c, t in EXPECTED_NULLABLE.items() if c not in existing}
