"""Compile a query spec into SQL deterministically. The model never writes it."""
from semantic import DIMENSIONS, METRICS


def compile_sql(metrics, dimensions, weeks):
    select = [f"{DIMENSIONS[d]} AS {d}" for d in dimensions]
    select += [f"{METRICS[m]} AS {m}" for m in metrics]
    weeks_sql = ", ".join(str(int(w)) for w in weeks)
    groups = ", ".join(str(i + 1) for i in range(len(dimensions)))
    return (f"SELECT {', '.join(select)} FROM transactions"
            f" WHERE {DIMENSIONS['week']} IN ({weeks_sql})"
            f" GROUP BY {groups} ORDER BY {groups}")
