# Data notes

## Source snapshot

`raw/ridership_headline.csv` is the user-supplied daily headline ridership extract from [data.gov.my](https://data.gov.my/data-catalogue/ridership_headline), supplied by Prasarana Malaysia and the Ministry of Transport. The catalogue was checked on 2026-10-05 and lists data through 2026-08-31, matching this snapshot. The original download timestamp was not supplied. See `processed/pipeline_manifest.json` for the raw SHA-256 and bounds; the pipeline never downloads or edits raw data.

The publisher describes audited ticketing-system headline totals and monthly updates. Rides are not unique passengers, station flows, occupancy, reliability, or service efficiency. The Prasarana headline attribution cannot be reconstructed by simply summing origin-destination records. Source data is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); repository code licensing does not replace that attribution requirement.

## Transformations

The raw table has one date row and 14 service columns. Dates are parsed strictly; service columns use nullable integer counts. Exact duplicate rows are removed and counted in the manifest, while conflicting dates, unexpected schemas, invalid dates, nonnumeric counts, fractional counts and negative counts fail clearly. Missing counts and genuine source zeros remain unchanged. Service names/mode mappings are visible in `src/config.py`.

Date gaps are profiled rather than filled with assumed ridership. The wide-to-long conversion retains every date-service cell, including nulls, and validates the reconstructed wide table and daily totals. Initial reporting dates are not treated as confirmed opening dates. A single snapshot cannot establish historical schema revisions or backfills.

## Outputs

| File | Grain and purpose |
|---|---|
| `processed/ridership_clean.csv` | Sorted date rows, original service codes/counts |
| `processed/ridership_long.csv` | Date-service rows with names, mode and calendar fields |
| `processed/tableau_ridership.csv` | Same validated grain, intended for Tableau import |
| `processed/quality_profile.csv` | Service-level observation, null, zero and range checks |
| `processed/pipeline_manifest.json` | Input checksum, bounds, record/count reconciliation metadata |

Long fields: `date` (local calendar date), `service_code` (source identifier), `service` (display label), `mode` (analytical category), `ridership` (nullable ride count), `is_observed` (non-null count), `year`, `quarter` (1–4), `month` (English name), `month_number` (1–12), `year_month` (YYYY-MM), `iso_year`, `iso_week`, `day` (day of month), `day_of_week`, `day_of_week_number` (Monday=0), and `is_weekend` (Saturday/Sunday). These are not public-holiday fields.

## Coverage decisions

There are 2,800 dates and 39,200 possible date-service cells; 27,007 are observed. Four services cover the entire extract and define the long-term basket: LRT Ampang, MRT Kajang, LRT Kelana Jaya and KL Monorail. Other services begin reporting later or have gaps; see the profile for exact ranges.

Shah Alam has 94 observed days and 2,706 nulls, including 59 missing days between its first and last observations. Kuantan has a continuous 260-day zero run from 2025-12-15 through 2026-08-31; Shah Alam reports zeros on all 30 days of April 2026. These require source/operator follow-up before interpretation; the project does not convert them to nulls or claim a closure. `internal_missing_days` counts nulls between first and last observed dates, and distinguishes reporting gaps from missing tails.

Reported totals sum available counts with a non-null minimum of one. Coverage counts accompany them. Complete monthly growth requires every calendar day observed in both service-months; annual comparisons require complete calendar years. Zero comparison denominators produce unavailable growth. 2026 is partial and excluded from full-year ranking/growth. Shares describe the reported dataset, not national transport market share.

## Analytical exports

`reports/` contains daily basket/reported totals, monthly service growth, complete-year service comparisons, mode totals, weekday/weekend averages and anomaly candidates. Anomalies use the preceding eight observations on the same weekday: absolute z-score >= 4 **and** absolute relative deviation >= 25%, with all eight observations required and a nonzero standard deviation/baseline. This screening rule is sensitive to trend changes and holidays; it does not establish causation or statistical significance. No candidates are removed.
