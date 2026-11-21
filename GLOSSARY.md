# Payments Analytics

The language of the AI Business Analyst: payment performance questions asked by business users, and the evidence-backed answers it returns.

## Time

**Week**:
Monday to Sunday, numbered from wk1 = 28 Sep 2026 to wk8 = 16-22 Nov 2026.
_Avoid_: ISO week, rolling 7 days

## Payments

**Attempt**:
One distinct transaction, identified by `txn_id`, with status success or failed. There is no pending status.
_Avoid_: Transaction row, txn (when counting)

**Duplicate**:
A repeated row with the same `txn_id` as an earlier row. Only the first copy is an Attempt.
_Avoid_: Double-count, repeat

**Success rate**:
Successful Attempts divided by all Attempts. Failed Attempts with an unknown failure reason still count.
_Avoid_: Approval rate, conversion

**GMV**:
The total value of successful Attempts. Attempts with an unknown amount are left out.
_Avoid_: Volume, TPV, revenue

**Average ticket**:
GMV divided by the number of successful Attempts with a known amount.
_Avoid_: AOV, basket size

**Settlement**:
The gross amount paid out to a merchant for the successful Attempts of one transaction date. There are no fees.
_Avoid_: Payout, settled value

**Source mismatch**:
A gap above 0.5% between Settlement and successful Attempt value for the same merchants and dates.
_Avoid_: Reconciliation break, discrepancy

## Analysis

**Segment**:
One value of a dimension, such as UPI or one bank. Attempts with an unknown bank form their own segment, "Unknown bank".
_Avoid_: Cohort, slice, bucket

**Mix effect**:
The part of a Success rate change caused by Attempts moving between segments with different Success rates.
_Avoid_: Composition effect, Simpson's effect

**Rate effect**:
The part of a Success rate change caused by Success rates changing within segments.
_Avoid_: Performance effect, degradation (unless the rate effect is negative)

## Answers

**Assumption**:
A default the analyst chose for an ambiguous question, such as time window or denominator. It is shown to the user, who can change it.
_Avoid_: Guess, interpretation

**Fact**:
A statement backed by an executed query, with its tables, filters and time window cited.
_Avoid_: Finding, insight

**Hypothesis**:
A plausible explanation for the Facts that the data does not prove.
_Avoid_: Insight, root cause

**Recommendation**:
A suggested next action that follows from the Facts and Hypotheses.
_Avoid_: Insight, action item

## Access

**Analyst**:
A role that may see all datasets.

**Merchant manager**:
A role limited to one merchant category, with no access to Settlements.
_Avoid_: Merchant (the merchant is the business, not the user)
