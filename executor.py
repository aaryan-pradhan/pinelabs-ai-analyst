"""Run validated SQL on a read-only DuckDB connection."""
import threading

import duckdb

from validator import Rejected

TIMEOUT = 5  # seconds (D28)


def run(sql, db_path, timeout=TIMEOUT):
    with duckdb.connect(str(db_path), read_only=True) as con:
        timer = threading.Timer(timeout, con.interrupt)
        timer.start()
        try:
            return con.execute(sql).df()
        except duckdb.InterruptException:
            raise Rejected(f"The query was cut off after {timeout:g} seconds; ask for less data.")
        finally:
            timer.cancel()
