# Grilling log: Enterprise AI Business Analyst (Pine Labs Case Study 02)

Full brief: [brief.md](brief.md). Deadline: **22 Nov 2026, 6:00 PM IST**. Demo-ready target: **22 Nov 12:00 PM IST**.

## Settled decisions (rounds 1-2, 21 Nov 2026)

| # | Decision | Answer |
|---|----------|--------|
| D1 | LLM default | `claude-haiku-5-5` ($0.10/$0.50 per MTok). Escalate to `claude-sonnet-5-5` only if Haiku fails eval questions. |
| D2 | Model switching | UI dropdown to switch model. Providers: Anthropic (Haiku/Sonnet) + an OpenRouter free model. |
| D3 | Deployed-app cost | Anthropic console spend limit **$5**, per-session question cap. |
| D4 | Replay mode | The 6 demo questions are cached as JSON, so the deployed link never shows an error, even with no key or quota. |
| D5 | Repo | `aaryan-pradhan/pinelabs-ai-analyst`, **private** until submission, then public. Commits straight to `main`, small. |
| D6 | LLM/deterministic split | Hybrid: the LLM emits a JSON plan chosen from the semantic layer, and Python compiles the SQL for metric questions. Free LLM SQL only for ad-hoc questions, always through the `sqlglot` validator. Decomposition is pure Python. |
| D7 | Stack | Python, DuckDB (read-only, timeout), sqlglot, Streamlit, Plotly, pandas. |
| D8 | Deploy | Streamlit Community Cloud from the private repo (1 private app is free) as soon as a slice works; flip to public at submission. |
| D9 | Prior art | Background research agent writes [prior-art.md](prior-art.md). Borrow ideas; copying open-source code is fine only when its license allows it, with attribution. Do not copy other candidates' Pine Labs submissions. |
| D10 | Video | 2-2.5 min screen recording of the 6-step demo + a 20-30 s Manim segment explaining mix-vs-rate. Made only after the app is demo-ready. |
| D11 | Process | `docs/PLAN.md` then `docs/SPEC.md` then GitHub issues (vertical slices, riskiest first, closed with `Closes #n`). |
| D12 | Submission | Aaryan logs in to pinelabs.ai (institute email + OTP) on the night of 21 Nov; Claude reads the form via Chrome; Aaryan clicks Submit. |

## Open questions (next round)

Proposed in round 2 but not yet explicitly confirmed:

- **Q7 Data shape:** 8 weeks (28 Sep - 22 Nov 2026), ~150k txns, fixed seed, UPI/card/netbanking/wallet, ~8 fictional banks, ~300 merchants, 6 categories, 3 tiers.
- **Q8 Planted stories:** (a) wk 6 mix shift: a festive-sale merchant pushes traffic to netbanking/wallet; overall -4pp, each method flat within +/-0.3pp. (b) wk 7 genuine drop: one bank's card success 92% to 78%. (c) ~1.5% duplicate `txn_id` + nulls in `failure_reason`/`bank_id`/`amount`. (d) wk 5 settlements 3% below successful txn value for one category (delayed settlement).
- **Q9 Roles:** `analyst` (all) and `merchant_manager` (one category, no `settlements`); sidebar dropdown, auth mocked.
- **Q10 Ambiguity:** default + visible "Assumption" chip, editable and re-runnable; ask back only when no sensible default exists.

Still to grill after these: semantic-layer metric list, answer-card layout, DQ check list, eval question set, model-switch UI details, OpenRouter model choice.
