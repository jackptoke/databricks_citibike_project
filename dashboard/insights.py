"""Turn the aggregated data into a handful of executive takeaways.

Each function returns a dict with a short finding (backed by a real number) and
a concrete recommendation, so the dashboard reads as decisions-to-make rather
than just charts.
"""

from __future__ import annotations

import pandas as pd

# Commute windows used to gauge how "commuter" the network is.
AM_PEAK = range(7, 10)  # 7–9am
PM_PEAK = range(17, 20)  # 5–7pm


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def commuter_signal(hourly: pd.DataFrame) -> dict:
    total = hourly["trips"].sum()
    peak = hourly.loc[hourly["hr"].isin([*AM_PEAK, *PM_PEAK]), "trips"].sum()
    share = peak / total if total else 0
    commuter = share >= 0.35
    return {
        "title": "Commuter vs leisure network",
        "finding": f"{_pct(share)} of trips fall in the 7–9am / 5–7pm commute peaks.",
        "recommendation": (
            "Strong commuter base — protect it with commuter-friendly perks and make sure "
            "top origin stations are rebalanced *before* the morning peak."
            if commuter
            else "Leisure-leaning demand — lean into weekend/tourist promotions and day passes."
        ),
    }


def membership_health(fact: pd.DataFrame) -> dict:
    by_type = fact.groupby("member_casual")["trips"].sum()
    total = by_type.sum()
    member_share = by_type.get("member", 0) / total if total else 0
    return {
        "title": "Recurring-revenue base",
        "finding": f"Members drive {_pct(member_share)} of trips (casual riders the rest).",
        "recommendation": (
            "Casual volume is a large conversion pool — trigger a membership offer after a "
            "rider's 3rd casual trip in a month to grow the recurring base."
            if member_share < 0.7
            else "Membership base is strong — focus on retention and frequency, not acquisition."
        ),
    }


def ebike_adoption(fact: pd.DataFrame) -> dict | None:
    monthly = (
        fact.assign(month=fact["trip_start_date"].values.astype("datetime64[M]"))
        .groupby(["month", "rideable_type"])["trips"]
        .sum()
        .unstack(fill_value=0)
    )
    if "electric_bike" not in monthly or len(monthly) < 2:
        return None
    share = monthly["electric_bike"] / monthly.sum(axis=1)
    first, last = share.iloc[0], share.iloc[-1]
    trend = "up" if last > first else "down"
    return {
        "title": "E-bike adoption",
        "finding": f"E-bikes are {_pct(last)} of trips, {trend} from {_pct(first)} at the start of the range.",
        "recommendation": (
            "E-bike demand is rising — expand the e-bike fleet and dock capacity at the busiest "
            "stations to capture the higher usage."
            if trend == "up"
            else "E-bike share is flat/declining — review pricing, availability and battery uptime."
        ),
    }


def seasonality(fact: pd.DataFrame) -> dict:
    monthly = fact.assign(m=fact["trip_start_date"].values.astype("datetime64[M]")).groupby("m")["trips"].sum()
    by_month = monthly.groupby(monthly.index.month).mean()
    peak_m, trough_m = int(by_month.idxmax()), int(by_month.idxmin())
    ratio = by_month.max() / by_month.min() if by_month.min() else 0
    names = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return {
        "title": "Seasonality",
        "finding": f"{names[peak_m - 1]} runs ~{ratio:.1f}× the volume of the low month ({names[trough_m - 1]}).",
        "recommendation": (
            "Sharp seasonal swing — flex the fleet and staffing seasonally, and test off-season "
            "membership discounts to smooth demand."
        ),
    }


def station_concentration(stations: pd.DataFrame, fact: pd.DataFrame) -> dict:
    total = fact["trips"].sum()
    top5 = stations.nlargest(5, "trips")["trips"].sum()
    share = top5 / total if total else 0
    return {
        "title": "Network concentration",
        "finding": f"The top 5 start stations account for {_pct(share)} of all trips.",
        "recommendation": (
            "Demand is concentrated — prioritise dock expansion and rebalancing at these hubs; "
            "they give the highest return on capital."
        ),
    }


def build_all(fact: pd.DataFrame, hourly: pd.DataFrame, stations: pd.DataFrame) -> list[dict]:
    candidates = [
        commuter_signal(hourly),
        membership_health(fact),
        ebike_adoption(fact),
        seasonality(fact),
        station_concentration(stations, fact),
    ]
    return [c for c in candidates if c]
