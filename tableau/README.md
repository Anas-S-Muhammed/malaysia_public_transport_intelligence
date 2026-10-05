# Tableau build specification

The CSV and calculations are ready; a Tableau workbook and Tableau Public publication have **not** been created. Build these manually in Tableau Desktop or Tableau Public. Do not add screenshots or a public link until the workbook exists and has been checked.

## Data contract

Import `data/processed/tableau_ridership.csv`: one row per date and service, including unreported rows with blank Ridership. It deliberately uses the same validated analytical fields as the long export, without precomputed growth KPIs. Use `Is Observed` for coverage. Review `data/README.md` and `calculated_fields.md` before aggregating.

Use an approximately 1200 x 800 layout, white background, one font, dark blue for counts and muted amber for comparisons. Place scope and coverage notes beside KPI cards. Tooltips should identify the date, service, observed count, and comparison baseline.

## 1. Executive Overview

Top row: title, extract date range, date/service/mode filters, and a toggle between reported services and the fixed four-service basket. KPI cards: selected-period reported rides, average daily rides, comparable YoY growth, leading service, and highest-growth eligible service. Each growth card names its baseline and eligible service population; show unavailable comparisons as blank or N/A.

Main row: monthly trend and horizontal service ranking. Lower row: horizontal mode contribution and full-year basket comparison. Default to 2025, the latest complete year in this snapshot. Include the coverage count beside total demand; do not compare expanding reported totals as if coverage were fixed. The fixed basket comprises Ampang, Kajang, Kelana Jaya, and Monorail.

## 2. Service Performance

Show an annual ranking, complete-period YoY growth bars, selected-service daily/rolling trend, paired weekday/weekend bars, and a growth-versus-volume scatter. Use a service selection action to filter the trend and pattern sheets. Label the scatter's eligible years and exclude unavailable growth rather than displaying it at zero.

Fastest-growing means largest percentage increase among services with full observed counts in both calendar years; it does not mean largest absolute passenger gain. Rank the lowest-volume services too, with clear coverage labels. The Shah Alam series has no 2025 observations and must not appear as a zero-ridership service for that year.

## 3. Ridership Patterns

Use a month x weekday heatmap for the selected service/year, average daily rides by month, a daily trend with 7/30-day averages, and a volatility table. Display observed days in tooltips. Add an anomaly-candidate table from `reports/anomaly_candidates.csv` as a separate source; relate on Date + Service without multiplying fact rows. A candidate is not a confirmed disruption or error.

Weekends are Saturday/Sunday; no holiday classification is available. Monthly patterns can reflect year-specific changes as well as seasonality. Use the fixed basket for multi-year comparisons, and show missing months as unavailable.

## Check before publishing

1. Match default 2025 totals, ranking, and shares to `reports/service_performance.csv` and `reports/mode_totals.csv`.
2. Compare monthly YoY values against `reports/monthly_service_metrics.csv`, including a missing month and a zero prior denominator.
3. Confirm changing a service filter changes the share denominator as documented.
4. Confirm a date filter preserves the prior-year rows needed by growth and the preceding rows needed by rolling calculations.
5. Check that unknown counts remain blank, no-data selections are readable, and all three dashboards fit without clipped labels.
6. Replace this status note with the actual workbook filename, screenshots, and verified Tableau Public link after publication.
