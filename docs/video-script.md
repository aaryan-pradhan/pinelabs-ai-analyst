# Video script

Target length: about 2 minutes 35 seconds (the form allows 2 to 5). Spoken
pace is about 150 words a minute, so each line below fits its slot.

Record the deployed app at
https://pinelabs-ai-analyst-nlszjuhrufcg9lmk9b6tjv.streamlit.app/ in a
1920 x 1080 browser window. With no key, the demo questions replay, so the
take cannot fail on a rate limit.

The Manim segment goes in after step 1. Every number in it comes from
`payments.duckdb` (duplicates removed), so it matches the app.

| Time | Section | Length |
|------|---------|--------|
| 0:00 | Problem | 15 s |
| 0:15 | Step 1: Why did success rate drop in Week 6? | 25 s |
| 0:40 | Manim: Mix effect vs Rate effect | 25 s |
| 1:05 | Step 2: Which bank got worse on cards? | 20 s |
| 1:25 | Step 3: An ambiguous question | 15 s |
| 1:40 | Step 4: A Merchant manager is blocked | 15 s |
| 1:55 | Step 5: Duplicates found and excluded | 15 s |
| 2:10 | Step 6: The known-answer eval | 15 s |
| 2:25 | Close | 10 s |

## 0:00 Problem (15 s)

**Screen:** the app's opening page, garden in day palette.

**Say:** "When a payments leader asks why success rate changed, an analyst
spends hours finding the right tables and writing SQL. This is an AI analyst
that answers in seconds, and shows the query and the caveats behind every
number."

## 0:15 Step 1: Why did success rate drop in Week 6? (25 s)

**Screen:** the default question is already in the box. Press Enter. Scroll
through the headline, the bridge chart and the SQL.

**Say:** "Success rate fell four percentage points from Week 5 to Week 6. The
obvious story is that something broke. The analyst says no: almost all of the
drop is a Mix effect. Traffic moved to payment methods that always succeed
less, while each method's own rate held. Here is the SQL it ran."

## 0:40 Manim: Mix effect vs Rate effect (25 s)

**Scene 1 (8 s).** Four bars, one per payment method. Width is the share of
Attempts, height is the Success rate. Week 5:

| Method | Share | Success rate |
|--------|-------|--------------|
| UPI | 61% | 95.5% |
| Card | 29% | 91.5% |
| Netbanking | 6% | 78.1% |
| Wallet | 4% | 79.9% |

The overall rate, 92.7%, is drawn as a line across the bars.

**Scene 2 (8 s).** The bars change width to Week 6 and keep their height:
UPI 44%, Card 20%, Netbanking 20%, Wallet 16%. The overall line slides down
to 88.7%.

**Scene 3 (9 s).** The two formulas appear, then a bridge: Week 5 92.7%, Mix
effect −3.99 percentage points, Rate effect −0.01 percentage points, Week 6
88.7%. Fall in orange, as in the app.

**Say:** "Each bar is a payment method: its width is its share of traffic,
its height is its success rate. In Week 6 the heights stay put. Only the
widths change, as traffic moves from UPI to netbanking and wallets. That
shift alone pulls the average down. The Mix effect explains nearly all of
the drop; the Rate effect is close to zero."

## 1:05 Step 2: Which bank got worse on cards? (20 s)

**Screen:** type "Which bank got worse on cards in wk7?" and press Enter.
Point at Coastal Bank in the bridge chart.

**Say:** "Now a real drop. On cards in Week 7, the change is inside the
banks, not in the mix. Coastal Bank fell from 91.5% to 77.8%. Its 95%
interval is clear of zero, so this is not noise."

## 1:25 Step 3: An ambiguous question (15 s)

**Screen:** type "How's success rate lately?" and press Enter. Point at the
stated assumption.

**Say:** "This question names no period. The analyst does not guess
silently: it states its assumption, the latest two weeks, and answers that."

## 1:40 Step 4: A Merchant manager is blocked (15 s)

**Screen:** switch the role to Merchant manager. The garden turns to night.
Type "Show me settlements" and press Enter.

**Say:** "A Merchant manager sees only their own category and no settlement
data. The SQL validator rejects this request and says why, before anything
runs."

## 1:55 Step 5: Duplicates found and excluded (15 s)

**Screen:** switch back to Analyst. Type "How many duplicate transactions are
there?" and press Enter. Point at the data-quality warning.

If this answer does not show the line "2,252 Duplicates … excluded; the first
copy is kept", point at it on the Week 6 answer instead.

**Say:** "The data has 2,252 duplicate transaction rows. The analyst finds
them, removes them before counting any metric, and says so on the answer."

## 2:10 Step 6: The known-answer eval (15 s)

**Screen:** press "Run eval". Show the Pass column.

**Say:** "Finally, the eval. Ten known-answer questions with expected numbers
run through the same pipeline, and all ten pass."

## 2:25 Close (10 s)

**Screen:** the README's architecture diagram on GitHub.

**Say:** "Numbers always come from executed SQL; the model only plans and
narrates. The code, the eval and the design notes are in the repository."
