# Data sources

All data are public. Nothing in this repository contains personal data. Raw files are **not committed**; the pipeline downloads them and writes `data/raw/_provenance.json` (URL, retrieval time, size, SHA-256) so every run is traceable.

| Source | Publisher | What it provides | Access |
|---|---|---|---|
| Kenya food prices | World Food Programme (WFP), via the Humanitarian Data Exchange (HDX) | Monthly retail/wholesale prices by market and commodity, 2006 onward; market coordinates; price flags | https://data.humdata.org/dataset/wfp-food-prices-for-kenya (CSV resolved through the HDX API) |
| Crops and livestock products (QCL) | FAO, FAOSTAT | Annual area harvested, production, yield by country and crop | https://www.fao.org/faostat/en/#data/QCL (bulk "Normalized" zip) |
| Consumer price index (optional) | World Bank, indicator FP.CPI.TOTL | Annual CPI (2010 = 100) to deflate prices | https://data.worldbank.org/indicator/FP.CPI.TOTL?locations=KE |

## Licences and attribution
Check the licence on each source page before redistributing derived data, and keep the attribution line in any published chart or report:
"Source: WFP Price Database (HDX); FAOSTAT; World Bank WDI. Analysis by <your name>."

## Known upstream behaviour (handled in code)
- The HDX CSV has a second row of HXL hashtags (`#date`, `#value`...). It is removed on load.
- Prices are reported in mixed units (KG, 90 KG bag, L, etc.). Weight-based units are converted to KES/kg; others are kept but excluded from per-kg indicators.
- HDX resource URLs change over time, so the pipeline asks the HDX API for the current CSV link.
- If the upstream column set changes, the loader fails with an explicit "schema changed" error instead of producing silently wrong results.

## Suggested extensions (need manual registration or download)
- **FinAccess Household Survey** (CBK, KNBS, FSD Kenya): financial inclusion by county, for farmer-finance questions.
- **KNBS Kenya Integrated Household Budget Survey (KIHBS)** via the World Bank Microdata Library: household welfare and agricultural income.
- **WFP rainfall and NDVI at subnational level** (HDX): link rainfall anomalies to price spikes.
