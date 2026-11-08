"""Interactive dashboard. Run the pipeline first, then:  streamlit run dashboard/app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `agrimarket` importable

import altair as alt
import pandas as pd
import streamlit as st

from agrimarket import indicators
from agrimarket.config import ROOT

st.set_page_config(page_title="Kenya staples market monitor", layout="wide")
PARQUET = ROOT / "data/processed/wfp_prices_clean.parquet"
OUT = ROOT / "outputs"

if not PARQUET.exists():
    st.error("No processed data found. Run `python -m agrimarket.pipeline` first.")
    st.stop()


@st.cache_data
def load() -> pd.DataFrame:
    return pd.read_parquet(PARQUET)


df = load()
st.title("Kenya staples market monitor")
st.caption("Source: WFP food price database via HDX; FAOSTAT. All figures are KES per kg, retail unless stated.")

# ---- Filters
with st.sidebar:
    st.header("Filters")
    commodities = sorted(df.loc[df["price_per_kg"].notna(), "commodity_group"].dropna().unique())
    commodity = st.selectbox("Commodity", commodities, index=commodities.index("Maize") if "Maize" in commodities else 0)
    pricetype = st.radio("Price type", ["Retail", "Wholesale"], horizontal=True)
    regions = sorted(df["admin1"].dropna().unique())
    sel_regions = st.multiselect("Region (admin1)", regions, default=regions)
    yrs = (int(df["year"].min()), int(df["year"].max()))
    yr_range = st.slider("Years", yrs[0], yrs[1], (max(yrs[0], yrs[1] - 10), yrs[1]))

d = df[df["admin1"].isin(sel_regions) & df["year"].between(*yr_range)]
base = indicators.analysis_base(d, commodity, pricetype)
if base.empty:
    st.warning("No data for this selection."); st.stop()

mm = indicators.market_monthly(base)
nat = indicators.national_monthly(mm)
last = nat.dropna(subset=["price_kes_kg"]).iloc[-1]

# ---- KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Latest price ({last['month_start']:%b %Y})", f"KES {last['price_kes_kg']:.1f}/kg")
c2.metric("Change vs 12 months ago", f"{last['yoy_pct']:+.1f}%" if pd.notna(last["yoy_pct"]) else "n/a")
c3.metric("Spike months (last 24)", int(nat.tail(24)["spike"].sum()))
c4.metric("Markets reporting (latest)", int(last["n_markets"]))

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Trend", "Seasonality", "Markets", "Supply vs price", "Data quality"])

with tab1:
    ch = alt.Chart(nat).mark_line(color="#2E7D32").encode(x="month_start:T", y=alt.Y("price_kes_kg:Q", title="KES/kg"))
    pts = alt.Chart(nat[nat["spike"]]).mark_circle(color="#E08A00", size=70).encode(x="month_start:T", y="price_kes_kg:Q",
                                                                                   tooltip=["month_start:T", "price_kes_kg:Q"])
    st.altair_chart((ch + pts).properties(height=380), use_container_width=True)
    st.caption("Orange points: price above 120% of the trailing 12-month mean.")

with tab2:
    seas = indicators.seasonality_index(nat)
    st.altair_chart(alt.Chart(seas).mark_bar(color="#2E7D32").encode(
        x=alt.X("month:O", title="Month"), y=alt.Y("seasonal_index:Q", scale=alt.Scale(zero=False), title="Index (1.0 = trend)")
    ).properties(height=320), use_container_width=True)

with tab3:
    ms = indicators.market_summary(mm)
    if ms.empty:
        st.info("Not enough history per market for this selection.")
    else:
        st.altair_chart(alt.Chart(ms).mark_circle(size=90).encode(
            x=alt.X("avg_price_kes_kg:Q", title="Average KES/kg"), y=alt.Y("volatility_pct:Q", title="Volatility %"),
            color="segment:N", tooltip=["market", "admin1", "avg_price_kes_kg", "volatility_pct", "spike_rate_pct"]
        ).properties(height=420), use_container_width=True)
        st.dataframe(ms.round(1), use_container_width=True, hide_index=True)

with tab4:
    rec_f = OUT / "reconciliation.csv"
    if rec_f.exists():
        rec = pd.read_csv(rec_f)
        st.dataframe(rec.round(2), use_container_width=True, hide_index=True)
        st.caption("Rows marked REVIEW need a human check before being reported (imports, stocks and data errors are all possible causes).")
    else:
        st.info("Run the pipeline with FAOSTAT data to populate this tab.")

with tab5:
    dq_f = OUT / "dq_report.csv"
    if dq_f.exists():
        st.dataframe(pd.read_csv(dq_f), use_container_width=True, hide_index=True)
    log_f = OUT / "cleaning_log.csv"
    if log_f.exists():
        st.subheader("Cleaning log"); st.dataframe(pd.read_csv(log_f), use_container_width=True, hide_index=True)
