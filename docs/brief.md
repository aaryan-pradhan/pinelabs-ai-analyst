# Task: build "Enterprise AI Business Analyst" for the Pine Labs case study round

You are helping me (Aaryan, final-year IIT Kharagpur, B.Tech Chemical + M.Tech Financial Engineering, quant/data background) build and submit Pine Labs Case Study 02. Work with me step by step. Ask me before choosing anything that is mine to decide (LLM provider and API key, repo name).

## Hard deadline and submission
- Final submission: **22 Nov 2026, 6:00 PM IST**. No extensions, no late submissions.
- Submit on https://www.pinelabs.ai (login with my institute email + OTP; I do the login).
- Deliverables: a **public GitHub repository** (must be publicly accessible) and a **short video demo** (optional per the mail, but the site asks for it; we will make one, 2 to 3 minutes).
- One case study, one solution.
- Plan so a working, demo-able version exists by **22 Nov 12:00 PM IST**, leaving time for the README, video and submission.

## The problem (Pine Labs' brief, in full)

**Customer context.** A payments business has transaction, merchant, bank, payment-method and settlement data spread across several datasets. Leaders ask questions like "why did success rates change?", "which segments drove the decline?", "what should we do?". Analysts spend hours finding the right data and writing up explanations.

**Goal.** Build an AI analyst that turns a natural-language business question into safe, reproducible data analysis and an evidence-backed answer.

**Illustrative end-to-end journey.**
1. A business user asks a question about payment performance.
2. The system identifies the relevant datasets, measures and dimensions.
3. It generates a query or analysis plan and **validates it before execution**.
4. It executes against a supplied database or dataset.
5. It segments and compares results, makes visualisations and identifies plausible drivers.
6. It returns an answer with the query evidence, caveats and recommended next steps.

**Core requirements (must have).**
- At least two related datasets, e.g. transactions plus merchant/bank dimension tables.
- Natural-language questions about metrics and trends.
- Generate and execute SQL (or equivalent structured analysis).
- Show the query / analysis steps used.
- Charts or tables for key findings.
- Cite the dataset, filters and time window behind each conclusion.
- Clearly separate **observed facts** from **hypotheses** and **recommendations**.

**Advanced / stretch (only after core works).**
- Role-based access and query restrictions.
- Data-quality checks and missing-data warnings.
- Cohort comparison or drill-down analysis.
- Query cost / timeout controls and caching.
- Evaluate generated queries against known-answer test questions.
- Confidence and uncertainty explanations.

**Failure and exception scenarios to handle.**
- A dataset has missing or duplicated records.
- The user asks for data outside their access scope.
- Two sources disagree on the same metric (e.g. transactions vs settlements).
- A success-rate decline is actually explained by a **shift in transaction mix** (Simpson's-paradox style: every segment is flat, but traffic moved to a lower-success segment).
- The question is ambiguous about time period or denominator.
- A generated query is expensive or unsafe.

**Minimum successful demonstration.** A business question answered from the supplied data, with an executed query, segmented analysis, visual evidence and explicit caveats. Plus **at least one data-quality or access-control failure** shown being handled.

**What they are evaluating.** Analytical reasoning, data modelling, safe text-to-SQL, business interpretation, and the ability to substantiate AI-generated conclusions.

**Scope note from Pine Labs.** Build a coherent, working vertical slice, not every enterprise feature or production infrastructure. State assumptions, mocked dependencies and limitations clearly.

## Suggested build (keep it simple; change only with a reason)
- **Stack:** Python, SQLite (or DuckDB), Streamlit for the UI, an LLM API for planning/SQL/narration, pandas + Plotly/Altair for charts. One repo, runs with `pip install -r requirements.txt && streamlit run app.py`.
- **Synthetic data (seeded, reproducible generator script):**
  - `transactions` (txn_id, ts, merchant_id, bank_id, payment_method [UPI/card/netbanking/wallet], amount, status [success/failed], failure_reason, …), about 8 weeks, 100k+ rows.
  - `merchants` (merchant_id, name, category, city, tier), `banks` (bank_id, name, type), `settlements` (merchant_id, date, settled_amount, settled_count).
  - **Plant the stories** the demo will find: (a) a week where overall success rate drops only because traffic shifted to a low-success method/bank (mix shift); (b) a real drop at one bank on one method (genuine degradation); (c) some duplicate txn rows and missing values; (d) a settlement total that disagrees with transactions for a period.
- **Pipeline per question:**
  1. Parse intent; if time window or denominator is ambiguous, state the assumption made (or ask).
  2. Build a plan using a **semantic layer**: a small YAML/dict of defined metrics (e.g. success_rate = successful txns / all attempted txns, excluding duplicates), dimensions and allowed joins. The LLM picks from it, so metric definitions stay consistent.
  3. Generate SQL; **validate before running**: SELECT-only (parse with `sqlglot`), allowed tables/columns per role, a LIMIT, a row/time budget, no cross joins without keys. Reject or rewrite unsafe queries and say why.
  4. Execute read-only, with a timeout. Cache results.
  5. Analysis: compare periods; segment by method/bank/merchant category; run a **mix-vs-rate decomposition** of the change in success rate (rate effect vs mix effect per segment). This is the centrepiece.
  6. Data-quality checks run on every answer: duplicates, nulls, coverage gaps, source mismatch. Surface warnings.
  7. Answer card: headline, **Facts** (each with the SQL, table, filters, time window), **Hypotheses**, **Recommendations**, **Caveats/confidence**, chart(s).
- **Access control:** 2 roles (e.g. `analyst` sees everything; `merchant_manager` sees only their merchant category, no settlement data). Demo a blocked request.
- **Evaluation:** 8 to 10 known-answer questions with expected numbers; a script that runs them and reports pass/fail.

## Demo script (for the video)
1. "Why did payment success rate drop in week X?" The answer shows a mix shift, not degradation, with the decomposition chart and the SQL.
2. "Which bank got worse on cards?" It finds the genuine drop.
3. An ambiguous question; the stated assumption is shown.
4. The `merchant_manager` role asks for settlement data and is blocked, with the reason.
5. Data-quality warning: duplicates are found and excluded, and the warning is shown on the answer.
6. Run the known-answer eval and show the pass rate.

## README must include
Problem summary, architecture diagram (simple), how to run, data model, metric definitions, the safety checks, roles, eval results, assumptions, what is mocked (synthetic data), limitations, and what I would do next.

## How to work with me
- Start by confirming the plan and asking me for the LLM provider/key. Then build in this order: data generator, semantic layer + safe SQL, analysis + decomposition, UI, DQ + access control, eval, README, video.
- Commit small and often. The repo must be public before submission.
- Never put API keys in the repo (use `.env`, gitignored).
