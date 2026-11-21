"""Check SQL against the safety rules before anything runs."""
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from semantic import JOINS, TABLES

ROW_LIMIT = 10000


@dataclass(frozen=True)
class Role:
    """Who is asking; auth is mocked (D15). A category limits the role to that one
    merchant category and hides Settlements."""
    name: str
    category: str = None


ANALYST = Role("Analyst")


class Rejected(Exception):
    """A query the validator refused; the message is the human-readable reason."""


def validate(sql, role=ANALYST):
    """Return (safe SQL, tables used) or raise Rejected. A role with a category gets
    that category's filter added; the rule lives here, not in the prompt."""
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

    if role.category is not None:
        tree = scoped(tree, tables, role)
        tables = sorted({t.name for t in tree.find_all(exp.Table)})
    if not tree.args.get("limit"):
        tree = tree.limit(ROW_LIMIT)
    return tree.sql(dialect="duckdb"), tables


def scoped(tree, tables, role):
    """`tree` limited to the role's category, joining merchants if it is not joined."""
    # ponytail: scopes the outer query only; safe because SQL comes from the compiler,
    # whose one subquery is the unfiltered Attempts source. Scope subqueries if plans ever nest.
    named = {eq.expression.name for eq in tree.find_all(exp.EQ)
             if isinstance(eq.this, exp.Column) and eq.this.name == "category"}
    if role.category in named:
        return tree
    if "merchants" not in tables:
        key = JOINS["merchants"]
        tree = tree.join("merchants", on=f"merchants.{key} = transactions.{key}", join_type="left")
    return tree.where(exp.column("category", "merchants").eq(exp.Literal.string(role.category)))
