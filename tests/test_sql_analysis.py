import duckdb
import pandas as pd
import pytest

from src.config import ROOT


def test_sql_growth_matches_python_export(monkeypatch):
    monkeypatch.chdir(ROOT)
    with duckdb.connect() as connection:
        connection.execute((ROOT / "sql/schema.sql").read_text())
        query = connection.extract_statements((ROOT / "sql/analysis.sql").read_text())[2]
        sql = connection.execute(query).df()
        python = pd.read_csv(ROOT / "reports/monthly_service_metrics.csv")
        sql["year_month"] = sql.month.dt.strftime("%Y-%m")
        joined = sql.merge(python, on=["service", "year_month"], suffixes=("_sql", "_python"))
        assert len(joined) == len(sql)
        for measure in ["mom_pct", "yoy_pct"]:
            left, right = joined[f"{measure}_sql"], joined[f"{measure}_python"]
            assert left.isna().equals(right.isna())
            assert left.dropna().tolist() == pytest.approx(right.dropna().tolist())
