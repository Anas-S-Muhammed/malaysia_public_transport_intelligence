-- Every violation query should return no rows.
SELECT date, service_code, count(*) AS records
FROM ridership GROUP BY date, service_code HAVING count(*) <> 1;

SELECT date, service_code, ridership FROM ridership
WHERE ridership < 0 OR service IS NULL OR date IS NULL
   OR is_observed <> (ridership IS NOT NULL);

-- Coverage and zero counts are diagnostics, not violations.
SELECT service, count(*) AS calendar_days, count(ridership) AS observed_days,
       count(*) FILTER (WHERE ridership = 0) AS zero_days,
       min(date) FILTER (WHERE ridership IS NOT NULL) AS first_observed,
       max(date) FILTER (WHERE ridership IS NOT NULL) AS last_observed
FROM ridership GROUP BY service ORDER BY observed_days, service;

-- Detect absent calendar days (missing service cells remain explicit in the table).
WITH dates AS (SELECT DISTINCT date FROM ridership),
gaps AS (SELECT date, lead(date) OVER (ORDER BY date) AS next_date FROM dates)
SELECT * FROM gaps WHERE next_date > date + INTERVAL '1 day';

-- Daily wide/long reconciliation: no rows expected.
WITH raw_totals AS (
    SELECT date::DATE AS date,
           coalesce(bus_rkl, 0) + coalesce(bus_rkn, 0) + coalesce(bus_rpn, 0)
           + rail_lrt_ampang + rail_mrt_kajang + rail_lrt_kj + rail_monorail
           + coalesce(rail_mrt_pjy, 0) + coalesce(rail_lrt_shah_alam, 0)
           + coalesce(rail_ets, 0) + coalesce(rail_intercity, 0)
           + coalesce(rail_komuter_utara, 0) + coalesce(rail_tebrau, 0)
           + coalesce(rail_komuter, 0) AS rides
    FROM read_csv_auto('data/raw/ridership_headline.csv')
), long_totals AS (SELECT date, sum(ridership) AS rides FROM ridership GROUP BY date)
SELECT raw_totals.date, raw_totals.rides, long_totals.rides
FROM raw_totals FULL OUTER JOIN long_totals USING (date)
WHERE raw_totals.rides IS DISTINCT FROM long_totals.rides;
