"""Seam 2: the generated database, checked with plain SQL."""
import duckdb

import generator

WEEK = "CAST(FLOOR(date_diff('day', DATE '2026-09-28', CAST(ts AS DATE)) / 7) AS INTEGER) + 1"
RATE = "AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END)"


def test_story_a_wk6_overall_drop_with_every_method_flat(con):
    overall = dict(con.execute(
        f"SELECT {WEEK} AS wk, {RATE} FROM transactions WHERE {WEEK} IN (5, 6) GROUP BY 1"
    ).fetchall())
    assert -0.05 < overall[6] - overall[5] < -0.03

    by_method = con.execute(f"""
        SELECT payment_method,
               {RATE} FILTER (WHERE {WEEK} = 6) - {RATE} FILTER (WHERE {WEEK} = 5)
        FROM transactions GROUP BY 1
    """).fetchall()
    assert sorted(m for m, _ in by_method) == ["card", "netbanking", "upi", "wallet"]
    for method, change in by_method:
        assert abs(change) <= 0.003, method


def test_same_seed_reproduces_identical_data(db_path, tmp_path):
    again = tmp_path / "again.duckdb"
    generator.build(again)
    a = duckdb.connect(str(db_path), read_only=True)
    b = duckdb.connect(str(again), read_only=True)
    for table in ["transactions", "merchants", "banks", "settlements"]:
        query = f"SELECT * FROM {table} ORDER BY ALL"
        assert a.execute(query).fetchall() == b.execute(query).fetchall(), table
