"""Data quality framework: every check returns a documented, reproducible finding.

Dimensions follow common DQ practice: Completeness, Validity, Uniqueness, Consistency,
Timeliness and Accuracy. Checks *detect and log*; corrections happen in clean.py so that
every change to the data is traceable to a finding.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import KENYA_BBOX, MIN_SERIES_COVERAGE, OUTLIER_MAD_Z

DUP_KEY = ["date", "admin1", "admin2", "market", "commodity", "unit", "pricetype", "priceflag"]
SERIES_KEY = ["market", "commodity_group", "pricetype", "unit"]


def flag_outliers(df: pd.DataFrame, z: float = OUTLIER_MAD_Z) -> pd.Series:
    """Flag prices that deviate from their own series' rolling median (robust to inflation trends)."""
    d = df.sort_values("date")
    valid = d["price"] > 0

    def _flag(s: pd.Series) -> pd.Series:
        x = np.log(s.where(s > 0))
        resid = x - x.rolling(7, center=True, min_periods=4).median()
        mad = max(resid.abs().median(), 0.02)  # floor stops flat series flagging tiny moves
        return (0.6745 * resid.abs() / mad) > z

    keys = [k for k in SERIES_KEY if k in d.columns]
    out = d.assign(_p=d["price"].where(valid)).groupby(keys, dropna=False)["_p"].transform(_flag)
    return out.fillna(False).astype(bool).reindex(df.index)


def _severity(pct: float) -> str:
    if pct == 0:
        return "Pass"
    return "High" if pct > 5 else "Medium" if pct > 1 else "Low"


def _finding(check_id, dimension, description, n, total, action, info=False) -> dict:
    """info=True marks expected structural properties (not defects) so they do not inflate severity."""
    pct = round(100 * n / total, 3) if total else 0.0
    return {
        "check_id": check_id, "dimension": dimension, "description": description,
        "records_affected": int(n), "pct_of_records": pct,
        "severity": "Info" if info else _severity(pct), "action_taken": action,
    }


def run_quality_checks(df: pd.DataFrame) -> pd.DataFrame:
    """Run all checks on the standardised (not yet cleaned) dataset."""
    n = len(df)
    f = []

    crit = ["date", "market", "commodity", "price"]
    f.append(_finding("DQ01", "Completeness", f"Missing any of critical fields {crit}",
                      df[crit].isna().any(axis=1).sum(), n, "Records removed (cannot be analysed)"))
    f.append(_finding("DQ02", "Completeness", "Missing coordinates or admin2 (sub-county/county)",
                      (df[["latitude", "longitude", "admin2"]].isna().any(axis=1)).sum(), n,
                      "Retained; excluded from map views only"))
    f.append(_finding("DQ03", "Uniqueness", f"Duplicate records on key {DUP_KEY}",
                      df.duplicated(subset=DUP_KEY, keep="first").sum(), n, "First occurrence kept, rest dropped"))
    f.append(_finding("DQ04", "Validity", "Non-positive prices",
                      (df["price"] <= 0).sum(), n, "Records removed"))

    lat_ok = df["latitude"].between(*KENYA_BBOX["lat"])
    lon_ok = df["longitude"].between(*KENYA_BBOX["lon"])
    has_xy = df[["latitude", "longitude"]].notna().all(axis=1)
    f.append(_finding("DQ05", "Validity", "Coordinates outside Kenya's bounding box",
                      (has_xy & ~(lat_ok & lon_ok)).sum(), n, "Coordinates nulled; price retained"))
    f.append(_finding("DQ06", "Timeliness", "Future-dated records",
                      (df["date"] > pd.Timestamp.today().normalize()).sum(), n, "Records removed"))
    f.append(_finding("DQ07", "Consistency", "Units that cannot be converted to KG (e.g. litres, pieces)",
                      df["kg_per_unit"].isna().sum(), n, "Retained; excluded from per-kg indicators", info=True))

    unit_counts = df.groupby("commodity_group")["unit"].nunique()
    multi = df["commodity_group"].isin(unit_counts[unit_counts > 1].index)
    f.append(_finding("DQ08", "Consistency", "Commodities reported in more than one unit",
                      multi.sum(), n, "Prices standardised to KES per KG where unit is weight-based", info=True))

    f.append(_finding("DQ09", "Accuracy",
                      f"Price outliers (modified z > {OUTLIER_MAD_Z} vs rolling median of own series)",
                      flag_outliers(df).sum(), n, "Flagged (is_outlier) and excluded from indicators; retained in data"))

    d = df.dropna(subset=["date"]).assign(m=lambda x: x["date"].dt.to_period("M"))
    g = d.groupby(SERIES_KEY, dropna=False)["m"].agg(["nunique", "min", "max", "size"])
    span = (g["max"] - g["min"]).apply(lambda x: x.n) + 1
    sparse = g[(g["nunique"] / span) < MIN_SERIES_COVERAGE]
    f.append(_finding("DQ10", "Completeness",
                      f"Records in series with < {int(MIN_SERIES_COVERAGE*100)}% monthly coverage",
                      int(sparse["size"].sum()), n, "Retained; series excluded from volatility statistics"))

    f.append(_finding("DQ11", "Accuracy", "Non-'actual' price flags (aggregate/forecast/other)",
                      (~df["priceflag"].fillna("actual").str.lower().eq("actual")).sum(), n,
                      "Forecasts excluded from indicators; aggregates retained", info=True))
    f.append(_finding("DQ12", "Consistency", "Currency other than KES",
                      (df["currency"].fillna("KES").str.upper() != "KES").sum(), n, "Flagged for review; none converted"))

    return pd.DataFrame(f)
