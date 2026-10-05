"""Author and execute the three notebook companions from reusable project code."""
from pathlib import Path
import asyncio
import sys
import json
import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

SETUP = """from pathlib import Path
import sys
import pandas as pd
from IPython.display import display

ROOT = Path.cwd() if (Path.cwd() / 'src').is_dir() else Path.cwd().parent
sys.path.insert(0, str(ROOT))
from src.config import RAW_PATH, OUTPUT_DIR, SERVICES, CORE_SERVICES
from src.data_cleaning import clean_data, quality_profile, reshape_data, validate_outputs
pd.set_option('display.max_rows', 16)
pd.set_option('display.max_columns', 10)
pd.set_option('display.width', 120)
"""


def notebook(filename, cells):
    document = nbf.v4.new_notebook(cells=[nbf.v4.new_markdown_cell(content) if kind == "md"
                                        else nbf.v4.new_code_cell(content) for kind, content in cells])
    document.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    document.metadata.language_info = {"name": "python", "version": "3.11"}
    nbf.validate(document)
    path = ROOT / "notebooks" / filename
    path.parent.mkdir(exist_ok=True)
    NotebookClient(document, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    # Absolute execution paths are machine-specific and not part of the analysis.
    for cell in document.cells:
        cell.metadata.pop("execution", None)
    nbf.write(document, path)
    print(f"Executed {filename}", flush=True)


def build():
    findings = json.loads((ROOT / "reports/findings.json").read_text(encoding="utf-8"))["findings"]
    notebook("01_data_ingestion_and_quality.ipynb", [
        ("md", "# Raw ridership: ingestion and quality\n\n## Summary\n2,800 daily rows, 14 services, no duplicate dates or date gaps. There are 12,193 unreported service-day cells, 290 zeros, and no negative values. Coverage differences matter more than row-level cleaning in this snapshot."),
        ("md", "## Context and methods\nThe supplied CSV is the controlling input. [Official catalogue](https://data.gov.my/data-catalogue/ridership_headline), checked 2026-10-05; its published data end date matches this snapshot. Counts represent headline rides, not unique passengers. No refresh or raw edits are made.\n\n### Assumptions\nBlank counts are unknown, not zero. A first observation is a reporting boundary, not proof of a service opening. One extract cannot establish schema history or backfills."),
        ("code", SETUP),
        ("md", "## Data\nCheck the source dimensions, schema, types and boundaries before making transformations."),
        ("code", "raw = pd.read_csv(RAW_PATH)\ndates = pd.to_datetime(raw['date'], format='%Y-%m-%d')\ndisplay(pd.Series({'rows': len(raw), 'columns': len(raw.columns), 'first_date': dates.min(), 'last_date': dates.max(), 'duplicate_rows': raw.duplicated().sum(), 'duplicate_dates': dates.duplicated().sum(), 'date_gaps': len(pd.date_range(dates.min(), dates.max()).difference(dates))}).to_frame('value'))\ndisplay(raw.dtypes.to_frame('raw_dtype'))\ndisplay(raw.head(3))"),
        ("md", "## Results\nCompare missing counts, zeros and internal gaps. Zero counts remain valid source observations, but long runs need follow-up before interpreting them as demand."),
        ("code", "profile = quality_profile(raw)\ndisplay(profile[['service_code', 'observed_days', 'missing_pct', 'zero_days', 'internal_missing_days']].round(1))"),
        ("md", "### Reporting boundaries and value ranges"),
        ("code", "display(profile[['service_code', 'first_observed', 'last_observed', 'minimum', 'maximum']])\nassert profile.negative_days.sum() == 0\nassert set(raw.columns) == {'date', *SERVICES}"),
        ("md", "### Suspicious zero runs\nThe two services below account for all source zeros. Reporting zeros and reporting blanks are kept separate."),
        ("code", "zero_ranges = []\nfor code in ['bus_rkn', 'rail_lrt_shah_alam']:\n    zero = raw[code].eq(0)\n    groups = zero.ne(zero.shift()).cumsum()\n    for _, indexes in raw[zero].groupby(groups[zero]).groups.items():\n        zero_ranges.append({'service': SERVICES[code][0], 'start': dates.loc[indexes].min(), 'end': dates.loc[indexes].max(), 'days': len(indexes)})\ndisplay(pd.DataFrame(zero_ranges).sort_values('days', ascending=False).head(10))"),
        ("md", "### Daily spikes and drops\nCompare each service with its preceding eight matching weekdays. The full criterion is documented in data/README.md. This is a screening list; counts are not deleted."),
        ("code", "from src.features import anomaly_flags\nflags = anomaly_flags(reshape_data(clean_data(raw)))\ncandidates = flags[flags.is_anomaly].sort_values('anomaly_score', key=abs, ascending=False)\ndisplay(candidates[['date', 'service', 'ridership', 'weekday_baseline', 'anomaly_score']].head(10).round(2))\nprint(f'{len(candidates):,} review candidates; no automatic removals')"),
        ("md", "## Takeaways\nThe source supports service-level demand analysis, with explicit coverage restrictions. Keep nulls and zeros intact. Use the four continuously reported rail services for long-term comparisons; require complete service-period coverage for growth. Verify zero runs and extreme dates with operator records before assigning causes. No historical schema-change claim can be made from this single snapshot.")])

    notebook("02_data_cleaning.ipynb", [
        ("md", "# Cleaning and reshaping\n\n## Summary\nThe pipeline retains 2,800 dates, creates 39,200 date-service rows, and preserves 27,007 observed counts and all nulls. The source checksum is recorded in the pipeline manifest."),
        ("md", "## Context and methods\nExact duplicate rows may be removed and counted. Conflicting date rows and invalid dates/counts stop processing. No imputation, anomaly removal, interpolation or manual edits are applied. The long form lets the same service/mode dimensions work in SQL and Tableau.\n\n### Assumptions\nThe schema is explicit: newly added services require a reviewed mapping change. Month and weekday features describe calendar dates; weekends are not a holiday proxy."),
        ("code", SETUP),
        ("md", "## Data\nInspect the source and service mapping."),
        ("code", "raw = pd.read_csv(RAW_PATH)\ndisplay(pd.DataFrame([{'service_code': code, 'service': name, 'mode': mode} for code, (name, mode) in SERVICES.items()]))"),
        ("md", "## Results\nRun the same entry point as the command-line pipeline. Outputs are reproducible; the raw file is checked for changes."),
        ("code", "from src.data_cleaning import run_pipeline\nclean, long = run_pipeline()\ndisplay(long[long.ridership.notna()].head(5))"),
        ("md", "### Prove that reshaping preserved counts\nThe validator reconstructs the full wide table, compares null positions and counts, and reconciles daily totals. A grand total alone would miss offsetting errors."),
        ("code", "validate_outputs(clean, long)\nwide_total = clean[list(SERVICES)].sum().sum()\nlong_total = long.ridership.sum()\ndisplay(pd.Series({'wide_total': wide_total, 'long_total': long_total, 'observed_cells': long.ridership.count(), 'unreported_cells': long.ridership.isna().sum(), 'duplicate_keys': long.duplicated(['date', 'service_code']).sum()}).to_frame('value'))\nassert wide_total == long_total"),
        ("md", "### Comparison features retain unavailable values\nMonthly growth requires every day in both calendar months. Initial months and zero comparison totals stay unavailable."),
        ("code", "from src.features import monthly_service_metrics\nmonthly = monthly_service_metrics(long)\ndisplay(monthly[monthly.service_code.eq('rail_lrt_shah_alam') & monthly.ridership.notna()][['year_month', 'ridership', 'observed_days', 'complete', 'mom_pct', 'yoy_pct']].round(2))"),
        ("md", "## Takeaways\nUse `python -m src.data_cleaning` to reproduce all three processed datasets. Tableau receives calendar/service fields and observation flags, leaving growth and share calculations to the workbook. Do not edit the exports by hand.")])

    eda = [
        ("md", "# Malaysian public transport demand\n\n## Summary\n" + "\n\n".join(findings[1:5])),
        ("md", "## Context and methods\nExplore demand, service contribution and temporal patterns from the supplied headline counts. Historical trends use the fixed basket: Ampang, Kajang, Kelana Jaya and Monorail. Service ranking and growth focus on 2025, the latest complete year.\n\n### Assumptions\nShares refer to reported rides, not unique travellers or national market share. Full-year growth requires complete observations in both years; 2026 is partial. Zeros are preserved but need investigation. Service reliability, capacity and journey purpose are not measured, so efficiency and causation cannot be inferred. Source: [data.gov.my](https://data.gov.my/data-catalogue/ridership_headline)."),
        ("code", SETUP + "\nimport matplotlib.pyplot as plt\nfrom src.analysis import build_analysis\nfrom src.features import daily_totals, monthly_service_metrics\nfrom IPython.display import Image\nclean = pd.read_csv(OUTPUT_DIR / 'ridership_clean.csv', parse_dates=['date'])\nlong = pd.read_csv(OUTPUT_DIR / 'ridership_long.csv', parse_dates=['date'])\nevidence = build_analysis(clean, long)\ncomparison_year = evidence['comparison_year']"),
        ("md", "## Data\nConfirm bounds and observation coverage before comparing demand."),
        ("code", "display(pd.read_csv(OUTPUT_DIR / 'quality_profile.csv')[['service_code', 'observed_days', 'missing_pct', 'zero_days']].round(1))"),
        ("md", "## Results\n### Long-term demand on a fixed basket"),
        ("code", "display(Image(filename=str(ROOT / 'images/core_trend.png')))"),
        ("md", findings[4] + " " + findings[5]),
        ("md", "### Reported totals need a coverage companion\nThe increase in measured services changes the population being summed. Use this chart for reported volume, and the basket chart for like-for-like history."),
        ("code", "display(Image(filename=str(ROOT / 'images/reported_coverage.png')))"),
        ("md", "### Which services carry the most rides?"),
        ("code", "display(Image(filename=str(ROOT / 'images/service_ranking.png')))"),
        ("md", findings[2]),
        ("code", "performance = pd.read_csv(ROOT / 'reports/service_performance.csv')\ndisplay(performance[['service', 'ridership', 'observed_days', 'share_pct', 'yoy_pct']].round(2))"),
        ("md", "### Growth and decline among comparable services"),
        ("code", "display(Image(filename=str(ROOT / 'images/service_growth.png')))"),
        ("md", findings[3] + " Kuantan's zero run limits interpretation: the decline may mix demand and reporting/operational changes. Check with the publisher before describing it as a demand loss."),
        ("md", "### Mode contribution\nThe categories are defined in src/config.py. Multiple rail categories are retained to avoid hiding different service patterns."),
        ("code", "display(Image(filename=str(ROOT / 'images/mode_totals.png')))\nmodes = pd.read_csv(ROOT / 'reports/mode_totals.csv')\nmodes['reported_share_pct'] = modes.ridership / modes.ridership.sum() * 100\ndisplay(modes.round(2))"),
        ("md", "### Weekday and weekend demand"),
        ("code", "display(Image(filename=str(ROOT / 'images/weekday_weekend.png')))"),
        ("md", findings[6] + " ETS and commuter services need their own comparisons; a network average should not dictate every service's timetable."),
        ("md", "### Monthly pattern across years\nEach cell is mean daily ridership, avoiding month-length effects. Blank cells are unavailable. Repeated patterns are a descriptive clue; annual recovery and service changes can confound seasonality."),
        ("code", "display(Image(filename=str(ROOT / 'images/monthly_patterns.png')))"),
        ("md", findings[7]),
        ("md", "### Annual comparison excludes 2026"),
        ("code", "display(Image(filename=str(ROOT / 'images/annual_core.png')))\ndisplay(pd.read_csv(ROOT / 'reports/core_annual.csv').round(2))"),
        ("md", "### Which services look consistent or volatile?\nDaily coefficient of variation describes variability relative to the mean; it mixes weekday patterns, trends and unusual days. It is not a risk score or service-reliability metric. Compare complete 2025 observations."),
        ("code", "display(performance[performance.observed_days.eq(365)][['service', 'daily_mean', 'coefficient_of_variation']].sort_values('coefficient_of_variation', ascending=False).round(3))\nmonthly = monthly_service_metrics(long)\nlatest = monthly[monthly.month_start.dt.year.eq(comparison_year)]\nconsistency = latest.groupby('service').agg(comparable_months=('yoy_pct', 'count'), positive_yoy_months=('yoy_pct', lambda s: s.gt(0).sum()), median_yoy_pct=('yoy_pct', 'median'))\ndisplay(consistency.sort_values(['positive_yoy_months', 'median_yoy_pct'], ascending=False).round(2))"),
        ("md", "Services with positive YoY in all 12 comparable months show sustained observed growth for this year. Services with small annual changes may still vary substantially month to month; avoid labelling them permanently stagnant."),
        ("md", "### Unusual observations remain in the data"),
        ("code", "display(Image(filename=str(ROOT / 'images/anomaly_candidates.png')))\nanomalies = pd.read_csv(ROOT / 'reports/anomaly_candidates.csv')\ndisplay(anomalies.head(8).round(2))"),
        ("md", findings[8] + " The rule uses eight preceding matching weekdays, a four-standard-deviation threshold and a 25% relative deviation threshold. Source records, holidays and disruption logs would be needed to distinguish real events from measurement issues."),
        ("md", "## Takeaways\n" + "\n\n".join(f"- {f}" for f in findings) + "\n\nPossible operational implication: review whether each service's capacity and frequency align with its day-type demand. Add capacity and timetable data before recommending actual schedule changes. This dataset measures usage, not punctuality, crowding or efficiency.")]
    notebook("03_exploratory_analysis.ipynb", eda)


if __name__ == "__main__":
    build()
