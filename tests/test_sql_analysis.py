import duckdb
import pandas as pd
import pytest

from src.config import RAW_PATH, ROOT
from src.data_cleaning import clean_data, reshape_data
from src.features import monthly_service_metrics


def test_sql_growth_matches_fresh_python_calculation(monkeypatch):
    monkeypatch.chdir(ROOT)
    with duckdb.connect() as connection:
        connection.execute((ROOT / "sql/schema.sql").read_text())
        query = connection.extract_statements((ROOT / "sql/analysis.sql").read_text())[2]
        sql = connection.execute(query).df()
        python = monthly_service_metrics(reshape_data(clean_data(pd.read_csv(RAW_PATH))))
        sql["year_month"] = sql.month.dt.strftime("%Y-%m")
        joined = sql.merge(python, on=["service", "year_month"], suffixes=("_sql", "_python"))
        assert len(joined) == len(sql)
        for measure in ["mom_pct", "yoy_pct"]:
            left, right = joined[f"{measure}_sql"], joined[f"{measure}_python"]
            assert left.isna().equals(right.isna())
            assert left.dropna().tolist() == pytest.approx(right.dropna().tolist())
