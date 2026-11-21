"""Check SQL against the safety rules before anything runs."""
from dataclasses import dataclass

import sqlglot
from sqlglot import exp

from semantic import ATTEMPTS, JOINS, TABLES

ROW_LIMIT = 10000


@dataclass(frozen=True)
class Role:
    """Who is asking; auth is mocked (D15). A category limits the role to that one
    merchant category and hides Settlements."""
    name: str
    category: str = None


ANALYST = Role("Analyst")
ATTEMPTS_FROM = sqlglot.parse_one(f"SELECT * FROM {ATTEMPTS}", read="duckdb").args["from_"]


class Rejected(Exception):
    """A query the validator refused; the message is the human-readable reason."""
    sql = ()  # the refused SQL, shown with the reason


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
    allowed |= {a.alias for a in tree.find_all(exp.Alias)}  # ORDER BY n, HAVING n > 5
    unknown = sorted({c.name for c in tree.find_all(exp.Column)} - allowed)
    if unknown:
        raise Rejected(f"Column not in the semantic layer: {', '.join(unknown)}.")
    for join in tree.find_all(exp.Join):
        if not keyed(join):
            raise Rejected(f"Join without a key: {join.sql(dialect='duckdb')}. Join on a key both tables "
                           "share, e.g. merchants.merchant_id = transactions.merchant_id.")

    if role.category is not None:
        tree = scoped(tree, tables, role)
        tables = sorted({t.name for t in tree.find_all(exp.Table)})
    if not tree.args.get("limit"):
        tree = tree.limit(ROW_LIMIT)
    return tree.sql(dialect="duckdb"), tables


def keyed(join):
    """USING, or an ON with no OR that equates two tables' join key (merchant_id, bank_id)."""
    if join.args.get("using"):
        return True
    on = join.args.get("on")
    if on is None or on.find(exp.Or):
        return False
    return any(isinstance(eq, exp.EQ) and isinstance(eq.this, exp.Column) and isinstance(eq.expression, exp.Column)
               and eq.this.name == eq.expression.name in JOINS.values() and eq.this.table != eq.expression.table
               for eq in (on.flatten() if isinstance(on, exp.And) else [on]))


def scoped(tree, tables, role):
    """`tree` limited to the role's category, joining merchants if it is not joined."""
    if "settlements" in tables:
        raise Rejected(f"A {role.name} cannot see Settlements; only an Analyst can.")
    # The scope is ANDed on the outer query only, so the one subquery allowed is the
    # compiler's Attempts source in FROM; any other could read every category.
    # ponytail: refuses all other subqueries; scope each nested SELECT if managers need them.
    nested = [q for q in tree.find_all(exp.Select) if q is not tree]
    if nested and (len(nested) > 1 or tree.args.get("from_") != ATTEMPTS_FROM):
        raise Rejected(f"A {role.name} query may not use subqueries; the category scope covers the outer query only.")
    # A second copy of a table escapes the scope: it is not the copy the filter names.
    names = [t.name for t in tree.find_all(exp.Table)]
    if len(names) != len(set(names)):
        raise Rejected(f"A {role.name} query may read each table once; the category scope covers one copy only.")
    named = {eq.expression.name for eq in tree.find_all(exp.EQ)
             if isinstance(eq.this, exp.Column) and eq.this.name == "category"}
    others = sorted(n for n in named if n.lower() != role.category.lower())
    if others:
        raise Rejected(f"A {role.name} for {role.category} cannot see {', '.join(others)}; "
                       f"ask about {role.category} only.")
    # Always ANDed at the top: a match elsewhere (an OR, a CASE) does not scope the rows.
    scope = exp.column("category", "merchants").eq(exp.Literal.string(role.category))
    where = tree.args.get("where")
    if where and scope in (where.this.flatten() if isinstance(where.this, exp.And) else [where.this]):
        return tree
    if "merchants" not in tables:
        key = JOINS["merchants"]
        tree = tree.join("merchants", on=f"merchants.{key} = transactions.{key}", join_type="left")
    return tree.where(scope)
