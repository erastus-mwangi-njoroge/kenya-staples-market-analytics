# Data quality framework

**Principle:** detect, log, then correct. Checks run on the standardised raw data *before* cleaning (`quality.py`), and each correction in `clean.py` maps to a finding, so nothing changes silently.

| ID | Dimension | Check | Action |
|---|---|---|---|
| DQ01 | Completeness | Missing date, market, commodity or price | Remove |
| DQ02 | Completeness | Missing coordinates or admin2 | Keep; excluded from map views |
| DQ03 | Uniqueness | Duplicates on (date, admin1, admin2, market, commodity, unit, pricetype, priceflag) | Keep first |
| DQ04 | Validity | Non-positive price | Remove |
| DQ05 | Validity | Coordinates outside Kenya's bounding box | Null coordinates |
| DQ06 | Timeliness | Future-dated records | Remove |
| DQ07 | Consistency | Units not convertible to KG | Keep; exclude from per-kg indicators (info) |
| DQ08 | Consistency | Commodity reported in several units | Standardise to KES/kg (info) |
| DQ09 | Accuracy | Outlier: modified z-score > 6 vs rolling 7-month median of the series' own log price | Flag and exclude from indicators; keep in data |
| DQ10 | Completeness | Series with < 50% monthly coverage | Keep; excluded from volatility |
| DQ11 | Accuracy | Non-"actual" price flags | Exclude forecasts (info) |
| DQ12 | Consistency | Currency other than KES | Flag |

Severity: **Pass** (0%), **Low** (<= 1% of records), **Medium** (1-5%), **High** (> 5%), **Info** (expected structural property, not a defect).

## Outputs
- `outputs/dq_report.csv`: one row per check with counts, percentages, severity and action.
- `outputs/cleaning_log.csv`: rows before/after for each cleaning step.

## Recurring-error loop (turning findings into fixes at source)
1. Review the DQ report after every data refresh.
2. For each Medium/High finding, find the entry point that produces it (form field, enumerator, system export).
3. Recommend a prevention rule (for example a required field, a unit drop-down, or a plausible-range validation) to the data owner.
4. Track whether the finding shrinks in the next refresh.
