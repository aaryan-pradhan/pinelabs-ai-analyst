"""Seeded synthetic payments data, written to a DuckDB file.

8 Weeks, Mon 28 Sep - Sun 22 Nov 2026. Planted story (a): in wk6 a
festive-sale merchant pushes extra traffic to netbanking and wallet, so the
overall Success rate falls while every payment method stays flat. Planted
story (b): in wk7 Coastal Bank's card Success rate falls from ~92% to ~78%.
Planted story (c): ~1.5% exact-copy Duplicates and nulls in bank_id, amount and
failure_reason. Planted story (d): in wk5 electronics merchants' Settlements are
3% below their successful Attempt value; everywhere else they match exactly.
"""
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

START = pd.Timestamp("2026-09-28")
DAYS = 56
BASE_PER_DAY = 2550
FESTIVE_PER_DAY = 1050  # wk6 extra traffic from the festive merchant
FESTIVE_MERCHANT = 1

# payment method: (share of baseline traffic, Success rate)
METHODS = {
    "upi": (0.62, 0.955),
    "card": (0.28, 0.915),
    "netbanking": (0.06, 0.78),
    "wallet": (0.04, 0.80),
}
FESTIVE_METHODS = {"netbanking": 0.55, "wallet": 0.45}
DROP_BANK, DROP_RATE = 3, 0.78  # story (b): Coastal Bank's card rate in wk7
SHORT_CATEGORY, SHORT_WEEK, SHORT_BY = "electronics", 5, 0.03  # story (d): wk5 Settlements 3% short

CATEGORIES = ["grocery", "electronics", "fashion", "travel", "food_delivery", "fuel"]
CITIES = ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad",
          "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]
TIERS = ["large", "mid", "small"]
BANKS = [("Arya Bank", "public"), ("Bharat National Bank", "public"),
         ("Coastal Bank", "public"), ("Deccan Private Bank", "private"),
         ("Everest Bank", "private"), ("Fortune Bank", "private"),
         ("Global Trust Bank", "foreign"), ("Harbour International", "foreign")]
FAILURE_REASONS = ["insufficient_funds", "bank_timeout", "authentication_failed",
                   "risk_declined", "technical_error"]
N_MERCHANTS = 300
DUPLICATES = 0.015  # share of Attempts copied once more
NULL_BANK, NULL_AMOUNT = 0.02, 0.015  # share of Attempts
NULL_REASON = 0.03  # share of failed Attempts
DB_PATH = Path(__file__).parent / "payments.duckdb"


def build(path, seed=42):
    rng = np.random.default_rng(seed)

    merchants = pd.DataFrame({
        "merchant_id": np.arange(1, N_MERCHANTS + 1),
        "name": [f"Merchant {i:03d}" for i in range(1, N_MERCHANTS + 1)],
        "category": rng.choice(CATEGORIES, N_MERCHANTS),
        "city": rng.choice(CITIES, N_MERCHANTS),
        "tier": rng.choice(TIERS, N_MERCHANTS, p=[0.1, 0.3, 0.6]),
    })
    merchants.loc[0, ["name", "category"]] = ["Utsav Festive Mart", "fashion"]
    banks = pd.DataFrame({
        "bank_id": np.arange(1, len(BANKS) + 1),
        "name": [b[0] for b in BANKS],
        "type": [b[1] for b in BANKS],
    })

    n_base = DAYS * BASE_PER_DAY
    day = np.repeat(np.arange(DAYS), BASE_PER_DAY)
    weights = rng.lognormal(0, 1, N_MERCHANTS)
    merchant = rng.choice(merchants.merchant_id, n_base, p=weights / weights.sum())
    method = rng.choice(list(METHODS), n_base, p=[s for s, _ in METHODS.values()])

    festive_days = np.arange(35, 42)  # wk6
    n_fest = len(festive_days) * FESTIVE_PER_DAY
    day = np.concatenate([day, np.repeat(festive_days, FESTIVE_PER_DAY)])
    merchant = np.concatenate([merchant, np.full(n_fest, FESTIVE_MERCHANT)])
    method = np.concatenate([method, rng.choice(
        list(FESTIVE_METHODS), n_fest, p=list(FESTIVE_METHODS.values()))])

    n = len(day)
    tx = pd.DataFrame({
        "ts": START + pd.to_timedelta(day, "D") + pd.to_timedelta(rng.integers(0, 86400, n), "s"),
        "merchant_id": merchant,
        "bank_id": rng.integers(1, len(BANKS) + 1, n),
        "payment_method": method,
        "amount": np.round(rng.lognormal(7, 1, n), 2),
    })

    # Exact successes per (week, method, bank) keep each rate flat week to week,
    # except Coastal Bank's cards in wk7 (story b).
    week = day // 7
    success = np.zeros(n, dtype=bool)
    for (w, m, b), idx in tx.groupby([week, method, tx["bank_id"]]).indices.items():
        dropped = (w, m, b) == (6, "card", DROP_BANK)
        k = round(len(idx) * (DROP_RATE if dropped else METHODS[m][1]))
        success[rng.choice(idx, k, replace=False)] = True
    tx["status"] = np.where(success, "success", "failed")
    tx["failure_reason"] = np.where(success, None, rng.choice(FAILURE_REASONS, n))

    # Story (c): nulls in bank_id, amount and failed Attempts' failure_reason.
    tx["bank_id"] = tx["bank_id"].astype("Int64")
    tx["amount"] = tx["amount"].astype("Float64")
    tx.loc[rng.random(n) < NULL_BANK, "bank_id"] = pd.NA
    tx.loc[rng.random(n) < NULL_AMOUNT, "amount"] = pd.NA
    tx.loc[~success & (rng.random(n) < NULL_REASON), "failure_reason"] = None

    tx = tx.sort_values("ts", kind="stable").reset_index(drop=True)
    tx.insert(0, "txn_id", np.arange(1, n + 1))

    # Story (c): exact-copy Duplicates. Settlements are built from Attempts, without them.
    dup = rng.choice(n, round(n * DUPLICATES), replace=False)
    with_dups = pd.concat([tx, tx.iloc[dup]]).sort_values("txn_id", kind="stable")

    path = Path(path)
    path.unlink(missing_ok=True)
    con = duckdb.connect(str(path))
    for name, df in [("transactions", with_dups), ("merchants", merchants), ("banks", banks)]:
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
    # Story (d): keyed by transaction date, gross, no fees; one category short in wk5.
    con.execute(f"""
        CREATE TABLE settlements AS
        SELECT merchant_id, CAST(ts AS DATE) AS date,
               SUM(amount) * CASE WHEN category = '{SHORT_CATEGORY}'
                                   AND date_diff('day', DATE '{START.date()}', CAST(ts AS DATE)) // 7 + 1 = {SHORT_WEEK}
                                  THEN {1 - SHORT_BY} ELSE 1 END AS settled_amount,
               COUNT(*) AS settled_count
        FROM tx JOIN merchants USING (merchant_id) WHERE status = 'success'
        GROUP BY 1, 2, category ORDER BY 1, 2
    """)
    con.close()


