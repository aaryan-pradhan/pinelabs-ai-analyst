# Grilling log: Enterprise AI Business Analyst (Pine Labs Case Study 02)

Full brief: [brief.md](brief.md). Deadline: **22 Nov 2026, 6:00 PM IST**. Demo-ready target: **22 Nov 12:00 PM IST**.

## Settled decisions (rounds 1-3, 21 Nov 2026)

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
| D13 | Data shape | 8 Weeks (Mon 28 Sep - Sun 22 Nov 2026; wk6 = Diwali week). ~150k Attempts, fixed seed, UPI/card/netbanking/wallet, ~8 fictional banks (public/private/foreign), ~300 merchants, 6 categories, 3 tiers, ~10 cities. Status only success/failed. |
| D14 | Planted stories | (a) wk6 mix shift: festive-sale merchant pushes traffic to netbanking/wallet; overall -4pp, each method flat within +/-0.3pp. (b) wk7 genuine drop: one bank's card success 92% to 78%. (c) ~1.5% exact-duplicate `txn_id` rows (keep first) + nulls in `failure_reason`/`bank_id`/`amount`. (d) wk5 Settlements 3% below successful value for one category. Settlements keyed by txn date, gross, no fees; Source mismatch above 0.5%. |
| D15 | Roles | `analyst` (all) and `merchant_manager` (one category, no `settlements`); sidebar dropdown, auth mocked. Enforced in the validator (SQL rewrite adds the category filter; `settlements` rejected), not by prompt. |
| D16 | Ambiguity | Default + visible Assumption chip, editable and re-runnable; ask back only when no sensible default exists. Defaults: latest complete week vs previous; denominator = all Attempts excluding Duplicates. |
| D17 | Answer card | Headline, Assumption chips, chart, Facts (each with SQL/tables/filters/window expander), Hypotheses, Recommendations, Caveats (DQ warnings + confidence). Facts only from executed numbers; Hypotheses/Recommendations labelled as LLM narration. |
| D18 | Model use | Replay cache for the demo questions is generated with the best model, so it reads well. Live use defaults to the cheapest (D1). Model dropdown in sidebar; replay auto-on with banner when no key or cap hit. OpenRouter model picked and verified at build time; OpenRouter is the last slice and is cut first if time is short. |
| D19 | Success rate | Successful Attempts / all Attempts after removing Duplicates; null `failure_reason` still counts. Terms in [GLOSSARY.md](../GLOSSARY.md). |

## Open questions (next round)

- Which model generates the replay cache (D18 "best model")?
- "Show a very good success rate": eval pass rate, or the baseline level of the metric?
- Semantic-layer metric and dimension list.
- DQ check list.

Still to grill after these: eval question set.
