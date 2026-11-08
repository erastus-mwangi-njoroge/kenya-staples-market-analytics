"""Cross-source reconciliation: WFP market prices vs FAOSTAT national production.

Mirrors a common analyst task: bring two independent systems together, align definitions
(units, years, item names), then flag discrepancies for human review instead of hiding them.
"""
from __future__ import annotations

import zipfile

import pandas as pd

from .config import FAOSTAT_ITEM, SUPPLY_SHOCK_THRESHOLD


def load_faostat(zip_path, area: str = "Kenya", item_contains: str = FAOSTAT_ITEM) -> pd.DataFrame:
    """Annual area harvested, production (t) and yield (kg/ha) from the FAOSTAT QCL bulk file."""
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".csv") and "normalized" in n.lower())
        with z.open(name) as fh:
            raw = pd.read_csv(fh, encoding="latin-1")
    d = raw[(raw["Area"] == area) & raw["Item"].str.contains(item_contains, case=False, na=False)
            & raw["Element"].isin(["Area harvested", "Production", "Yield"])].copy()
    if d.empty:
        raise ValueError(f"No FAOSTAT rows for {area}/{item_contains}")

    def to_std(row):  # harmonise units: yield may be hg/ha or 100g/ha depending on release
        u = str(row["Unit"]).lower().replace(" ", "")
        if row["Element"] == "Yield" and (u.startswith("hg") or u.startswith("100g")):
            return row["Value"] / 10.0
        return row["Value"]

    d["value_std"] = d.apply(to_std, axis=1)
    wide = d.pivot_table(index="Year", columns="Element", values="value_std", aggfunc="sum").reset_index()
    wide = wide.rename(columns={"Year": "year", "Production": "production_t",
                                "Area harvested": "area_harvested_ha", "Yield": "yield_kg_ha"})
    wide.columns.name = None
    return wide


def load_cpi(path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path is not None and path.exists() else None


def annual_prices(nat: pd.DataFrame, cpi: pd.DataFrame | None = None) -> pd.DataFrame:
    a = nat.assign(year=nat["month_start"].dt.year).groupby("year").agg(
        price_nominal_kes_kg=("price_kes_kg", "mean"), months_with_data=("price_kes_kg", "count")).reset_index()
    if cpi is not None and not cpi.empty:
        a = a.merge(cpi, on="year", how="left")
        base = a.dropna(subset=["cpi"]).sort_values("year").iloc[-1]["cpi"] if a["cpi"].notna().any() else None
        if base:
            a["price_real_kes_kg"] = a["price_nominal_kes_kg"] * base / a["cpi"]
    return a


def reconcile(prices_annual: pd.DataFrame, fao: pd.DataFrame) -> pd.DataFrame:
    """Join sources by year and test an agronomic expectation: big supply falls should not coincide
    with falling prices. Mismatches are flagged REVIEW (could be imports, stocks, or data error)."""
    m = prices_annual.merge(fao, on="year", how="outer").sort_values("year").reset_index(drop=True)
    price_col = "price_real_kes_kg" if "price_real_kes_kg" in m.columns else "price_nominal_kes_kg"
    m["price_basis"] = "real" if price_col == "price_real_kes_kg" else "nominal"
    m["production_yoy_pct"] = m["production_t"].pct_change(fill_method=None) * 100
    m["price_yoy_pct"] = m[price_col].pct_change(fill_method=None) * 100

    def status(r):
        if pd.isna(r["price_nominal_kes_kg"]):
            return "Missing in WFP prices"
        if pd.isna(r["production_t"]):
            return "Missing in FAOSTAT"
        if r["months_with_data"] < 9:
            return "Partial price year (<9 months)"
        if pd.notna(r["production_yoy_pct"]) and r["production_yoy_pct"] <= SUPPLY_SHOCK_THRESHOLD * 100:
            return "REVIEW: supply fall, price did not rise" if r["price_yoy_pct"] <= 0 else "Consistent: supply fall, price rose"
        return "No supply shock"

    m["reconciliation_status"] = m.apply(status, axis=1)
    return m
