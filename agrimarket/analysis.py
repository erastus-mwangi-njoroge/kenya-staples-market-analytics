"""Static figures for reports (the interactive version lives in dashboard/app.py)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})
GREEN, AMBER, GREY = "#2E7D32", "#E08A00", "#6B7280"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fig_national_trend(nat: pd.DataFrame, commodity: str, path):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(nat["month_start"], nat["price_kes_kg"], color=GREEN, lw=1.8, label="National median retail price")
    ax.plot(nat["month_start"], nat["trailing_12m_mean"], color=GREY, lw=1, ls="--", label="Trailing 12-month mean")
    sp = nat[nat["spike"]]
    ax.scatter(sp["month_start"], sp["price_kes_kg"], color=AMBER, zorder=3, s=22, label="Spike (>120% of trailing mean)")
    ax.set(title=f"{commodity}: national retail price, KES per kg", ylabel="KES / kg")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_seasonality(seas: pd.DataFrame, commodity: str, path):
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(seas["month"], seas["seasonal_index"] - 1, color=[GREEN if v >= 1 else AMBER for v in seas["seasonal_index"]])
    ax.set_xticks(range(1, 13)); ax.set_xticklabels(MONTHS)
    ax.set(title=f"{commodity}: seasonal price pattern (deviation from trend)", ylabel="Deviation from trend")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.0%}")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_market_segments(ms: pd.DataFrame, path):
    if ms.empty:
        return
    colours = {"High price / volatile": AMBER, "High price / stable": "#8D6E63",
               "Lower price / volatile": "#1E88E5", "Lower price / stable": GREEN}
    fig, ax = plt.subplots(figsize=(8, 5))
    for seg, g in ms.groupby("segment"):
        ax.scatter(g["avg_price_kes_kg"], g["volatility_pct"], s=40, label=seg, color=colours[seg], alpha=0.85)
    ax.axvline(ms["avg_price_kes_kg"].median(), color=GREY, lw=0.8, ls=":")
    ax.axhline(ms["volatility_pct"].median(), color=GREY, lw=0.8, ls=":")
    ax.set(title="Market segmentation: price level vs month-to-month volatility",
           xlabel="Average price (KES/kg)", ylabel="Volatility (std of monthly % change)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_supply_price(rec: pd.DataFrame, path):
    r = rec.dropna(subset=["production_t", "price_nominal_kes_kg"])
    if r.empty:
        return
    fig, ax1 = plt.subplots(figsize=(9, 4.2))
    ax1.bar(r["year"], r["production_t"] / 1e6, color="#A5D6A7", label="Production (million t, FAOSTAT)")
    ax1.set_ylabel("Million tonnes")
    ax2 = ax1.twinx()
    col = "price_real_kes_kg" if "price_real_kes_kg" in r.columns and r["price_real_kes_kg"].notna().any() else "price_nominal_kes_kg"
    ax2.plot(r["year"], r[col], color=AMBER, lw=2, marker="o", ms=3, label=f"Retail price ({col.split('_')[1]}, KES/kg, WFP)")
    ax2.set_ylabel("KES / kg"); ax2.grid(False)
    h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
    ax1.set_title("Supply vs price: national maize production and retail price")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def fig_margin(margin: pd.DataFrame, path):
    if margin.empty:
        return
    m = margin.groupby("month_start")["margin_pct"].median()
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(m.index, m.values, color=GREEN)
    ax.set(title="Retail-wholesale margin (median across markets)", ylabel="% of wholesale price")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
