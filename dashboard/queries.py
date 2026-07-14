"""Cached data-access functions for the dashboard.

Each function returns a small, pre-aggregated DataFrame so the SQL Warehouse
does the heavy lifting and only wakes occasionally (results are cached for an
hour). Dates coming from Streamlit widgets are `datetime.date` objects, so
formatting them straight into the SQL is safe from injection.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st
from databricks_client import GOLD, SILVER, run_query

_TTL = 3600  # seconds


@st.cache_data(ttl=_TTL, show_spinner=False)
def date_bounds() -> tuple[dt.date, dt.date]:
    """Earliest and latest trip date available in gold."""
    df = run_query(f"SELECT min(trip_start_date) lo, max(trip_start_date) hi FROM {GOLD}")
    # Normalise to plain date objects regardless of how Arrow types the column.
    return pd.to_datetime(df["lo"].iloc[0]).date(), pd.to_datetime(df["hi"].iloc[0]).date()


@st.cache_data(ttl=_TTL, show_spinner="Loading ridership…")
def daily_fact() -> pd.DataFrame:
    """All-time daily trips & avg duration by rider type and bike type.

    Small enough to filter in pandas for any date range, which powers the KPIs,
    trends and mix charts from a single query.
    """
    return run_query(f"""
        SELECT trip_start_date,
               member_casual,
               rideable_type,
               count(*)                    AS trips,
               avg(trip_duration_mins)     AS avg_dur
        FROM {SILVER}
        WHERE trip_start_date IS NOT NULL
        GROUP BY trip_start_date, member_casual, rideable_type
    """)


@st.cache_data(ttl=_TTL, show_spinner="Loading demand patterns…")
def hour_of_day(start: dt.date, end: dt.date) -> pd.DataFrame:
    return run_query(f"""
        SELECT hour(started_at) AS hr,
               member_casual,
               count(*)         AS trips
        FROM {SILVER}
        WHERE trip_start_date BETWEEN '{start}' AND '{end}'
        GROUP BY hour(started_at), member_casual
        ORDER BY hr
    """)


@st.cache_data(ttl=_TTL, show_spinner="Loading demand patterns…")
def day_of_week(start: dt.date, end: dt.date) -> pd.DataFrame:
    return run_query(f"""
        SELECT dayofweek(started_at) AS dow,   -- 1=Sunday … 7=Saturday
               count(*)              AS trips
        FROM {SILVER}
        WHERE trip_start_date BETWEEN '{start}' AND '{end}'
        GROUP BY dayofweek(started_at)
        ORDER BY dow
    """)


@st.cache_data(ttl=_TTL, show_spinner="Loading stations…")
def top_stations(start: dt.date, end: dt.date, limit: int = 12) -> pd.DataFrame:
    return run_query(f"""
        SELECT start_station_name        AS station,
               avg(start_lat)            AS lat,
               avg(start_lng)            AS lng,
               count(*)                  AS trips
        FROM {SILVER}
        WHERE trip_start_date BETWEEN '{start}' AND '{end}'
          AND start_station_name IS NOT NULL
          AND start_lat IS NOT NULL
        GROUP BY start_station_name
        ORDER BY trips DESC
        LIMIT {limit}
    """)
