"""Compile a query spec into SQL deterministically. The model never writes it."""
from semantic import ATTEMPTS, DIMENSIONS, JOINS, METRICS


def compile_sql(metrics, dimensions, weeks, filters={}):
    """filters: {dimension: value}, each an equality on that dimension."""
    select = [f"{DIMENSIONS[d]} AS {d}" for d in dimensions]
    select += [f"{METRICS[m]} AS {m}" for m in metrics]
    weeks_sql = ", ".join(str(int(w)) for w in weeks)
    # Doubled quotes keep a model-supplied value inside its string literal.
    where = "".join(" AND {} = '{}'".format(DIMENSIONS[d], v.replace("'", "''")) for d, v in filters.items())
    groups = ", ".join(str(i + 1) for i in range(len(dimensions)))
    # LEFT JOIN keeps Attempts with a null key, so Segment totals still add up.
    joins = "".join(f" LEFT JOIN {t} ON {t}.{k} = transactions.{k}"
                    for t, k in JOINS.items() if f"{t}." in " ".join(select) + where)
    return (f"SELECT {', '.join(select)} FROM {ATTEMPTS}{joins}"
            f" WHERE {DIMENSIONS['week']} IN ({weeks_sql}){where}"
            f" GROUP BY {groups} ORDER BY {groups}")
