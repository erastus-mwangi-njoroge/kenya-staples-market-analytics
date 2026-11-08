import numpy as np
import pandas as pd
import pytest

from agrimarket import clean, indicators, quality, reconcile
from agrimarket.config import Paths
from agrimarket.pipeline import run
from tests import synthetic as syn


@pytest.fixture(scope="module")
def std():
    return clean.standardise_wfp(syn.make_wfp())


def test_unit_parsing():
    assert clean.parse_unit_kg("KG") == 1
    assert clean.parse_unit_kg("90 KG") == 90
    assert np.isnan(clean.parse_unit_kg("L"))
    assert np.isnan(clean.parse_unit_kg(None))


def test_hxl_row_removed(tmp_path):
    p = tmp_path / "w.csv"
    syn.write_wfp_csv(syn.make_wfp(), p)
    raw = clean.load_wfp_raw(p)
    assert not raw["date"].str.startswith("#").any()


def test_schema_contract_fails_loudly(tmp_path):
    p = tmp_path / "bad.csv"
    pd.DataFrame({"date": ["2020-01-01"], "price": [1]}).to_csv(p, index=False)
    with pytest.raises(ValueError, match="schema changed"):
        clean.load_wfp_raw(p)


def test_quality_checks_detect_injected_problems(std):
    dq = quality.run_quality_checks(std).set_index("check_id")
    assert dq.loc["DQ03", "records_affected"] == 1   # duplicate
    assert dq.loc["DQ04", "records_affected"] == 1   # negative price
    assert dq.loc["DQ05", "records_affected"] == 1   # coordinates outside Kenya
    assert dq.loc["DQ09", "records_affected"] >= 1   # outlier
    assert dq.loc["DQ07", "records_affected"] > 0    # litre-based milk


def test_cleaning_is_logged_and_removes_problems(std):
    df, log = clean.clean_wfp(std)
    assert (df["price"] > 0).all()
    assert not df.duplicated(subset=quality.DUP_KEY).any()
    steps = log.set_index("step")["rows_changed"]
    assert steps["drop_duplicates"] == 1 and steps["drop_non_positive_price"] == 1


def test_spike_flag():
    s = pd.Series([100.0] * 12 + [150.0], index=pd.date_range("2020-01-01", periods=13, freq="MS"))
    out = indicators.add_spike_flag(s)
    assert out["spike"].iloc[-1] and not out["spike"].iloc[:12].any()


def test_reconcile_flags_supply_fall_without_price_rise():
    prices = pd.DataFrame({"year": [2019, 2020], "price_nominal_kes_kg": [50.0, 45.0], "months_with_data": [12, 12]})
    fao = pd.DataFrame({"year": [2019, 2020], "production_t": [4e6, 3e6]})
    out = reconcile.reconcile(prices, fao)
    assert out.iloc[-1]["reconciliation_status"].startswith("REVIEW")


def test_end_to_end(tmp_path):
    paths = Paths(tmp_path / "data", tmp_path / "out").ensure()
    syn.write_wfp_csv(syn.make_wfp(), paths.raw / "wfp_food_prices_ken.csv")
    syn.write_fao_zip(paths.raw / "faostat_qcl_normalized.zip")
    res = run(paths, "Maize", skip_download=True)
    for f in ["dq_report.csv", "cleaning_log.csv", "national_monthly.csv", "market_summary.csv",
              "reconciliation.csv", "brief.md"]:
        assert (paths.out_dir / f).exists(), f
    assert (paths.figures / "national_price_trend.png").exists()
    assert "Maize market brief" in res["brief"]
    assert (paths.processed / "wfp_prices_clean.parquet").exists()
