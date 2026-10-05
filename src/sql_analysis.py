"""Execute the SQL files and save each result for inspection."""
import os
import duckdb

from .config import ROOT


def run_sql():
    previous_dir = os.getcwd()
    output = ROOT / "reports/sql"
    output.mkdir(parents=True, exist_ok=True)
    try:
        os.chdir(ROOT)
        with duckdb.connect() as connection:
            connection.execute((ROOT / "sql/schema.sql").read_text(encoding="utf-8"))
            for filename in ("data_quality", "analysis"):
                statements = connection.extract_statements((ROOT / f"sql/{filename}.sql").read_text(encoding="utf-8"))
                for number, statement in enumerate(statements, 1):
                    result = connection.execute(statement).df()
                    result.to_csv(output / f"{filename}_{number:02}.csv", index=False)
                    if filename == "data_quality" and number in (1, 2, 4, 5) and not result.empty:
                        raise ValueError(f"SQL quality check {number} failed")
                    print(f"{filename} {number}: {len(result):,} rows")
    finally:
        os.chdir(previous_dir)


if __name__ == "__main__":
    run_sql()
