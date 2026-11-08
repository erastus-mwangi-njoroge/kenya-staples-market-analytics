"""Load, standardise and clean WFP price data. Every transformation is logged."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .config import KENYA_BBOX, REQUIRED_WFP_COLUMNS
from .quality import DUP_KEY, flag_outliers

_UNIT_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)?\s*KG\s*$", re.IGNORECASE)


def parse_unit_kg(unit) -> float:
    """'KG' -> 1, '90 KG' -> 90, anything else (L, Unit, Bunch...) -> NaN."""
    if not isinstance(unit, str):
        return np.nan
    m = _UNIT_RE.match(unit)
    if not m:
        return np.nan
    return float(m.group(1)) if m.group(1) else 1.0


def load_wfp_raw(path) -> pd.DataFrame:
    """Read the HDX CSV. Row 2 holds HXL hashtags (e.g. '#date'), which are not data."""
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_WFP_COLUMNS if c not in df.columns]
    if missing:  # data contract: fail loudly if the upstream schema changes
        raise ValueError(f"Upstream schema changed; missing columns: {missing}")
    return df[~df["date"].astype(str).str.startswith("#")].copy()


def standardise_wfp(df: pd.DataFrame) -> pd.DataFrame:
    """Type conversion and derived fields. No rows are dropped here."""
    d = df.copy()
    for c in ["admin1", "admin2", "market", "category", "commodity", "unit", "priceflag", "pricetype", "currency"]:
        d[c] = d[c].astype("string").str.strip()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    for c in ["latitude", "longitude", "price", "usdprice"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["month_start"] = d["date"].dt.to_period("M").dt.to_timestamp()
    d["year"] = d["date"].dt.year
    d["commodity_group"] = d["commodity"].str.replace(r"\s*\(.*\)\s*$", "", regex=True).str.strip()
    d["kg_per_unit"] = d["unit"].map(parse_unit_kg)
    d["price_per_kg"] = d["price"] / d["kg_per_unit"]
    return d


def clean_wfp(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply corrections documented in the DQ report. Returns (clean_df, cleaning_log)."""
    log = []

    def record(step, before, after, rule):
        log.append({"step": step, "rows_before": before, "rows_after": after,
                    "rows_changed": before - after, "rule": rule})

    x = d.copy()
    b = len(x)
    x = x.dropna(subset=["date", "market", "commodity", "price"])
    record("drop_missing_critical", b, len(x), "date, market, commodity, price must be present")

    b = len(x)
    x = x[x["price"] > 0]
    record("drop_non_positive_price", b, len(x), "price > 0")

    b = len(x)
    x = x[x["date"] <= pd.Timestamp.today().normalize()]
    record("drop_future_dates", b, len(x), "date <= today")

    b = len(x)
    x = x.drop_duplicates(subset=DUP_KEY, keep="first")
    record("drop_duplicates", b, len(x), f"unique on {DUP_KEY}")

    bad_xy = ~(x["latitude"].between(*KENYA_BBOX["lat"]) & x["longitude"].between(*KENYA_BBOX["lon"]))
    bad_xy &= x[["latitude", "longitude"]].notna().all(axis=1)
    x.loc[bad_xy, ["latitude", "longitude"]] = np.nan
    log.append({"step": "null_invalid_coordinates", "rows_before": len(x), "rows_after": len(x),
                "rows_changed": int(bad_xy.sum()), "rule": "coordinates inside Kenya bounding box"})

    x["is_outlier"] = flag_outliers(x)
    log.append({"step": "flag_outliers", "rows_before": len(x), "rows_after": len(x),
                "rows_changed": int(x["is_outlier"].sum()), "rule": "flag only; excluded from indicators"})

    return x.reset_index(drop=True), pd.DataFrame(log)
