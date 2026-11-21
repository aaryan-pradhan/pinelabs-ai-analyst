"""Data-quality checks for one answer, scoped to its window (D23)."""
from executor import run
from semantic import DIMENSIONS


def check(db_path, weeks):
    """{"duplicates": n, "caveats": [line]} for the Attempts in `weeks`."""
    window = f"{DIMENSIONS['week']} IN ({', '.join(str(int(w)) for w in weeks)})"
    rows, attempts = run(
        f"SELECT COUNT(*) AS n, COUNT(DISTINCT txn_id) AS a FROM transactions WHERE {window}",
        db_path).iloc[0]
    dupes = int(rows - attempts)
    return {"duplicates": dupes,
            "caveats": [f"{dupes:,} Duplicates ({dupes / rows:.1%} of rows) excluded; the first copy is kept."]}
