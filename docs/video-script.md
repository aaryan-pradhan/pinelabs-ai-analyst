# Video script

The video tells one story: a Head of Payments has a bad Monday, and the AI
analyst gets them through it. Every point Pine Labs evaluates appears in the
story at the moment it is needed. How the analyst works is explained only at
the end, once the viewer has seen why it matters.

The form allows 2 to 5 minutes; at a relaxed pace the script reads in about
4 minutes 45 seconds.

## How the video is made

The voice comes first, and the video is built to fit it.

1. **Voice.** Aaryan reads each chapter's "Say" text into its own audio file,
   `ch0.m4a` to `ch9.m4a`. A bad take is re-recorded on its own.
2. **Timing.** Each file is transcribed with word timestamps, so every zoom
   and every typed question lands on the word that names it.
3. **Screen clips.** A scripted browser run of the deployed app records each
   chapter's actions at that timing, with smooth zooms. Chapters 2 and 9 are
   Manim animations, timed the same way.
4. **Merge.** Each clip is joined to its voice file, and the ten chapters are
   joined into one video.

Deployed app: https://pinelabs-ai-analyst-nlszjuhrufcg9lmk9b6tjv.streamlit.app/

## Chapter 0: The hook

**The viewer must understand:** the business problem, in human terms.

**Screen:** Pine Labs' problem statement, with a slow zoom onto its Goal line:
"turn a natural-language business question into safe, reproducible data
analysis and an evidence-backed answer." Then cut to the app's opening page,
garden in its day palette.

**Say:**
"It's Monday morning. You run payments for thousands of merchants, and your
dashboard says success rate fell four points last week. Your CEO wants to know
why by noon. Pine Labs asked for an AI analyst that can answer that. Here it
is."

## Chapter 1: The scare

**The viewer must understand:** one question returns a complete, checkable
answer, with Facts kept apart from Hypotheses and Recommendations.

**Screen:** Role is Analyst. Type "Why did success rate drop in week 6?" and
press Enter. Zoom in turn onto:

1. The headline.
2. The bridge chart (Exhibit A).
3. One Fact, with its table, filters and time window.
4. The Hypotheses, then the Recommendations.
5. The SQL.

Zoom back out onto the bridge chart for the last line.

**Say:**
"So we ask it exactly that: why did success rate drop in Week 6? First, the
headline. Success rate fell from 92.7% to 88.7%. Then the evidence. Every
number is a Fact, and each one cites its table, its filters and its time
window. Kept apart from the Facts are the Hypotheses, what might explain it,
and the Recommendations, what to check next. And here is the exact SQL it ran,
so nothing is taken on trust. But look at the chart. Almost all of the drop is
a Mix effect. So what actually happened?"

## Chapter 2: Nothing broke

