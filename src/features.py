import pandas as pd

from .config import CORE_SERVICES, SERVICES


def daily_totals(clean):
    values = clean.set_index("date")[list(SERVICES)]
    daily = pd.DataFrame({"reported_total": values.sum(axis=1, min_count=1),
                          "observed_services": values.count(axis=1),
                          "core_total": values[CORE_SERVICES].sum(axis=1, min_count=len(CORE_SERVICES))})
    # Calendar reindexing prevents row windows from masquerading as day windows.
    daily = daily.reindex(pd.date_range(daily.index.min(), daily.index.max(), name="date"))
    for window in (7, 30):
        daily[f"core_rolling_{window}d"] = daily["core_total"].rolling(window, min_periods=window).mean()
    return daily


def monthly_service_metrics(long):
    monthly = long.groupby(["service_code", "service", "mode", "year_month"], observed=True).agg(
        ridership=("ridership", lambda s: s.sum(min_count=1)), observed_days=("ridership", "count")
    ).reset_index()
    monthly["month_start"] = pd.to_datetime(monthly["year_month"] + "-01")
    monthly["expected_days"] = monthly["month_start"].dt.days_in_month
    monthly["complete"] = monthly["observed_days"].eq(monthly["expected_days"])
    monthly["comparable_total"] = monthly["ridership"].where(monthly["complete"])
    previous = monthly[["service_code", "month_start", "comparable_total"]].copy()
    for months, name in ((1, "mom_pct"), (12, "yoy_pct")):
        shifted = previous.rename(columns={"comparable_total": "previous_total"})
        shifted["month_start"] += pd.DateOffset(months=months)
        comparison = monthly.merge(shifted, on=["service_code", "month_start"], how="left")
        monthly[name] = ((comparison["comparable_total"] / comparison["previous_total"].replace(0, float("nan"))) - 1) * 100
    monthly["service_rank"] = monthly.groupby("year_month")["comparable_total"].rank(method="dense", ascending=False)
    return monthly


def anomaly_flags(long):
    parts = []
    for _, service in long.groupby("service_code", sort=False):
        series = service.set_index("date")["ridership"].astype(float).asfreq("D")
        # Compare with the preceding eight matching weekdays; never use future data.
        baseline = pd.concat([series.shift(7 * lag) for lag in range(1, 9)], axis=1)
        mean = baseline.mean(axis=1).where(baseline.count(axis=1).eq(8))
        std = baseline.std(axis=1).where(baseline.count(axis=1).eq(8))
        score = (series - mean) / std.replace(0, float("nan"))
        result = service.set_index("date").copy()
        result["weekday_baseline"] = mean
        result["anomaly_score"] = score
        result["is_anomaly"] = score.abs().ge(4) & ((series - mean).abs() / mean.replace(0, float("nan"))).ge(0.25)
        parts.append(result.reset_index())
    return pd.concat(parts, ignore_index=True)
