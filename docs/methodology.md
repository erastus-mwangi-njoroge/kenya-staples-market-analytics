# Methodology, assumptions and limitations

## Scope
Explain how staple-crop market prices move in Kenya, where and when volatility is highest, and whether national supply (FAOSTAT) and prices (WFP) tell a consistent story.

## Key decisions and why
- **KES per kg as the common unit.** Weight-based units are converted using the unit string (for example "90 KG" divides by 90). Litres and pieces are not forced into kg.
- **Median across markets for national price.** WFP market coverage changes over time; a mean of whichever markets reported would drift with the market mix.
- **Robust outlier rule.** A rolling median of each series' own log price handles inflation trends; a global z-score would flag legitimate price rises as errors.
- **Flag, don't delete, outliers.** Records stay in the cleaned file with `is_outlier = True`, so a reviewer can overrule the rule.
- **Spike threshold of 120% of trailing mean.** Simple and explainable to non-technical staff; change `SPIKE_THRESHOLD` and re-run to test sensitivity.
- **Explainable segmentation.** Median splits on price and volatility rather than clustering, so a field team can see why a market sits in a segment.

## Limitations
1. WFP prices are market-monitoring observations, not farm-gate prices; they do not show what farmers received.
2. Market coverage is uneven, and some markets stop or start reporting.
3. FAOSTAT values are partly estimated; production and prices are annual aggregates, so the reconciliation test is a screening rule.
4. Nominal prices rise with inflation. Real prices need CPI; if the CPI download fails, the pipeline reports nominal values and labels them as such.
5. Correlation between production and price is not evidence of cause; imports, stocks and policy also matter.

## Reproducibility
Python 3.10+, dependencies in `requirements.txt`, tests in `tests/` (synthetic data with the same schema as the real files, never used for findings), provenance log for every download.
