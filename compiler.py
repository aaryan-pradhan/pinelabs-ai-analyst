"""Compile a query spec into SQL deterministically. The model never writes it."""
from semantic import ATTEMPTS, DIMENSIONS, JOINS, METRICS


def compile_sql(metrics, dimensions, weeks):
    select = [f"{DIMENSIONS[d]} AS {d}" for d in dimensions]
    select += [f"{METRICS[m]} AS {m}" for m in metrics]
    weeks_sql = ", ".join(str(int(w)) for w in weeks)
    groups = ", ".join(str(i + 1) for i in range(len(dimensions)))
    # LEFT JOIN keeps Attempts with a null key, so Segment totals still add up.
    joins = "".join(f" LEFT JOIN {t} ON {t}.{k} = transactions.{k}"
                    for t, k in JOINS.items() if f"{t}." in " ".join(select))
    return (f"SELECT {', '.join(select)} FROM {ATTEMPTS}{joins}"
            f" WHERE {DIMENSIONS['week']} IN ({weeks_sql})"
            f" GROUP BY {groups} ORDER BY {groups}")
