-- Annual service ranking: totals require a complete observed year.
WITH annual AS (
    SELECT year(date) AS year, service, mode, sum(ridership) AS rides,
           count(ridership) AS observed_days
    FROM ridership GROUP BY year(date), service, mode
), complete AS (
    SELECT * FROM annual
    WHERE observed_days = date_diff('day', make_date(year, 1, 1), make_date(year + 1, 1, 1))
)
SELECT *, dense_rank() OVER (PARTITION BY year ORDER BY rides DESC) AS service_rank
FROM complete ORDER BY year, service_rank;

-- Monthly reported total alongside changing coverage.
SELECT month, sum(rides) AS reported_rides,
       count(*) FILTER (WHERE complete) AS fully_observed_services,
       sum(observed_days) AS observed_service_days
FROM monthly_service GROUP BY month ORDER BY month;

-- Exact calendar joins avoid treating an absent month as the previous period.
SELECT current.month, current.service, current.rides,
       100.0 * (current.rides / nullif(previous.rides, 0) - 1) AS yoy_pct,
       100.0 * (current.rides / nullif(last_month.rides, 0) - 1) AS mom_pct
FROM monthly_service current
LEFT JOIN monthly_service previous
    ON current.service_code = previous.service_code
   AND current.month = previous.month + INTERVAL '1 year' AND previous.complete
LEFT JOIN monthly_service last_month
    ON current.service_code = last_month.service_code
   AND current.month = last_month.month + INTERVAL '1 month' AND last_month.complete
WHERE current.complete ORDER BY current.month, current.service;

-- Fixed basket annual growth, excluding partial years before computing lag.
WITH annual AS (
    SELECT year(date) AS year, sum(rides) AS rides, count(rides) AS days
    FROM core_daily GROUP BY year(date)
), full_years AS (
    SELECT * FROM annual
    WHERE days = date_diff('day', make_date(year, 1, 1), make_date(year + 1, 1, 1))
), comparisons AS (
    SELECT *, lag(year) OVER (ORDER BY year) AS previous_year,
           lag(rides) OVER (ORDER BY year) AS previous_rides FROM full_years
)
SELECT *, CASE WHEN year = previous_year + 1
    THEN 100.0 * (rides / nullif(previous_rides, 0) - 1) END AS yoy_pct
FROM comparisons ORDER BY year;

-- Calendar range window; unavailable initial/gapped windows remain null.
SELECT date, rides,
       CASE WHEN count(rides) OVER moving = 30 THEN avg(rides) OVER moving END AS rolling_30d
FROM core_daily
WINDOW moving AS (ORDER BY date RANGE BETWEEN INTERVAL '29 days' PRECEDING AND CURRENT ROW)
ORDER BY date;

-- Complete latest year only; shares mean contribution to reported rides.
WITH latest AS (
    SELECT max(year) AS year FROM (
        SELECT year(date) AS year FROM core_daily GROUP BY year(date)
        HAVING count(rides) = date_diff('day', make_date(year(date), 1, 1), make_date(year(date) + 1, 1, 1))
    )
), mode_totals AS (
    SELECT mode, sum(ridership) AS rides FROM ridership, latest
    WHERE year(date) = latest.year GROUP BY mode
)
SELECT *, 100.0 * rides / sum(rides) OVER () AS reported_share_pct
FROM mode_totals ORDER BY rides DESC;

SELECT year(date) AS year, service,
       CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS week_type,
       avg(ridership) AS average_daily_rides, count(ridership) AS observed_days
FROM ridership GROUP BY year(date), service, week_type ORDER BY year, service, week_type;