def ensure(path):
    """Build the database from the seed if it is missing."""
    if not Path(path).exists():
        build(path)


EXPECTED_PATH = Path(__file__).parent / "eval" / "expected.json"


def expected(path):
    """The eval's expected answers, from hand-written SQL over the generated data,
    independent of the semantic layer and compiler the analyst uses."""
    con = duckdb.connect(str(path), read_only=True)
    wk = f"date_diff('day', DATE '{START.date()}', CAST(ts AS DATE)) // 7 + 1"
    tx = f"(SELECT DISTINCT ON (txn_id) *, {wk} AS wk FROM transactions) t"  # Duplicates removed
    ok = "AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END)"

    def rows(sql):
        return con.execute(sql).fetchall()

    (wk5, wk6), = rows(f"SELECT {ok} FILTER (WHERE wk = 5), {ok} FILTER (WHERE wk = 6) FROM {tx}")
    methods = rows(f"SELECT payment_method, {ok} FILTER (WHERE wk = 6) - {ok} FILTER (WHERE wk = 5)"
                   f" FROM {tx} GROUP BY 1 ORDER BY 1")
    (bank, card6, card7), = rows(
        f"SELECT b.name, {ok} FILTER (WHERE wk = 6), {ok} FILTER (WHERE wk = 7) FROM {tx}"
        f" JOIN banks b USING (bank_id) WHERE payment_method = 'card' AND b.bank_id = {DROP_BANK} GROUP BY 1")
    (dupes,), = rows("SELECT COUNT(*) - COUNT(DISTINCT txn_id) FROM transactions")
    (gap,), = rows(
        f"SELECT (SELECT SUM(settled_amount) FROM settlements s JOIN merchants m USING (merchant_id)"
        f"  WHERE m.category = '{SHORT_CATEGORY}' AND date_diff('day', DATE '{START.date()}', s.date) // 7 + 1 = {SHORT_WEEK})"
        f" / SUM(amount) - 1 FROM {tx} JOIN merchants m USING (merchant_id)"
        f" WHERE status = 'success' AND m.category = '{SHORT_CATEGORY}' AND wk = {SHORT_WEEK}")
    gmv = rows(f"SELECT m.category, ROUND(SUM(amount), 2) FROM {tx} JOIN merchants m USING (merchant_id)"
               " WHERE status = 'success' AND wk = 8 GROUP BY 1 ORDER BY 1")
    con.close()
    r = lambda x: round(x, 10)  # parallel float sums differ in the last digits run to run
    return {"wk6_total_change": r(wk6 - wk5), "wk6_method_change": {m: r(c) for m, c in methods},
            "drop_bank": bank, "drop_bank_card_rate": [r(card6), r(card7)], "duplicates": dupes,
            "gap_category": SHORT_CATEGORY, "gap": r(gap), "wk8_gmv_by_category": dict(gmv)}


if __name__ == "__main__":  # rebuild the database and the eval's expected answers
    build(DB_PATH)
    EXPECTED_PATH.parent.mkdir(exist_ok=True)
    EXPECTED_PATH.write_text(json.dumps(expected(DB_PATH), indent=2) + "\n")
