"""Citibike executive snapshot — a single-page Streamlit dashboard.

Reads the medallion pipeline's silver/gold tables from a Databricks SQL
Warehouse and presents a business-at-a-glance view for a bike-share executive:
growth, revenue-mix proxies, demand patterns, network hotspots, and a set of
auto-generated recommendations.
"""

from __future__ import annotations

import datetime as dt

import insights
import pandas as pd
import plotly.express as px
import queries
import streamlit as st
from databricks_client import CATALOG

# --- Theme constants ---------------------------------------------------------
MEMBER_COLORS = {"member": "#0B6FB4", "casual": "#F2A900"}
BIKE_COLORS = {"classic_bike": "#0B6FB4", "electric_bike": "#17B890", "docked_bike": "#9AA5B1"}
PLOT_TMPL = "plotly_white"
DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

st.set_page_config(page_title="Citibike Executive Snapshot", page_icon="🚲", layout="wide")


def _fmt(n: float) -> str:
    """Human-friendly large-number formatting (1.2M, 34.5K, 812)."""
    for unit, div in (("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n:.0f}"


def _delta(curr: float, prev: float) -> str | None:
    if not prev:
        return None
    return f"{(curr - prev) / prev * 100:+.1f}% vs prior period"


# --- Data --------------------------------------------------------------------
try:
    lo, hi = queries.date_bounds()
    fact_all = queries.daily_fact()
except Exception as exc:  # missing config or warehouse asleep/unreachable
    st.error(
        "Could not reach the Databricks SQL Warehouse.\n\n"
        f"```\n{exc}\n```\n\n"
        "Check the `DATABRICKS_*` environment variables (see `dashboard/.env.example`) "
        "and that the warehouse and Unity Catalog grants are in place."
    )
    st.stop()

fact_all["trip_start_date"] = pd.to_datetime(fact_all["trip_start_date"])

# --- Sidebar / filters -------------------------------------------------------
st.sidebar.title("🚲 Citibike")
st.sidebar.caption(f"Source: `{CATALOG}` · silver + gold")
# Default the range to the most recent ~12 months of available data.
default_start = max(lo, (hi.replace(day=1) - pd.DateOffset(months=11)).date())
date_range = st.sidebar.date_input(
    "Date range",
    value=(default_start, hi),
    min_value=lo,
    max_value=hi,
)
if not isinstance(date_range, tuple) or len(date_range) != 2:
    st.stop()
start, end = date_range
st.sidebar.caption(f"Data available {lo} → {hi}")

# --- Filter to selected range + previous equal-length period -----------------
mask = (fact_all["trip_start_date"].dt.date >= start) & (fact_all["trip_start_date"].dt.date <= end)
fact = fact_all[mask]
span = (end - start).days + 1
prev_mask = (fact_all["trip_start_date"].dt.date >= start - dt.timedelta(days=span)) & (
    fact_all["trip_start_date"].dt.date < start
)
fact_prev = fact_all[prev_mask]

if fact.empty:
    st.warning("No trips in the selected range.")
    st.stop()

hourly = queries.hour_of_day(start, end)
dow = queries.day_of_week(start, end)
stations = queries.top_stations(start, end)

# --- Header ------------------------------------------------------------------
st.title("Executive Snapshot")
st.caption(
    f"Jersey City Citibike · {start:%b %d, %Y} – {end:%b %d, %Y}. "
    "Trip volume is used as the demand/revenue proxy (the dataset has no revenue or user data)."
)

# --- KPI row -----------------------------------------------------------------
total = fact["trips"].sum()
total_prev = fact_prev["trips"].sum()
days = fact["trip_start_date"].dt.date.nunique()
member_share = fact.loc[fact["member_casual"] == "member", "trips"].sum() / total
ebike_share = fact.loc[fact["rideable_type"] == "electric_bike", "trips"].sum() / total
avg_dur = (fact["trips"] * fact["avg_dur"]).sum() / total

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total trips", _fmt(total), _delta(total, total_prev))
k2.metric("Avg trips / day", _fmt(total / days))
k3.metric("Member share", f"{member_share * 100:.0f}%")
k4.metric("E-bike share", f"{ebike_share * 100:.0f}%")
k5.metric("Avg duration", f"{avg_dur:.1f} min")

st.divider()

# --- Ridership trend ---------------------------------------------------------
st.subheader("Ridership over time")
monthly_mix = (
    fact.assign(month=fact["trip_start_date"].values.astype("datetime64[M]"))
    .groupby(["month", "member_casual"], as_index=False)["trips"]
    .sum()
)
fig = px.area(
    monthly_mix,
    x="month",
    y="trips",
    color="member_casual",
    color_discrete_map=MEMBER_COLORS,
    template=PLOT_TMPL,
    labels={"trips": "Trips", "month": "", "member_casual": "Rider"},
)
fig.update_layout(height=320, legend_title_text="", margin=dict(t=10, b=0))
st.plotly_chart(fig, use_container_width=True)

# --- Demand patterns ---------------------------------------------------------
c1, c2 = st.columns(2)
with c1:
    st.subheader("When do people ride? (hour of day)")
    fig = px.bar(
        hourly,
        x="hr",
        y="trips",
        color="member_casual",
        color_discrete_map=MEMBER_COLORS,
        template=PLOT_TMPL,
        labels={"hr": "Hour", "trips": "Trips", "member_casual": "Rider"},
    )
    fig.update_layout(height=300, legend_title_text="", margin=dict(t=10, b=0), barmode="stack")
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.subheader("Which days? (day of week)")
    dow = dow.assign(day=dow["dow"].map(lambda d: DOW_NAMES[int(d) - 1]))
    fig = px.bar(dow, x="day", y="trips", template=PLOT_TMPL, labels={"day": "", "trips": "Trips"})
    fig.update_traces(marker_color="#0B6FB4")
    fig.update_layout(height=300, margin=dict(t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

# --- Mix trends --------------------------------------------------------------
c3, c4 = st.columns(2)
with c3:
    st.subheader("Membership mix trend")
    mm = monthly_mix.pivot(index="month", columns="member_casual", values="trips").fillna(0)
    mm_share = (mm.div(mm.sum(axis=1), axis=0) * 100).reset_index().melt("month", var_name="Rider", value_name="pct")
    fig = px.area(
        mm_share,
        x="month",
        y="pct",
        color="Rider",
        color_discrete_map=MEMBER_COLORS,
        template=PLOT_TMPL,
        labels={"pct": "% of trips", "month": ""},
    )
    fig.update_layout(height=300, legend_title_text="", margin=dict(t=10, b=0), yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
with c4:
    st.subheader("E-bike adoption")
    fleet = (
        fact.assign(month=fact["trip_start_date"].values.astype("datetime64[M]"))
        .groupby(["month", "rideable_type"], as_index=False)["trips"]
        .sum()
    )
    fig = px.area(
        fleet,
        x="month",
        y="trips",
        color="rideable_type",
        color_discrete_map=BIKE_COLORS,
        template=PLOT_TMPL,
        labels={"trips": "Trips", "month": "", "rideable_type": "Bike"},
    )
    fig.update_layout(height=300, legend_title_text="", margin=dict(t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)

# --- Network -----------------------------------------------------------------
c5, c6 = st.columns((5, 4))
with c5:
    st.subheader("Busiest start stations")
    top = stations.sort_values("trips")
    fig = px.bar(
        top, x="trips", y="station", orientation="h", template=PLOT_TMPL, labels={"trips": "Trips", "station": ""}
    )
    fig.update_traces(marker_color="#0B6FB4")
    fig.update_layout(height=380, margin=dict(t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
with c6:
    st.subheader("Demand map")
    fig = px.scatter_map(
        stations,
        lat="lat",
        lon="lng",
        size="trips",
        color="trips",
        hover_name="station",
        color_continuous_scale="Teal",
        size_max=32,
        zoom=11,
        map_style="carto-positron",
    )
    fig.update_layout(height=380, margin=dict(t=0, b=0, l=0, r=0), coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- Executive takeaways -----------------------------------------------------
st.subheader("📌 Executive takeaways")
cards = insights.build_all(fact, hourly, stations)
cols = st.columns(len(cards) if cards else 1)
for col, card in zip(cols, cards):
    with col:
        st.markdown(f"**{card['title']}**")
        st.markdown(card["finding"])
        st.info(card["recommendation"])

st.caption("Built on the Databricks medallion pipeline in this repo · figures update as the pipeline runs.")
