"""Data-quality checks for one answer, scoped to its window and columns (D23)."""
import sqlglot
from sqlglot import exp

from executor import run
from semantic import ATTEMPTS, DIMENSIONS

NULL_LIMIT = 0.01  # caveat above this null rate

# Nullable key column: (rows it is measured on, what the answer does with a null).
NULLABLE = {
    "bank_id": ("TRUE", "Attempts", "counted in the Unknown bank Segment"),
}


def check(db_path, weeks, sqls):
    """{"duplicates": n, "nulls": {column: rate}, "caveats": [line]} for the
    Attempts in `weeks`, checking only the nullable columns `sqls` use."""
    window = f"{DIMENSIONS['week']} IN ({', '.join(str(int(w)) for w in weeks)})"
    rows, attempts = run(
        f"SELECT COUNT(*) AS n, COUNT(DISTINCT txn_id) AS a FROM transactions WHERE {window}",
        db_path).iloc[0]
    dupes = int(rows - attempts)
    caveats = [f"{dupes:,} Duplicates ({dupes / rows:.1%} of rows) excluded; the first copy is kept."]

    used = {c.name for sql in sqls for c in sqlglot.parse_one(sql, read="duckdb").find_all(exp.Column)}
    cols = [c for c in NULLABLE if c in used]
    nulls = {}
    if cols:
        rates = ", ".join(f"AVG(CASE WHEN {c} IS NULL THEN 1.0 ELSE 0.0 END) FILTER (WHERE {NULLABLE[c][0]}) AS {c}"
                          for c in cols)
        nulls = run(f"SELECT {rates} FROM {ATTEMPTS} WHERE {window}", db_path).iloc[0].to_dict()
    for c, rate in nulls.items():
        if rate > NULL_LIMIT:
            _, rows_label, effect = NULLABLE[c]
            caveats.append(f"`{c}` is missing on {rate:.1%} of {rows_label}; they are {effect}.")
    return {"duplicates": dupes, "nulls": nulls, "caveats": caveats}
