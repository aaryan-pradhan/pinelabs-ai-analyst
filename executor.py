"""Run validated SQL on a read-only DuckDB connection."""
import threading

import duckdb

from validator import Rejected

TIMEOUT = 5  # seconds (D28)


def run(sql, db_path, timeout=TIMEOUT):
    # No file or network access: model-written SQL could otherwise call read_text().
    # Set after connect, not as connect config, so other connections to the file still open.
    with duckdb.connect(str(db_path), read_only=True) as con:
        con.execute("SET enable_external_access = false")
        timer = threading.Timer(timeout, con.interrupt)
        timer.start()
        try:
            return con.execute(sql).df()
        except duckdb.InterruptException:
            raise Rejected(f"The query was cut off after {timeout:g} seconds; ask for less data.")
        except duckdb.Error as e:  # e.g. model SQL naming a column the table lacks
            raise Rejected(f"The query could not run: {e}")
        finally:
            timer.cancel()
