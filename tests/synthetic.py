"""Synthetic data with the SAME schema as the public WFP/FAOSTAT files, for offline tests/CI only.
Never used for reported findings."""
import io
import zipfile

import numpy as np
import pandas as pd

WFP_COLS = ["date", "admin1", "admin2", "market", "latitude", "longitude", "category", "commodity",
            "unit", "priceflag", "pricetype", "currency", "price", "usdprice"]
MARKETS = [("Nairobi", "Nairobi", "Nairobi", -1.28, 36.82), ("Rift Valley", "Nakuru", "Nakuru", -0.30, 36.07),
           ("Coast", "Mombasa", "Mombasa", -4.04, 39.67), ("North Eastern", "Mandera", "Mandera", 3.94, 41.86)]


def make_wfp(seed=0, years=6) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-15", periods=12 * years, freq="MS") + pd.Timedelta(days=14)
    rows = []
    for a1, a2, mk, lat, lon in MARKETS:
        for t, d in enumerate(dates):
            base = 40 + 0.4 * t + 6 * np.sin(2 * np.pi * d.month / 12) + rng.normal(0, 1.2)
            for ptype, k in (("Retail", 1.0), ("Wholesale", 0.8)):
                rows.append([d.strftime("%Y-%m-%d"), a1, a2, mk, lat, lon, "cereals and tubers", "Maize (white)",
                             "KG", "actual", ptype, "KES", round(base * k, 2), round(base * k / 120, 3)])
            rows.append([d.strftime("%Y-%m-%d"), a1, a2, mk, lat, lon, "milk and dairy", "Milk (cow, fresh)",
                         "L", "actual", "Retail", "KES", 60.0, 0.5])
    df = pd.DataFrame(rows, columns=WFP_COLS)
    # injected problems for the DQ checks
    df.loc[5, "price"] = df.loc[5, "price"] * 15           # outlier
    df.loc[10, "price"] = -3                                # invalid
    df = pd.concat([df, df.iloc[[20]]], ignore_index=True)  # duplicate
    df.loc[30, ["latitude", "longitude"]] = [50.0, 10.0]    # outside Kenya
    return df


def write_wfp_csv(df: pd.DataFrame, path):
    hxl = pd.DataFrame([["#date", "#adm1+name", "#adm2+name", "#loc+market+name", "#geo+lat", "#geo+lon",
                         "#item+type", "#item+name", "#item+unit", "#item+price+flag", "#item+price+type",
                         "#currency+code", "#value", "#value+usd"]], columns=WFP_COLS)
    pd.concat([hxl, df.astype(str)], ignore_index=True).to_csv(path, index=False)


def write_fao_zip(path, years=range(2018, 2024)):
    rows = []
    prod = [3.7e6, 4.0e6, 3.9e6, 3.4e6, 3.0e6, 3.4e6]
    for y, p in zip(years, prod):
        for el, u, v in (("Area harvested", "ha", 2.1e6), ("Production", "t", p), ("Yield", "hg/ha", p / 2.1e6 * 1e4)):
            rows.append({"Area": "Kenya", "Item": "Maize (corn)", "Element": el, "Year": y, "Unit": u, "Value": v})
    rows.append({"Area": "Uganda", "Item": "Maize (corn)", "Element": "Production", "Year": 2018, "Unit": "t", "Value": 1.0})
    buf = io.StringIO(); pd.DataFrame(rows).to_csv(buf, index=False)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Production_Crops_Livestock_E_All_Data_(Normalized).csv", buf.getvalue())
