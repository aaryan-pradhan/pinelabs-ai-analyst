"""The semantic layer: the only tables, columns, joins, metrics and dimensions
a plan may use. Metric and dimension expressions are SQL over `transactions`."""

TABLES = {
    "transactions": ["txn_id", "ts", "merchant_id", "bank_id", "payment_method",
                     "amount", "status", "failure_reason"],
    "merchants": ["merchant_id", "name", "category", "city", "tier"],
    "banks": ["bank_id", "name", "type"],
    "settlements": ["merchant_id", "date", "settled_amount", "settled_count"],
}

# Attempts: `transactions` with Duplicates removed. Every metric reads from this.
# ponytail: Duplicates are exact copies, so any copy is the first; order by an
# ingest column here if copies can ever differ.
ATTEMPTS = "(SELECT DISTINCT ON (txn_id) * FROM transactions) AS transactions"

# Allowed joins from transactions: table -> key column.
JOINS = {"merchants": "merchant_id", "banks": "bank_id"}

METRICS = {
    "attempts": "COUNT(*)",
    "successful_attempts": "COUNT(*) FILTER (WHERE status = 'success')",
    "success_rate": "AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END)",
    # SUM and AVG skip null amounts: those Attempts still count as Attempts.
    "gmv": "SUM(amount) FILTER (WHERE status = 'success')",
    "average_ticket": "AVG(amount) FILTER (WHERE status = 'success')",
    # A reason's share of the Week's failed Attempts; needs the week dimension.
    "failure_share": "COUNT(*) FILTER (WHERE status = 'failed') / SUM(COUNT(*) FILTER (WHERE status = 'failed'))"
                     " OVER (PARTITION BY CAST(FLOOR(date_diff('day', DATE '2026-09-28', CAST(ts AS DATE)) / 7)"
                     " AS INTEGER) + 1)",
}

DIMENSIONS = {
    # Week is Monday to Sunday, wk1 = 28 Sep 2026.
    "week": "CAST(FLOOR(date_diff('day', DATE '2026-09-28', CAST(ts AS DATE)) / 7) AS INTEGER) + 1",
    "payment_method": "payment_method",
    "bank": "COALESCE(banks.name, 'Unknown bank')",  # null bank_id is its own Segment
    # Failed Attempts only; successful ones group under NULL.
    "failure_reason": "CASE WHEN status = 'failed' THEN COALESCE(failure_reason, 'Unknown reason') END",
}
