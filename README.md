# Malaysia Public Transport Intelligence

A demand analysis of Malaysia's daily headline public transport ridership, built from the supplied official open-data snapshot. The project follows the data from quality checks through reproducible cleaning, Python analysis, DuckDB SQL and a Tableau-ready export.

The central analytical problem is changing coverage: a rising sum can reflect newly reported services as well as increased demand. Long-term comparisons therefore use four rail services observed throughout the extract. Service comparisons use complete calendar periods.

## Data and scope

The raw CSV covers **2019-01-01 to 2026-08-31**, with **2,800 dates and 14 services**. It has no duplicate dates, missing calendar dates or negative counts. Of 39,200 date-service cells, 12,193 are unreported. Services enter the extract at different times, and Shah Alam has internal reporting gaps. Counts describe headline rides, not unique passengers, all Malaysian transport, punctuality or efficiency.

See [data notes](data/README.md) for the source, field definitions, licensing and coverage decisions. The input is preserved unchanged; its SHA-256 is recorded in the [pipeline manifest](data/processed/pipeline_manifest.json).

## Findings

The latest complete calendar year is 2025; 2026 is excluded from full-year growth comparisons.

- Reported services recorded **451,121,402 rides in 2025**. MRT Kajang led with **92,737,532**, or **20.6%** of the reported total.
- Among services observed throughout both years, MRT Putrajaya grew fastest: **15.7%** from 2024. KTM Komuter declined **17.5%**. Kuantan declined **18.8%**, but its source zero run needs investigation before interpreting that change as lost demand.
- The fixed basket—LRT Ampang, MRT Kajang, LRT Kelana Jaya and KL Monorail—recorded **274,490,644 rides**, up **8.4%** from 2024 and **16.2%** from 2019. Its lowest full-year total was **70,861,926 in 2021**; this analysis does not establish the cause.
- Basket weekend daily demand averaged **33.9% below weekdays** in 2025. Commuting is a plausible explanation, but journey purpose is not recorded.
- LRT contributed **160,651,902 rides**, versus **148,407,596 for MRT** and **96,186,015 for buses** in 2025. These categories refer to this dataset's reported services.
- Six services had positive YoY growth in all **12 comparable months of 2025**: Ampang, Kajang, Putrajaya, Monorail, Komuter Utara and Rapid Bus Penang. KTM Komuter and Kuantan had no positive YoY months.
- KTM Intercity had the highest daily coefficient of variation among fully observed 2025 services (**0.353**); Rapid Bus Penang had the lowest (**0.068**). This measures daily demand variation, including calendar effects, rather than service reliability.
- Basket average daily ridership peaked in **July 2025 at 798,960** and was lowest in **March at 700,174**. A single year's pattern does not prove recurring seasonality.
- **684 service-day observations** meet the anomaly screening rule. They remain in the data; none are presented as confirmed errors or disruptions.

![Daily ridership for the continuously reported rail basket](images/core_trend.png)

![Complete-year service growth](images/service_growth.png)

The weekday/weekend differences justify checking service-specific capacity and timetable alignment. Actual schedule recommendations need frequency, capacity and crowding data. Zero runs and anomaly candidates need operator/source follow-up before assigning causes.

## Repository guide

| Location | Purpose |
|---|---|
| `src/data_cleaning.py` | Strict parsing, conservative cleaning, reshaping and reconciliation |
| `src/features.py` | Coverage-aware totals, rolling means, monthly growth and anomaly screening |
| `src/analysis.py` | Reproducible evidence tables, figures and findings |
| `notebooks/01_data_ingestion_and_quality.ipynb` | Raw schema, coverage, zeros and unusual observations |
| `notebooks/02_data_cleaning.ipynb` | Pipeline decisions and wide/long reconciliation |
| `notebooks/03_exploratory_analysis.ipynb` | Trends, rankings, modes, growth, day types, seasonality and variability |
| `sql/` | DuckDB schema, quality checks and seven analytical queries |
| `reports/` | Inspectable calculated results and SQL exports |
| `tableau/` | Dashboard specification, KPI definitions and calculation instructions |
| `tests/` | Failure cases, null/zero preservation, calendar windows and source reconciliation |

Notebooks have saved outputs and run from top to bottom. SQL demonstrates aggregation, CASE, calendar joins, CTEs, LAG, LEAD, DENSE_RANK and moving windows for the same analytical questions. DuckDB provides a local SQL layer without a database server.

## Reproduce

Python 3.10+ is required; the completed run used Python 3.11. From this project directory:

```bash
python -m venv .venv
```

Activate it with `.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` on macOS/Linux, then run:

```bash
python -m pip install -r requirements.txt
python -m src.data_cleaning
python -m src.analysis
python -m src.sql_analysis
python -m pytest -q
python scripts/build_notebooks.py
```

The final command rebuilds and executes the three notebooks. Alternatively, open them with `jupyter lab` and run all cells in order. Paths resolve from the repository or notebook directory; no machine-specific source paths are required. SQL reads relative CSV paths, and its runner sets the project directory automatically. The pipeline does not refresh the official dataset: to analyse a new snapshot, deliberately replace the raw input and rerun the checks. New service columns require updating the reviewed mapping.

Dependencies use bounded version ranges rather than a fully locked environment. They are listed in [requirements.txt](requirements.txt). No external credentials, cloud services or database server are needed.

## Tableau status

The [Tableau export](data/processed/tableau_ridership.csv), [three-dashboard specification](tableau/README.md) and [calculated fields](tableau/calculated_fields.md) are ready. **No Tableau workbook or Tableau Public dashboard has been created.** Build and validate the workbook manually; add real screenshots and a verified public link here when it is available.

## Validation and limitations

The pipeline reconstructs the full wide table from long rows, including null positions, and verifies daily totals. Tests cover corrupted counts, conflicting duplicates, invalid dates/schema, zero denominators, incomplete comparisons and calendar gaps. SQL checks independently reconcile every raw daily sum and verify keys, domains and date continuity. The raw snapshot remains unchanged.

Anomaly flags compare counts with the preceding eight matching weekdays and require both an absolute z-score of at least 4 and an absolute deviation of at least 25%. This is an exploratory screening rule, sensitive to holidays and trends. Neither flags nor coincident changes establish a cause. No public-holiday, station, origin-destination, timetable, capacity or disruption data is included.

## Attribution and license

Data: [Daily Public Transport Ridership, data.gov.my](https://data.gov.my/data-catalogue/ridership_headline), from Prasarana Malaysia and the Ministry of Transport, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The catalogue was checked on 2026-10-05; the supplied snapshot ends on 2026-08-31. Code is licensed under [MIT](LICENSE). This is an independent portfolio project.
