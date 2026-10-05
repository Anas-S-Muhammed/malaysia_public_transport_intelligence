"""Preserve source counts and unknowns; reject ambiguous input rather than repair it silently."""
import hashlib
import json

import pandas as pd

from .config import OUTPUT_DIR, RAW_PATH, SERVICES, SOURCE_URL


def clean_data(raw):
    expected = {"date", *SERVICES}
    if set(raw.columns) != expected:
        raise ValueError(f"Schema mismatch: missing={expected - set(raw.columns)}, unexpected={set(raw.columns) - expected}")
    if raw.empty:
        raise ValueError("Raw dataset is empty")
    clean = raw.copy()
    clean["date"] = pd.to_datetime(clean["date"], format="%Y-%m-%d", errors="raise")
    if clean["date"].isna().any():
        raise ValueError("Missing date")
    exact_duplicates = int(clean.duplicated().sum())
    clean = clean.drop_duplicates()
    if clean["date"].duplicated().any():
        raise ValueError("Conflicting records for the same date; inspect the raw file")
    for service in SERVICES:
        values = pd.to_numeric(clean[service], errors="raise")
        if (values.notna() & ((values < 0) | (values % 1 != 0))).any():
            raise ValueError(f"Negative or non-integer ridership in {service}")
        clean[service] = values.astype("Int64")
    clean = clean.sort_values("date").reset_index(drop=True)
    clean.attrs["exact_duplicates_removed"] = exact_duplicates
    return clean


def quality_profile(raw):
    dates = pd.to_datetime(raw["date"], errors="raise")
    rows = []
    for service in SERVICES:
        values = pd.to_numeric(raw[service], errors="raise")
        observed = dates[values.notna()]
        first, last = observed.min(), observed.max()
        inside = dates.between(first, last) if len(observed) else pd.Series(False, index=raw.index)
        rows.append({"service_code": service, "observed_days": int(values.count()),
                     "missing_days": int(values.isna().sum()), "missing_pct": values.isna().mean() * 100,
                     "zero_days": int(values.eq(0).sum()), "negative_days": int(values.lt(0).sum()),
                     "first_observed": first, "last_observed": last,
                     "internal_missing_days": int((inside & values.isna()).sum()),
                     "minimum": values.min(), "maximum": values.max()})
    return pd.DataFrame(rows)


def reshape_data(clean):
    long = clean.melt(id_vars="date", var_name="service_code", value_name="ridership")
    long["ridership"] = long["ridership"].astype("Int64")
    long["service"] = long["service_code"].map({k: v[0] for k, v in SERVICES.items()})
    long["mode"] = long["service_code"].map({k: v[1] for k, v in SERVICES.items()})
    long["is_observed"] = long["ridership"].notna()
    date = long["date"].dt
    for name, values in {"year": date.year, "quarter": date.quarter,
                         "month": date.month_name(), "month_number": date.month,
                         "year_month": date.strftime("%Y-%m"), "iso_year": date.isocalendar().year,
                         "iso_week": date.isocalendar().week, "day": date.day,
                         "day_of_week": date.day_name(), "day_of_week_number": date.dayofweek,
                         "is_weekend": date.dayofweek >= 5}.items():
        long[name] = values
    return long.sort_values(["service_code", "date"]).reset_index(drop=True)


def validate_outputs(clean, long):
    if clean.empty or long.empty:
        raise ValueError("Processed output is empty")
    required = {"date", "service_code", "service", "mode", "ridership", "is_observed"}
    if not required.issubset(long.columns):
        raise ValueError("Required long fields are missing")
    if long.duplicated(["date", "service_code"]).any() or long["service"].isna().any():
        raise ValueError("Invalid date-service key or service name")
    if long["ridership"].lt(0).any():
        raise ValueError("Negative processed count")
    if len(long) != len(clean) * len(SERVICES):
        raise ValueError("Reshape changed the expected number of observations")
    if long["date"].min() != clean["date"].min() or long["date"].max() != clean["date"].max():
        raise ValueError("Date bounds changed")
    restored = long.pivot(index="date", columns="service_code", values="ridership")
    pd.testing.assert_frame_equal(clean.set_index("date")[list(SERVICES)],
                                  restored[list(SERVICES)].astype("Int64"), check_names=False)
    before = clean.set_index("date")[list(SERVICES)].sum(axis=1, min_count=1)
    after = long.groupby("date")["ridership"].sum(min_count=1)
    pd.testing.assert_series_equal(before, after, check_names=False)


def run_pipeline(raw_path=RAW_PATH, output_dir=OUTPUT_DIR):
    if not raw_path.exists():
        raise FileNotFoundError(f"Expected raw dataset at {raw_path}")
    source_bytes = raw_path.read_bytes()
    raw = pd.read_csv(raw_path)
    clean = clean_data(raw)
    long = reshape_data(clean)
    validate_outputs(clean, long)
    output_dir.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output_dir / "ridership_clean.csv", index=False)
    long.to_csv(output_dir / "ridership_long.csv", index=False)
    long.to_csv(output_dir / "tableau_ridership.csv", index=False)
    quality_profile(raw).to_csv(output_dir / "quality_profile.csv", index=False)
    dates = clean["date"]
    manifest = {"source": SOURCE_URL, "raw_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "raw_rows": len(raw), "clean_rows": len(clean), "long_rows": len(long),
                "date_min": str(dates.min().date()), "date_max": str(dates.max().date()),
                "date_gaps": len(pd.date_range(dates.min(), dates.max()).difference(dates)),
                "exact_duplicates_removed": clean.attrs["exact_duplicates_removed"],
                "observed_cells": int(long["ridership"].count()),
                "ridership_sum": int(long["ridership"].sum()),
                "policy": "Nulls and zeros preserved; conflicts, invalid dates/counts and schema changes rejected."}
    (output_dir / "pipeline_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if raw_path.read_bytes() != source_bytes:
        raise RuntimeError("Raw file changed during processing")
    print(json.dumps(manifest, indent=2))
    return clean, long


if __name__ == "__main__":
    run_pipeline()
