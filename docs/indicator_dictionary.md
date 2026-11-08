# Indicator dictionary

One row per indicator: definition, formula, source, level, frequency, and known limits. Code lives in `agrimarket/indicators.py`. If a calculation changes, update this file in the same commit.

| ID | Indicator | Definition / formula | Source | Level | Frequency | Limitations |
|---|---|---|---|---|---|---|
| IND01 | Market monthly price | Mean of `price_per_kg` for a market-month (retail, weight-based units, outliers and forecasts excluded) | WFP | Market | Monthly | Mean of observations within a month; collection dates vary |
| IND02 | National price | Median of IND01 across reporting markets in the month | WFP | National | Monthly | Median reduces effect of market mix changes but is not population-weighted |
| IND03 | MoM change | `(P_t / P_t-1 - 1) x 100` of IND02 | WFP | National | Monthly | Undefined if the previous month is missing |
| IND04 | YoY change | `(P_t / P_t-12 - 1) x 100` of IND02 | WFP | National | Monthly | Nominal unless stated; inflation inflates YoY |
| IND05 | Price spike | `P_t > 1.20 x mean(P_t-12 ... P_t-1)`; needs at least 6 prior observations | WFP | National / market | Monthly | Threshold set in `config.SPIKE_THRESHOLD`; sensitive to short series |
| IND06 | Seasonal index | Median over years of `P_t / centred 12-month moving average`, by calendar month | WFP | National | Monthly profile | Needs at least 12 consecutive months around each point; regional rains differ |
| IND07 | Market volatility | Standard deviation of month-on-month % change of IND01 (markets with at least 24 months) | WFP | Market | Whole period | Gaps reduce reliability |
| IND08 | Market spike rate | Share of eligible months flagged as IND05 | WFP | Market | Whole period | As IND05 |
| IND09 | Market segment | Median split on average price and volatility: 4 segments | WFP | Market | Whole period | Relative, not absolute, classification |
| IND10 | Retail-wholesale margin | `(Retail - Wholesale) / Wholesale x 100` for market-months with both | WFP | Market | Monthly | Quality and quantity grades may differ between price types |
| IND11 | Annual price | Mean of monthly IND02 within a year; real price = nominal x CPI_base / CPI_year | WFP, World Bank | National | Annual | Years with fewer than 9 months flagged "partial" |
| IND12 | Maize production, area, yield | FAOSTAT values (yield converted to kg/ha) | FAOSTAT | National | Annual | FAO figures include estimates and imputations (see FAO flags) |
| IND13 | Supply-price consistency | Year flagged REVIEW when production YoY <= -15% and price YoY <= 0 | WFP + FAOSTAT | National | Annual | A screening rule, not a causal claim |
