"""Data-quality checks for one answer, scoped to its window and columns (D23)."""
import pandas as pd
import sqlglot
from sqlglot import exp

from executor import run
from generator import START
from semantic import ATTEMPTS, DIMENSIONS, SETTLED

NULL_LIMIT = 0.01  # caveat above this null rate
GAP_SHARE = 0.5  # a day below this share of the usual (median) daily Attempts
MIN_ATTEMPTS = 200  # a Segment below this in any Week is low-confidence
MISMATCH = 0.005  # Source mismatch: Settlements off successful Attempt value by more than this

# Nullable key column: (rows it is measured on, what the answer does with a null).
NULLABLE = {
    "bank_id": ("TRUE", "Attempts", "counted in the Unknown bank Segment"),
    "amount": ("TRUE", "Attempts", "counted as Attempts but left out of GMV and Average ticket"),
    "failure_reason": ("status = 'failed'", "failed Attempts", "counted as Unknown reason"),
}


def check(db_path, weeks, sqls, segments):
    """{"duplicates", "nulls", "gaps", "mismatch", "low_confidence", "caveats", "confidence"} for the
    Attempts in `weeks`, checking only the nullable columns `sqls` use.
    `segments` is {week: {Segment: (attempts, rate)}}."""
    window = f"{DIMENSIONS['week']} IN ({', '.join(str(int(w)) for w in weeks)})"
    rows, attempts = run(
        f"SELECT COUNT(*) AS n, COUNT(DISTINCT txn_id) AS a FROM transactions WHERE {window}",
        db_path).iloc[0]
    dupes = int(rows - attempts)
    caveats = [f"{dupes:,} Duplicates ({dupes / rows:.1%} of rows) excluded; the first copy is kept."]

    trees = [sqlglot.parse_one(sql, read="duckdb") for sql in sqls]
    used = {c.name for tree in trees for c in tree.find_all(exp.Column)}
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
    daily = run(f"SELECT CAST(ts AS DATE) AS day, COUNT(*) AS n FROM {ATTEMPTS} GROUP BY 1", db_path)
    counts = dict(zip(pd.to_datetime(daily["day"]).dt.date, daily["n"]))
    days = [(START + pd.Timedelta(days=7 * (w - 1) + i)).date() for w in weeks for i in range(7)]
    gaps = [d for d in days if counts.get(d, 0) < GAP_SHARE * daily["n"].median()]
    if gaps:
        caveats.append(f"Coverage gap: under {GAP_SHARE:.0%} of the usual daily Attempts on "
                       f"{', '.join(map(str, gaps))}.")

    mismatch = 0  # merchant-days, checked only when the answer reads Settlements
    if any(t.name == "settlements" for tree in trees for t in tree.find_all(exp.Table)):
        # A missing side counts as 0, so an unsettled merchant-day is a mismatch too.
        mismatch, days = run(
            f"SELECT COUNT(*) FILTER (WHERE ABS(COALESCE(settled_amount, 0) - COALESCE(amount, 0))"
            f" > {MISMATCH} * COALESCE(amount, 0)), COUNT(*) FROM {SETTLED} WHERE {window}", db_path).iloc[0]
        if mismatch:
            caveats.append(f"Source mismatch: Settlements differ from successful Attempt value by over "
                           f"{MISMATCH:.1%} on {mismatch:,} of {days:,} merchant-days.")

    low = sorted({f"{seg} in wk{w} ({a:,})" for w, segs in segments.items()
                  for seg, (a, _) in segs.items() if a < MIN_ATTEMPTS})
    if low:
        caveats.append(f"Under {MIN_ATTEMPTS} Attempts, so low-confidence: {'; '.join(low)}.")
        confidence = "Low: some Segments are too small to trust their rates."
    elif len(caveats) > 1:
        confidence = "Medium: read the Caveats before acting."
    else:
        confidence = "High: no data-quality issues beyond the excluded Duplicates."
    return {"duplicates": dupes, "nulls": nulls, "gaps": gaps, "mismatch": int(mismatch), "low_confidence": low,
            "caveats": caveats, "confidence": confidence}
