"""Indicator calculations. Definitions live in docs/indicator_dictionary.md; keep them in sync."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FOCUS_COMMODITY, MIN_MONTHS_FOR_MARKET_STATS, SPIKE_THRESHOLD


def analysis_base(df: pd.DataFrame, commodity: str = FOCUS_COMMODITY, pricetype: str = "Retail") -> pd.DataFrame:
    """Analysis-ready subset: one commodity, weight-based units, no outliers, no forecasts."""
    flag = df["priceflag"].fillna("actual").str.lower()
    m = (
        (df["commodity_group"] == commodity)
        & (df["pricetype"].str.lower() == pricetype.lower())
        & df["price_per_kg"].notna()
        & ~df["is_outlier"]
        & ~flag.str.contains("forecast")
    )
    return df.loc[m].copy()


def market_monthly(base: pd.DataFrame) -> pd.DataFrame:
    return (base.groupby(["admin1", "market", "month_start"], as_index=False)["price_per_kg"].mean())


def add_spike_flag(s: pd.Series, threshold: float = SPIKE_THRESHOLD) -> pd.DataFrame:
    """Spike = price above `threshold` x the mean of the *previous* 12 months (needs >= 6 obs)."""
    trailing = s.shift(1).rolling(12, min_periods=6).mean()
    return pd.DataFrame({"price": s, "trailing_12m_mean": trailing, "spike": s > threshold * trailing})


def national_monthly(mm: pd.DataFrame) -> pd.DataFrame:
    """National indicator: median of market prices each month (robust to market mix changes)."""
    nat = mm.groupby("month_start").agg(price_kes_kg=("price_per_kg", "median"),
                                        n_markets=("market", "nunique"))
    nat = nat.asfreq("MS")
    nat["mom_pct"] = nat["price_kes_kg"].pct_change(fill_method=None) * 100
    nat["yoy_pct"] = nat["price_kes_kg"].pct_change(12, fill_method=None) * 100
    sp = add_spike_flag(nat["price_kes_kg"])
    nat["trailing_12m_mean"] = sp["trailing_12m_mean"]
    nat["spike"] = sp["spike"].fillna(False)
    return nat.reset_index()


def seasonality_index(nat: pd.DataFrame) -> pd.DataFrame:
    """Median ratio of price to its centred 12-month moving average, by calendar month (1.0 = trend)."""
    s = nat.set_index("month_start")["price_kes_kg"]
    ratio = s / s.rolling(12, center=True, min_periods=12).mean()
    out = ratio.groupby(ratio.index.month).median().rename("seasonal_index").reset_index()
    out.columns = ["month", "seasonal_index"]
    return out


def market_summary(mm: pd.DataFrame) -> pd.DataFrame:
    """Per-market level, volatility, spike frequency and a simple explainable segment."""
    rows = []
    for (region, market), g in mm.groupby(["admin1", "market"]):
        s = g.set_index("month_start")["price_per_kg"].sort_index().asfreq("MS")
        if s.notna().sum() < MIN_MONTHS_FOR_MARKET_STATS:
            continue
        sp = add_spike_flag(s)
        rows.append({
            "admin1": region, "market": market, "months_observed": int(s.notna().sum()),
            "coverage_pct": round(100 * s.notna().mean(), 1),
            "avg_price_kes_kg": s.mean(),
            "volatility_pct": s.pct_change(fill_method=None).std() * 100,
            "spike_rate_pct": 100 * sp["spike"].sum() / max(sp["trailing_12m_mean"].notna().sum(), 1),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    hi_p = out["avg_price_kes_kg"] > out["avg_price_kes_kg"].median()
    hi_v = out["volatility_pct"] > out["volatility_pct"].median()
    out["segment"] = np.select(
        [hi_p & hi_v, hi_p & ~hi_v, ~hi_p & hi_v],
        ["High price / volatile", "High price / stable", "Lower price / volatile"],
        default="Lower price / stable",
    )
    return out.sort_values("volatility_pct", ascending=False).reset_index(drop=True)


def retail_wholesale_margin(df: pd.DataFrame, commodity: str = FOCUS_COMMODITY) -> pd.DataFrame:
    """Retail minus wholesale price per kg, by market-month, where both are observed."""
    flag = df["priceflag"].fillna("actual").str.lower()
    d = df[(df["commodity_group"] == commodity) & df["price_per_kg"].notna() & ~df["is_outlier"]
           & ~flag.str.contains("forecast")]
    p = d.pivot_table(index=["admin1", "market", "month_start"], columns=d["pricetype"].str.lower(),
                      values="price_per_kg", aggfunc="mean").reset_index()
    if not {"retail", "wholesale"} <= set(p.columns):
        return pd.DataFrame(columns=["admin1", "market", "month_start", "retail", "wholesale", "margin_kes_kg", "margin_pct"])
    p = p.dropna(subset=["retail", "wholesale"])
    p["margin_kes_kg"] = p["retail"] - p["wholesale"]
    p["margin_pct"] = 100 * p["margin_kes_kg"] / p["wholesale"]
    return p
