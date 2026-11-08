"""End-to-end pipeline: ingest -> validate -> clean -> indicators -> reconcile -> report.

Usage:
    python -m agrimarket.pipeline                 # download + run
    python -m agrimarket.pipeline --skip-download # reuse files already in data/raw
    python -m agrimarket.pipeline --commodity Beans
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import analysis, clean, indicators, ingest, quality, reconcile, report
from .config import FOCUS_COMMODITY, Paths


def run(paths: Paths, commodity: str = FOCUS_COMMODITY, skip_download: bool = False) -> dict:
    paths.ensure()

    # 1. Ingest
    if skip_download:
        wfp_csv, fao_zip = paths.raw / "wfp_food_prices_ken.csv", paths.raw / "faostat_qcl_normalized.zip"
        cpi_csv = paths.raw / "wb_cpi_kenya.csv"
    else:
        wfp_csv, fao_zip, cpi_csv = ingest.fetch_wfp_prices(paths), ingest.fetch_faostat_qcl(paths), ingest.fetch_cpi(paths)

    # 2. Standardise and validate BEFORE cleaning, so findings reflect the raw state
    std = clean.standardise_wfp(clean.load_wfp_raw(wfp_csv))
    dq = quality.run_quality_checks(std)
    dq.to_csv(paths.out_dir / "dq_report.csv", index=False)

    # 3. Clean (every correction logged)
    df, cleaning_log = clean.clean_wfp(std)
    cleaning_log.to_csv(paths.out_dir / "cleaning_log.csv", index=False)
    df.to_parquet(paths.processed / "wfp_prices_clean.parquet", index=False)

    # 4. Indicators
    base = indicators.analysis_base(df, commodity)
    if base.empty:
        raise ValueError(f"No analysable retail records for commodity '{commodity}'")
    mm = indicators.market_monthly(base)
    nat = indicators.national_monthly(mm)
    seas = indicators.seasonality_index(nat)
    ms = indicators.market_summary(mm)
    margin = indicators.retail_wholesale_margin(df, commodity)
    nat.to_csv(paths.out_dir / "national_monthly.csv", index=False)
    seas.to_csv(paths.out_dir / "seasonality.csv", index=False)
    ms.to_csv(paths.out_dir / "market_summary.csv", index=False)
    margin.to_csv(paths.out_dir / "retail_wholesale_margin.csv", index=False)

    # 5. Reconcile with FAOSTAT (only meaningful for a crop that exists in FAOSTAT)
    rec = None
    if fao_zip.exists():
        cpi = reconcile.load_cpi(cpi_csv) if cpi_csv else None
        fao = reconcile.load_faostat(fao_zip, item_contains=commodity)
        rec = reconcile.reconcile(reconcile.annual_prices(nat, cpi), fao)
        rec.to_csv(paths.out_dir / "reconciliation.csv", index=False)
        analysis.fig_supply_price(rec, paths.figures / "supply_vs_price.png")

    # 6. Figures + brief
    analysis.fig_national_trend(nat, commodity, paths.figures / "national_price_trend.png")
    analysis.fig_seasonality(seas, commodity, paths.figures / "seasonality.png")
    analysis.fig_market_segments(ms, paths.figures / "market_segments.png")
    analysis.fig_margin(margin, paths.figures / "retail_wholesale_margin.png")
    brief = report.build_brief(commodity, nat, seas, ms, rec, dq, margin)
    (paths.out_dir / "brief.md").write_text(brief, encoding="utf-8")

    return {"dq": dq, "cleaning_log": cleaning_log, "national": nat, "markets": ms,
            "reconciliation": rec, "margin": margin, "brief": brief}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=Paths().data_dir)
    ap.add_argument("--out-dir", type=Path, default=Paths().out_dir)
    ap.add_argument("--commodity", default=FOCUS_COMMODITY)
    ap.add_argument("--skip-download", action="store_true")
    a = ap.parse_args()
    res = run(Paths(a.data_dir, a.out_dir), a.commodity, a.skip_download)
    print(res["dq"][["check_id", "description", "records_affected", "severity"]].to_string(index=False))
    print(f"\nDone. Outputs in {a.out_dir}/ (open brief.md first).")


if __name__ == "__main__":
    main()
