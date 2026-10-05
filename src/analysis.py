"""Generate the evidence tables and figures used by the EDA and README."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

from .config import CORE_SERVICES, OUTPUT_DIR, ROOT, SERVICES
from .features import anomaly_flags, daily_totals, monthly_service_metrics


def build_analysis(clean, long):
    output = ROOT / "reports"
    images = ROOT / "images"
    output.mkdir(exist_ok=True)
    images.mkdir(exist_ok=True)
    daily = daily_totals(clean)
    monthly = monthly_service_metrics(long)
    monthly.to_csv(output / "monthly_service_metrics.csv", index=False)
    daily.to_csv(output / "daily_totals.csv")
    flags = anomaly_flags(long)
    anomalies = flags[flags["is_anomaly"]].sort_values("anomaly_score", key=abs, ascending=False)
    anomalies[["date", "service", "ridership", "weekday_baseline", "anomaly_score"]].to_csv(output / "anomaly_candidates.csv", index=False)

    # Compare the latest complete calendar year with its predecessor.
    complete_years = [y for y, group in clean.groupby(clean.date.dt.year)
                      if len(group) == pd.Timestamp(y, 12, 31).dayofyear]
    year = max(y for y in complete_years if y - 1 in complete_years)
    current = long[long.year.eq(year)]
    prior = long[long.year.eq(year - 1)]
    summary = current.groupby(["service_code", "service", "mode"]).agg(
        ridership=("ridership", lambda s: s.sum(min_count=1)),
        observed_days=("ridership", "count"), daily_mean=("ridership", "mean"),
        daily_std=("ridership", "std")).reset_index()
    previous = prior.groupby("service_code").agg(prior_total=("ridership", lambda s: s.sum(min_count=1)),
                                                 prior_days=("ridership", "count"))
    summary = summary.merge(previous, on="service_code")
    eligible = summary.observed_days.eq(pd.Timestamp(year, 12, 31).dayofyear) & summary.prior_days.eq(pd.Timestamp(year - 1, 12, 31).dayofyear)
    summary["yoy_pct"] = ((summary.ridership / summary.prior_total.replace(0, float("nan"))) - 1).where(eligible) * 100
    summary["coefficient_of_variation"] = summary.daily_std / summary.daily_mean.replace(0, float("nan"))
    summary["share_pct"] = summary.ridership / summary.ridership.sum() * 100
    summary = summary.sort_values("ridership", ascending=False)
    summary.to_csv(output / "service_performance.csv", index=False)
    modes = current.groupby("mode").ridership.sum(min_count=1).sort_values(ascending=False)
    modes.to_csv(output / "mode_totals.csv")
    core = daily.core_total
    annual = core.groupby(core.index.year).agg(["sum", "mean", "count"])
    annual["expected_days"] = [pd.Timestamp(y, 12, 31).dayofyear for y in annual.index]
    annual["complete"] = annual["count"].eq(annual.expected_days)
    annual["yoy_pct"] = annual["sum"].where(annual.complete).pct_change(fill_method=None) * 100
    annual.to_csv(output / "core_annual.csv", index_label="year")
    selected_core = core[core.index.year == year]
    week = current.groupby(["service", "is_weekend"]).ridership.mean().unstack()
    week.columns = ["weekday_mean", "weekend_mean"]
    week["weekend_vs_weekday_pct"] = (week.weekend_mean / week.weekday_mean - 1) * 100
    week.to_csv(output / "weekday_weekend.csv")

    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .18, "figure.dpi": 120})
    formatter = FuncFormatter(lambda value, _: f"{value / 1e6:.1f}M" if abs(value) >= 1e6 else f"{value / 1e3:.0f}K")

    def save(fig, name):
        fig.tight_layout()
        fig.savefig(images / f"{name}.png", bbox_inches="tight")
        plt.close(fig)

    def date_axis(ax, start, end):
        ticks = list(pd.date_range(start, end, freq="YS"))
        if not ticks or ticks[0] != start:
            ticks.insert(0, start)
        if ticks[-1] != end:
            ticks.append(end)
        ax.set_xticks(ticks, [str(t.year) if t.month == 1 and t.day == 1 else t.strftime("%Y-%m") for t in ticks])
        ax.set_xlim(start, end)

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(daily.index, core.astype(float), color="#b9c4ce", linewidth=.5, label="Daily count")
    ax.plot(daily.index, daily.core_rolling_30d, color="#285c7f", linewidth=1.6, label="30-day average")
    ax.set(title="Four continuously reported rail services: daily ridership", ylabel="Headline rides", xlabel="Date")
    date_axis(ax, daily.index.min(), daily.index.max())
    ax.yaxis.set_major_formatter(formatter)
    ax.legend(frameon=False)
    save(fig, "core_trend")

    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    axes[0].plot(daily.index, daily.reported_total, color="#285c7f", linewidth=.6)
    axes[0].set(title="Reported totals expand as service coverage changes", ylabel="Reported rides")
    axes[0].yaxis.set_major_formatter(formatter)
    axes[1].step(daily.index, daily.observed_services, color="#6c7553", where="mid")
    axes[1].set(ylabel="Observed services", xlabel="Date", ylim=(0, len(SERVICES) + 1))
    date_axis(axes[1], daily.index.min(), daily.index.max())
    save(fig, "reported_coverage")

    ranked = summary[summary.observed_days.gt(0)].sort_values("ridership")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(ranked.service, ranked.ridership.astype(float), color="#285c7f")
    ax.set(title=f"{year}: MRT Kajang carries the largest reported service total", xlabel="Headline rides")
    ax.xaxis.set_major_formatter(formatter)
    save(fig, "service_ranking")

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.barh(modes.index[::-1], modes.values[::-1].astype(float), color="#285c7f")
    ax.set(title=f"{year}: mode totals within the reported dataset", xlabel="Headline rides")
    ax.xaxis.set_major_formatter(formatter)
    save(fig, "mode_totals")

    growth = summary.dropna(subset=["yoy_pct"]).sort_values("yoy_pct")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(growth.service, growth.yoy_pct.astype(float), color=["#b58346" if v < 0 else "#285c7f" for v in growth.yoy_pct])
    ax.axvline(0, color="#555555", linewidth=.8)
    ax.set(title=f"{year} vs {year - 1}: growth for services with full-year observations", xlabel="Change in annual rides (%)")
    save(fig, "service_growth")

    fig, ax = plt.subplots(figsize=(10, 6))
    week = week.reindex(ranked.service).dropna()
    positions = range(len(week))
    ax.barh([p - .18 for p in positions], week.weekday_mean, height=.36, color="#285c7f", label="Weekday")
    ax.barh([p + .18 for p in positions], week.weekend_mean, height=.36, color="#b58346", label="Weekend")
    ax.set_yticks(list(positions), week.index)
    ax.set(title=f"{year}: weekday and weekend demand by service", xlabel="Average daily rides")
    ax.xaxis.set_major_formatter(formatter)
    ax.legend(frameon=False)
    save(fig, "weekday_weekend")

    matrix = core.groupby([core.index.year, core.index.month]).mean().unstack().astype(float)
    fig, ax = plt.subplots(figsize=(10, 4))
    heat = ax.imshow(matrix.to_numpy() / 1000, aspect="auto", cmap="Blues")
    ax.set_yticks(range(len(matrix)), matrix.index)
    ax.set_xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.grid(False)
    ax.set(title="Monthly average daily rides: fixed four-service rail basket", xlabel="Month", ylabel="Year")
    fig.colorbar(heat, ax=ax, label="Average daily rides (K)")
    save(fig, "monthly_patterns")

    full = annual[annual.complete]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(full.index.astype(str), full["sum"].astype(float), color="#285c7f")
    ax.set(title="Annual ridership for the fixed four-service rail basket", xlabel="Complete calendar year", ylabel="Headline rides")
    ax.yaxis.set_major_formatter(formatter)
    save(fig, "annual_core")

    fig, ax = plt.subplots(figsize=(10, 4))
    kajang = flags[flags.service_code.eq("rail_mrt_kajang") & flags.year.eq(year)]
    ax.plot(kajang.date, kajang.ridership.astype(float), color="#285c7f", linewidth=.8)
    candidates = kajang[kajang.is_anomaly]
    ax.scatter(candidates.date, candidates.ridership.astype(float), facecolors="none", edgecolors="#b58346", label="Review candidate", s=32)
    ax.set(title=f"{year}: MRT Kajang daily counts and anomaly candidates", ylabel="Headline rides", xlabel="Date")
    ax.yaxis.set_major_formatter(formatter)
    ax.legend(frameon=False)
    ax.set_xlim(kajang.date.min(), kajang.date.max())
    save(fig, "anomaly_candidates")

    leader = summary.iloc[0]
    fastest = growth.iloc[-1]
    slowest = growth.iloc[0]
    weekend_gap = (selected_core[selected_core.index.dayofweek >= 5].mean() / selected_core[selected_core.index.dayofweek < 5].mean() - 1) * 100
    all_current = current.ridership.sum()
    min_year = full["sum"].idxmin()
    month_means = selected_core.groupby(selected_core.index.month).mean()
    facts = [
        f"The snapshot spans {len(clean):,} consecutive dates ({clean.date.min().date()} to {clean.date.max().date()}) and {len(SERVICES)} services; {long.ridership.isna().sum():,} of {len(long):,} date-service cells are unreported.",
        f"In {year}, reported services sum to {all_current:,.0f} headline rides. This is an observed-service total, not a count of unique passengers or all Malaysian public transport.",
        f"{leader.service} records {leader.ridership:,.0f} rides in {year}, accounting for {leader.share_pct:.1f}% of reported rides and ranking first.",
        f"Among full-year comparable services, {fastest.service} has the largest {year} annual increase ({fastest.yoy_pct:+.1f}%); {slowest.service} has the weakest change ({slowest.yoy_pct:+.1f}%).",
        f"The fixed four-service rail basket totals {full.loc[year, 'sum']:,.0f} rides in {year}, {full.loc[year, 'yoy_pct']:+.1f}% against {year - 1} and {(full.loc[year, 'sum'] / full.loc[2019, 'sum'] - 1) * 100:+.1f}% against 2019.",
        f"The basket's lowest full-year total is {full.loc[min_year, 'sum']:,.0f} in {min_year}; the data identifies the drop but does not establish its cause.",
        f"In {year}, basket weekend daily ridership averages {weekend_gap:.1f}% relative to weekdays. Commuting is a plausible interpretation; journey purpose is not observed.",
        f"In {year}, the basket's highest monthly daily average occurs in month {month_means.idxmax()} ({month_means.max():,.0f} rides/day); its lowest occurs in month {month_means.idxmin()} ({month_means.min():,.0f}). This describes one year rather than proving recurring seasonality.",
        f"Across the snapshot, {len(anomalies):,} date-service observations meet the documented anomaly review rule; all remain in the analytical data. These flags are screening candidates, not confirmed errors.",
    ]
    consistency = monthly[monthly.month_start.dt.year.eq(year)].groupby("service").yoy_pct.agg(
        comparable_months="count", positive_months=lambda s: s.gt(0).sum())
    steady = consistency[(consistency.comparable_months == 12) & (consistency.positive_months == 12)].index.tolist()
    facts.append(f"In {year}, {len(steady)} services have positive YoY growth in all 12 comparable months: {', '.join(steady)}. This describes sustained observed growth over this year, not a forecast.")
    evidence = {"comparison_year": int(year), "findings": facts, "figures": [p.name for p in sorted(images.glob('*.png'))]}
    (output / "findings.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (output / "findings.md").write_text("# Observations from the supplied snapshot\n\n" + "\n\n".join(f"- {f}" for f in facts) + "\n\nOperational implication: compare staffing and capacity with each service's weekday/weekend demand, then add service frequency and capacity data before judging efficiency. Investigate zero runs and flagged dates with operator records before assigning causes.\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    clean = pd.read_csv(OUTPUT_DIR / "ridership_clean.csv", parse_dates=["date"])
    long = pd.read_csv(OUTPUT_DIR / "ridership_long.csv", parse_dates=["date"])
    print("\n".join(build_analysis(clean, long)["findings"]))
