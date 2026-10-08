import pandas as pd
import pytest

from src.config import RAW_PATH, SERVICES
from src.data_cleaning import clean_data, reshape_data, validate_outputs
from src.features import daily_totals, monthly_service_metrics


@pytest.fixture
def raw():
    return pd.DataFrame({"date": ["2024-01-02", "2024-01-01"],
                         **{code: [12, None] for code in SERVICES}})


def test_preserves_missing_zero_and_all_values(raw):
    raw.loc[0, "bus_rkn"] = 0
    clean = clean_data(raw)
    long = reshape_data(clean)
    validate_outputs(clean, long)
    assert long.ridership.isna().sum() == len(SERVICES)
    assert (long.ridership == 0).sum() == 1
    assert long.ridership.sum() == 12 * (len(SERVICES) - 1)


def test_exact_duplicates_removed_but_conflicts_rejected(raw):
    assert len(clean_data(pd.concat([raw, raw.iloc[[0]]]))) == 2
    conflict = raw.iloc[[0]].copy()
    conflict["bus_rkl"] = 99
    with pytest.raises(ValueError, match="Conflicting"):
        clean_data(pd.concat([raw, conflict]))


@pytest.mark.parametrize("value", [-1, 1.5, "unknown"])
def test_invalid_counts_rejected(raw, value):
    raw["bus_rkl"] = raw.bus_rkl.astype(object)
    raw.loc[0, "bus_rkl"] = value
    with pytest.raises(ValueError):
        clean_data(raw)


def test_invalid_date_and_schema_rejected(raw):
    with pytest.raises(ValueError, match="Schema"):
        clean_data(raw.drop(columns="bus_rkl"))
    raw.loc[0, "date"] = "2024-02-30"
    with pytest.raises(ValueError):
        clean_data(raw)


def test_tampered_reshape_detected(raw):
    clean = clean_data(raw)
    long = reshape_data(clean)
    long.loc[long.ridership.notna(), "ridership"] += 1
    with pytest.raises(AssertionError):
        validate_outputs(clean, long)


@pytest.mark.parametrize("observed,value", [(False, True), (True, False), (False, None)])
def test_invalid_observation_flag_rejected(raw, observed, value):
    clean = clean_data(raw)
    long = reshape_data(clean)
    long["is_observed"] = long["is_observed"].astype(object)
    long.loc[long.ridership.notna().eq(observed), "is_observed"] = value
    with pytest.raises(ValueError, match="Observation flags"):
        validate_outputs(clean, long)


@pytest.mark.parametrize("field,value", [("service", "Wrong service"), ("mode", "Wrong mode"), ("mode", None)])
def test_invalid_service_mapping_rejected(raw, field, value):
    clean = clean_data(raw)
    long = reshape_data(clean)
    long.loc[0, field] = value
    with pytest.raises(ValueError, match=f"Invalid {field} mapping"):
        validate_outputs(clean, long)


def test_rolling_calendar_gap_and_early_windows():
    dates = pd.date_range("2024-01-01", periods=40).delete(15)
    raw = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), **{c: 10 for c in SERVICES}})
    daily = daily_totals(clean_data(raw))
    assert pd.isna(daily.loc["2024-01-16", "core_total"])
    assert daily.core_rolling_30d.isna().all()
    assert daily.core_rolling_7d.iloc[6] == 40


def test_missing_comparison_and_zero_base_are_not_growth():
    dates = pd.date_range("2024-01-01", "2024-03-31")
    raw = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), **{c: 0 for c in SERVICES}})
    raw.loc[dates.month == 3, list(SERVICES)] = 10
    raw.loc[dates == "2024-02-10", "bus_rkl"] = None
    monthly = monthly_service_metrics(reshape_data(clean_data(raw)))
    assert monthly.yoy_pct.isna().all()
    assert monthly.mom_pct.isna().all()
    assert not monthly.loc[(monthly.service_code == "bus_rkl") & (monthly.year_month == "2024-02"), "complete"].item()


def test_actual_snapshot_reconciles():
    clean = clean_data(pd.read_csv(RAW_PATH))
    validate_outputs(clean, reshape_data(clean))
