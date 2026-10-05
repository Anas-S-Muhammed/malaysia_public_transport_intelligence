-- Run from the repository root, after python -m src.data_cleaning.
CREATE OR REPLACE TABLE ridership AS
SELECT * FROM read_csv('data/processed/ridership_long.csv', header = true,
    types = {'date': 'DATE', 'ridership': 'BIGINT', 'is_observed': 'BOOLEAN', 'is_weekend': 'BOOLEAN'});

CREATE OR REPLACE VIEW monthly_service AS
SELECT service_code, service, mode, date_trunc('month', date)::DATE AS month,
       sum(ridership) AS rides, count(ridership) AS observed_days,
       day(last_day(date_trunc('month', date))) AS expected_days,
       count(ridership) = day(last_day(date_trunc('month', date))) AS complete
FROM ridership
GROUP BY service_code, service, mode, date_trunc('month', date);

CREATE OR REPLACE VIEW core_daily AS
SELECT date, CASE WHEN count(ridership) = 4 THEN sum(ridership) END AS rides
FROM ridership
WHERE service_code IN ('rail_lrt_ampang', 'rail_mrt_kajang', 'rail_lrt_kj', 'rail_monorail')
GROUP BY date;
