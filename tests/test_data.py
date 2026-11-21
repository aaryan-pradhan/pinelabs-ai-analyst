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


def test_story_b_one_bank_card_rate_falls_in_wk7(con):
    card = con.execute(f"""
        SELECT banks.name, {RATE} FILTER (WHERE {WEEK} = 6), {RATE} FILTER (WHERE {WEEK} = 7)
        FROM transactions JOIN banks USING (bank_id)
        WHERE payment_method = 'card' GROUP BY 1
    """).fetchall()
    fell = [(bank, wk6, wk7) for bank, wk6, wk7 in card if wk7 - wk6 < -0.05]
    assert len(fell) == 1
    _, wk6, wk7 = fell[0]
    assert 0.90 < wk6 < 0.94
    assert 0.76 < wk7 < 0.80


def test_story_c_duplicates_and_nulls(con):
    rows, ids, distinct_rows = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT txn_id), (SELECT COUNT(*) FROM (SELECT DISTINCT * FROM transactions))"
        " FROM transactions").fetchone()
    assert 0.014 < (rows - ids) / rows < 0.016
    assert distinct_rows == ids  # every Duplicate is an exact copy

    bank, amount, reason, success_reason = con.execute("""
        SELECT AVG(CASE WHEN bank_id IS NULL THEN 1.0 ELSE 0.0 END),
               AVG(CASE WHEN amount IS NULL THEN 1.0 ELSE 0.0 END),
               AVG(CASE WHEN failure_reason IS NULL THEN 1.0 ELSE 0.0 END) FILTER (WHERE status = 'failed'),
               COUNT(failure_reason) FILTER (WHERE status = 'success')
        FROM (SELECT DISTINCT * FROM transactions)
    """).fetchone()
    assert 0.015 < bank < 0.025
    assert 0.01 < amount < 0.02
    assert 0.02 < reason < 0.04
    assert success_reason == 0


def test_same_seed_reproduces_identical_data(db_path, tmp_path):
    again = tmp_path / "again.duckdb"
    generator.build(again)
    a = duckdb.connect(str(db_path), read_only=True)
    b = duckdb.connect(str(again), read_only=True)
    for table in ["transactions", "merchants", "banks", "settlements"]:
        query = f"SELECT * FROM {table} ORDER BY ALL"
        assert a.execute(query).fetchall() == b.execute(query).fetchall(), table
