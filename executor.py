"""Run validated SQL on a read-only DuckDB connection."""
import duckdb


def run(sql, db_path):
    with duckdb.connect(str(db_path), read_only=True) as con:
        return con.execute(sql).df()
