-- Run with:  python sql/run_sql.py          (DuckDB reads the cleaned parquet; no database server needed)
-- Table `prices` = data/processed/wfp_prices_clean.parquet

-- name: q1_monthly_national_median_with_yoy
-- Window functions: year-on-year change of the national median maize retail price.
WITH monthly AS (
  SELECT month_start, MEDIAN(price_per_kg) AS price
  FROM prices
  WHERE commodity_group = 'Maize' AND lower(pricetype) = 'retail'
    AND price_per_kg IS NOT NULL AND NOT is_outlier
  GROUP BY 1
)
SELECT month_start,
       ROUND(price, 2) AS price_kes_kg,
       ROUND(100 * (price / LAG(price, 12) OVER (ORDER BY month_start) - 1), 1) AS yoy_pct
FROM monthly
ORDER BY month_start DESC
LIMIT 24;

-- name: q2_most_volatile_markets
-- Rank markets by volatility of month-on-month change (markets with >= 24 months of data).
WITH m AS (
  SELECT admin1, market, month_start, AVG(price_per_kg) AS p
  FROM prices
  WHERE commodity_group = 'Maize' AND lower(pricetype) = 'retail' AND price_per_kg IS NOT NULL AND NOT is_outlier
  GROUP BY ALL
), chg AS (
  SELECT *, p / LAG(p) OVER (PARTITION BY market ORDER BY month_start) - 1 AS mom
  FROM m
)
SELECT admin1, market, COUNT(*) AS months, ROUND(AVG(p), 1) AS avg_price,
       ROUND(100 * STDDEV(mom), 1) AS volatility_pct,
       RANK() OVER (ORDER BY STDDEV(mom) DESC) AS volatility_rank
FROM chg
GROUP BY admin1, market
HAVING COUNT(*) >= 24
ORDER BY volatility_rank
LIMIT 15;

-- name: q3_regional_price_gap_vs_national
-- How far each region's average sits above/below the national average, by year.
WITH r AS (
  SELECT year, admin1, AVG(price_per_kg) AS p
  FROM prices
  WHERE commodity_group = 'Maize' AND lower(pricetype) = 'retail' AND price_per_kg IS NOT NULL AND NOT is_outlier
  GROUP BY 1, 2
)
SELECT year, admin1, ROUND(p, 1) AS price,
       ROUND(100 * (p / AVG(p) OVER (PARTITION BY year) - 1), 1) AS gap_vs_national_pct
FROM r
WHERE year >= (SELECT MAX(year) - 4 FROM r)
ORDER BY year DESC, gap_vs_national_pct DESC;

-- name: q4_retail_wholesale_margin_by_market
-- Self-join of price types: where is the retail mark-up highest?
WITH x AS (
  SELECT market, month_start,
         AVG(price_per_kg) FILTER (WHERE lower(pricetype) = 'retail')    AS retail,
         AVG(price_per_kg) FILTER (WHERE lower(pricetype) = 'wholesale') AS wholesale
  FROM prices
  WHERE commodity_group = 'Maize' AND price_per_kg IS NOT NULL AND NOT is_outlier
  GROUP BY 1, 2
)
SELECT market, COUNT(*) AS months_with_both,
       ROUND(MEDIAN(100 * (retail - wholesale) / wholesale), 1) AS median_margin_pct
FROM x
WHERE retail IS NOT NULL AND wholesale IS NOT NULL
GROUP BY market
HAVING COUNT(*) >= 12
ORDER BY median_margin_pct DESC
LIMIT 15;

-- name: q5_reporting_gaps
-- Data-quality view: markets whose maize series has the longest gap (months) between consecutive reports.
WITH m AS (
  SELECT market, month_start,
         date_diff('month', LAG(month_start) OVER (PARTITION BY market ORDER BY month_start), month_start) AS gap_months
  FROM (SELECT DISTINCT market, month_start FROM prices
        WHERE commodity_group = 'Maize' AND lower(pricetype) = 'retail')
)
SELECT market, MAX(gap_months) AS longest_gap_months, COUNT(*) AS months_reported
FROM m GROUP BY market ORDER BY longest_gap_months DESC NULLS LAST LIMIT 15;
