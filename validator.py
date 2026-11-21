"""Check SQL against the safety rules before anything runs."""
import sqlglot
from sqlglot import exp

from semantic import TABLES

ROW_LIMIT = 10000


class Rejected(Exception):
    """A query the validator refused; the message is the human-readable reason."""


def validate(sql):
    """Return (safe SQL, tables used) or raise Rejected."""
    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except sqlglot.errors.ParseError:
        raise Rejected("The query could not be parsed.")
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise Rejected("Only a single SELECT statement may run.")
    tree = statements[0]

    tables = sorted({t.name for t in tree.find_all(exp.Table)})
    unknown = [t for t in tables if t not in TABLES]
    if unknown:
        raise Rejected(f"Table not in the semantic layer: {', '.join(unknown)}.")
    allowed = {c for t in tables for c in TABLES[t]}
    unknown = sorted({c.name for c in tree.find_all(exp.Column)} - allowed)
    if unknown:
        raise Rejected(f"Column not in the semantic layer: {', '.join(unknown)}.")

    if not tree.args.get("limit"):
        tree = tree.limit(ROW_LIMIT)
    return tree.sql(dialect="duckdb"), tables