**The viewer must understand:** the average fell although no payment method
got worse, because traffic moved (Simpson's paradox).

**Scene 1.** Four bars, one per payment method. Width is the share of
Attempts, height is the Success rate. Week 5:

| Method | Share | Success rate |
|--------|-------|--------------|
| UPI | 61% | 95.5% |
| Card | 29% | 91.5% |
| Netbanking | 6% | 78.1% |
| Wallet | 4% | 79.9% |

The overall rate, 92.7%, is a line across the bars.

**Scene 2.** The bars change width to Week 6 and keep their height: UPI 44%,
Card 20%, Netbanking 20%, Wallet 16%. The overall line slides down to 88.7%.

**Scene 3.** A bridge: Week 5 92.7%, Mix effect −3.99 percentage points, Rate
effect −0.01 percentage points, Week 6 88.7%. Fall in orange, as in the app.

All numbers come from `payments.duckdb` with Duplicates removed.

**Say:**
"Nothing broke. Each bar is a payment method. Its width is its share of
traffic, its height is its success rate. From Week 5 to Week 6, the heights
don't move. Only the widths do. Traffic moved from UPI and cards to netbanking
and wallets, which always succeed less. That alone pulls the average down. The
Mix effect is minus four points. The Rate effect is almost zero."

## Chapter 3: Now a real problem

**The viewer must understand:** the same tool tells a real failure apart from
a mix shift, and finds the one bank responsible.

**Screen:** Type "Which bank got worse on cards in wk7?" and press Enter. Zoom
onto the headline, then onto Coastal Bank in the bridge chart with its 95%
interval, then onto the Recommendations.

**Say:**
"A week later, card payments dip by almost two points. Is this another mix
shift? We ask which bank got worse on cards in Week 7. This time the answer is
different. The drop is inside one bank. Coastal Bank fell from 91.5% to 77.8%.
Its 95% interval is nowhere near zero, so this is not noise. This one is real,
and the Recommendations say what to check next."

## Chapter 4: Did it get fixed?

**The viewer must understand:** an ambiguous question gets a stated, editable
assumption instead of a silent guess.

**Screen:** Type "How's success rate lately?" and press Enter. Zoom onto the
Window chip ("Week 7 vs Week 8") and open it to show it can be changed. Close
it, then zoom onto the headline naming Coastal Bank.

**Say:**
"Your CEO then asks: how's success rate lately? That's vague. Lately since
when? The analyst doesn't guess silently. It states its assumption, the latest
two weeks, and you can change it right here. And the answer closes the story:
Coastal Bank is back, up four points in Week 8."

## Chapter 5: Finance joins in

**The viewer must understand:** when two sources disagree, the analyst says
which, where and by how much.

**Screen:** Type "Do settlements match transactions in wk5?" and press Enter.
Zoom onto the headline, then onto electronics in the by-category table.

**Say:**
"Next, finance asks: does the money match? Settlements are the money actually
paid out to merchants. The analyst checks them against successful payments,
category by category. In Week 5, electronics merchants were paid about 3% less
than their payments add up to. Two sources disagree, and the analyst says
exactly where."

## Chapter 6: A merchant manager logs in

**The viewer must understand:** each role sees only its own data, and the
system enforces that before any query runs.

**Screen:** Switch Role to Merchant manager, Category grocery. Zoom out to
show the garden turning to night. Type "Show me settlements" and press Enter;
zoom onto the rejection reason. Then type "What is the success rate for
electronics?" and press Enter; zoom onto the rejection reason.

**Say:**
"Now a different user logs in: a merchant manager for grocery. The garden
turns to night, so you always know whose view this is. They ask for
settlements and are refused, with the reason: only an Analyst can see
Settlements. They ask about electronics, a category that isn't theirs, and are
refused again. These rules are checked on the SQL itself, before any query
runs."

## Chapter 7: Someone tries something dangerous

**The viewer must understand:** the analyst cannot change or damage the data.

**Screen:** Switch Role back to Analyst. Type "Delete the failed
transactions" and press Enter. Zoom onto the rejection reason.

**Say:**
"Then someone tries something dangerous: delete the failed transactions. The
analyst refuses. Only a single SELECT statement may run, so it can never
change the data."

## Chapter 8: Can we trust any of this?

**The viewer must understand:** the numbers are cleaned and the system is
tested against known answers.

**Screen:** Type "How many duplicate transactions are there?" and press
Enter. Zoom onto 2,252. Then press "Run eval" and zoom onto the pass rate,
then the Pass column.

**Say:**
"Last question: can you trust any of this? Real data is messy. This data has
2,252 duplicate rows. The analyst finds them, removes them before counting
anything, and says so on the answer. And it is tested. Ten questions with
known answers run through the same pipeline, including the refusals you just
saw. Ten out of ten pass."

## Chapter 9: How it works

**The viewer must understand:** the model never produces a number; every
number comes from validated, executed SQL.

**Scene.** A left-to-right pipeline that lights up one stage at a time, each
stage named as the narration reaches it: Question, Plan (semantic layer), SQL,
Validator, DuckDB, Analysis (decomposition, intervals, data checks), Answer. A
"Numbers" track runs underneath from DuckDB to Answer, and a separate "Words"
track from the model to Answer, so the split is visible. End on the README's
limitations section for the last two sentences.

**Say:**
"Here's how it works. Your question goes to a language model, but the model
never writes a number. It only picks a plan from a semantic layer: a fixed
list of metrics, like success rate, and the ways you can split them. That
keeps every definition the same. The plan becomes SQL, and a validator checks
it before it runs: SELECT only, known tables and columns only, and only what
your role may see. DuckDB runs it read-only, with a five-second limit. Then the
analysis: the mix-versus-rate split, confidence intervals, and data-quality
checks on every answer. Last, the model writes the story, using only the
computed Facts. The data is synthetic, generated with these stories planted,
and the login is mocked. The limitations and what comes next are in the
README."
