# Prior art for the Enterprise AI Business Analyst

Research date: 2026-11-21. Star counts, licenses and push dates are what the GitHub API returned on that date (`gh api repos/OWNER/REPO`). Where a number was not seen, it is left out. Web results are mostly vendor or blog pages, so treat their numbers as claims, not proof.

## Every query run

### Web searches (22)

1. open source AI data analyst text-to-SQL agent GitHub
2. semantic layer LLM text-to-SQL dbt semantic layer MetricFlow accuracy
3. WrenAI semantic layer GenBI open source
4. Vanna.ai text-to-SQL RAG github
5. DataHerald NL-to-SQL engine open source
6. text-to-SQL safety guardrails sqlglot validate read-only SELECT only LLM
7. text-to-SQL evaluation execution accuracy BIRD Spider known-answer tests
8. mix shift vs rate change decomposition conversion rate Simpson's paradox automated analysis
9. PandasAI conversational data analysis open source
10. LangChain SQL agent LlamaIndex NLSQLTableQueryEngine safety read-only
11. DB-GPT Chat2DB SQLCoder DIN-SQL comparison open source text2sql
12. Cube semantic layer AI agent natural language queries metrics
13. root cause analysis metric change KPI driver analysis open source Python
14. LinkedIn ThirdEye anomaly detection root cause analysis Sisu Outlier automated insights
15. DoWhy root cause analysis metric change attribution
16. payment success rate analysis dashboard failure reasons issuer bank payment method
17. Pine Labs AI analyst case study AI builder hiring
18. "Pine Labs" "AI Business Analyst" github
19. AI business analyst Streamlit app natural language to SQL DuckDB charts
20. hackathon AI analyst agent natural language questions data warehouse hypotheses recommendations repo
21. Kitagawa decomposition rate effect composition effect conversion funnel python
22. LLM data analyst agent data quality checks duplicates nulls before answering

### GitHub repo searches (`gh search repos "<q>" --limit 15 --json fullName,description,stargazersCount,updatedAt,license`)

gh wraps multi-word terms in quotes, so exact-phrase queries often return nothing. Empty results are marked.

23. pine labs
24. pinelabs analyst (no results)
25. ai business analyst
26. text to sql streamlit duckdb (no results)
27. semantic layer llm
28. text2sql guardrails sqlglot (no results)
29. mix shift decomposition (no results)
30. payment success rate analysis (no results)
31. ai data analyst agent
32. nl2sql evaluation
33. pine labs case study (no results)
34. pinelabs ai
35. text2sql sqlglot (no results as exact phrase; see 38 for the re-run)
36. text-to-sql duckdb streamlit (no results)
37. text2sql guardrails (re-run, `--sort stars`, unquoted)
38. sqlglot text-to-sql (`--sort stars`)
39. text-to-sql duckdb (`--sort stars`)
40. mix shift (`--sort stars`, only noise: audio/shift apps and two KPI essays)
41. payment success rate (`--sort stars`, only noise)
42. nl2sql (`--sort stars`)
43. pine labs analyst (`--sort stars`, no results)
44. pinelabs hackathon (`--sort stars`)
45. text-to-sql eval (`--sort stars`)

One batch of 9 repo searches (mix shift decomposition, payment success rate analysis, ai data analyst agent, nl2sql evaluation, pine labs case study, pinelabs ai, text2sql sqlglot, text-to-sql duckdb streamlit, pine labs hackathon) hit `HTTP 403: API rate limit exceeded` and was re-run after a pause (rows 29-36 above; "pine labs hackathon" became row 44).

### GitHub code searches (`gh search code`)

46. sqlglot SELECT only guard language:python
47. mix effect rate effect decomposition language:python (noise only)
48. success_rate mix_effect rate_effect (no results)

### README and metadata reads (`gh api repos/OWNER/REPO/readme`, `gh api repos/OWNER/REPO`)

READMEs read: dbt-labs/semantic-layer-llm-benchmarking, fafa-ai-data-lab/ai-data-analyst-agent, jlcoto/the_honest_agent, fengyede79/text-to-sql-agent-system, Prennoy99/chartersense, rranjanyyadav/late-delivery-investigator, coolpinkzz/pinelabs-ai-merchant-copilot (empty README), gkdivya/pine_labs_assistant, krishnadev-ss/pine-ai, arnavgupta28/checkoutiq-pinelabs, empower-ai/dsensei, NVIDIA/auto-ontology-eval, holoviz/lumen.
Metadata only (stars, license): vanna-ai/vanna, Canner/WrenAI, dbt-labs/metricflow, py-why/dowhy, Sinaptik-AI/pandas-ai, Dataherald/dataherald, cube-js/cube, salesforce/PyRCA, taoyds/test-suite-sql-eval, defog-ai/sqlcoder, eosphoros-ai/DB-GPT, CodePhiliaX/Chat2DB, tobymao/sqlglot, plural-pinelabs/pinelabs-online-mcp. Not found at the path tried: microsoft/lumos, MinghuiTang/DIN-SQL.

## Top 10 to learn from

Reuse column: "reuse OK" means a permissive license was seen (still check attribution). "Ideas only" means no license, copyleft, or non-standard license.

| # | Name | Stars | License | What it does | Idea to borrow | Reuse |
|---|------|-------|---------|--------------|----------------|-------|
| 1 | [rranjanyyadav/late-delivery-investigator](https://github.com/rranjanyyadav/late-delivery-investigator) | 0 | none seen | Streamlit + DuckDB analyst for Olist orders. YAML semantic layer, SELECT-only SQL guard, LLM returns a JSON plan (metric / sql / drilldown / cannot_answer), 20 gold-question eval ([README](https://github.com/rranjanyyadav/late-delivery-investigator)) | Closest match to our whole stack. Copy the shape: drill-down that splits a ratio change into per-segment rate vs mix effects that sum exactly to the change; loader with 19 data-quality checks; explanation may only use numbers from results | Ideas only (no license) |
| 2 | [Prennoy99/chartersense](https://github.com/Prennoy99/chartersense) | 0 | MIT | Versioned YAML semantic layer, LLM SQL, SELECT-only guard plus a read-only DB role, answers diffed against independently computed ground truth ([README](https://github.com/Prennoy99/chartersense)) | Two independent safety layers (DB role plus AST guard). Ground-truth SQL written without the LLM, diffed in `validate_e2e.py` | Reuse OK (MIT) |
| 3 | [fengyede79/text-to-sql-agent-system](https://github.com/fengyede79/text-to-sql-agent-system) | 80 | MIT | LangGraph text-to-SQL agent. sqlglot AST safety check (read-only, multi-statement, DDL/DML, comment injection, `SELECT *`, unknown tables/columns, LIMIT clamp), bounded self-correction, scenario eval suite ([README, in Chinese](https://github.com/fengyede79/text-to-sql-agent-system)) | The checklist of validator rules; bounded repair budget; stop repairing when the request is destructive instead of "fixing" it | Reuse OK (MIT) |
| 4 | [jlcoto/the_honest_agent](https://github.com/jlcoto/the_honest_agent) | 9 | MIT | Eval harness: asks an analytics agent questions with known answers, grades accuracy and provenance (did the SQL read the right tables), stores runs in DuckDB, builds a report ([README](https://github.com/jlcoto/the_honest_agent)) | Grade two things per known-answer case: is the number right, and did the SQL touch the expected tables. Run each case several times and track a pass threshold | Reuse OK (MIT) |
| 5 | [Canner/WrenAI](https://github.com/Canner/WrenAI) | 18354 | NOASSERTION in API; README says the engine is Apache-2.0 ([README](https://raw.githubusercontent.com/Canner/WrenAI/HEAD/README.md)) | Open GenBI engine around an MDL semantic layer stored as text in Git, governed text-to-SQL, MCP server | Define metrics/models/relationships once in text, and make the LLM plan against those, not raw tables | Ideas only (license field is ambiguous) |
| 6 | [dbt-labs/semantic-layer-llm-benchmarking](https://github.com/dbt-labs/semantic-layer-llm-benchmarking) | 59 | Apache-2.0 | Benchmark of LLM questions through the dbt semantic layer ([README](https://github.com/dbt-labs/semantic-layer-llm-benchmarking)). The [2026 dbt post](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026) reports 98.2% via semantic layer vs 90.0% raw text-to-SQL for Claude Sonnet 4.6, and that the layer declines out-of-scope questions (vendor-run, 11 questions) | Prefer "pick a metric" over "write free SQL"; when a question is outside the semantic layer, say so rather than guess | Reuse OK (Apache-2.0) |
| 7 | [vanna-ai/vanna](https://github.com/vanna-ai/vanna) | 23789 | MIT | RAG text-to-SQL: store DDL, docs and example question/SQL pairs in a vector store ([search summary](https://github.com/vanna-ai/vanna)). Repo shows `archived=true`, last push 2026-02-02 | Few-shot store of verified question/SQL pairs; our eval cases can double as these examples | Reuse OK (MIT), but archived |
| 8 | [empower-ai/dsensei](https://github.com/empower-ai/dsensei) | 261 | GPL-3.0 | Key driver analysis: finds which segments explain a metric change ([README](https://github.com/empower-ai/dsensei)). Last push 2023-12-01 | Rank segments by share of the change vs share of the base. See also the [KPI-change article](https://towardsdatascience.com/making-sense-of-kpi-changes/) | Ideas only (GPL) |
| 9 | [taoyds/test-suite-sql-eval](https://github.com/taoyds/test-suite-sql-eval) | 322 | Apache-2.0 | Execution-based text-to-SQL eval using distilled test databases to cut false positives ([paper-linked repo](https://github.com/taoyds/test-suite-sql-eval)) | Compare result sets, not SQL text; test on more than one data variant so a wrong query cannot pass by luck | Reuse OK (Apache-2.0) |
| 10 | [fafa-ai-data-lab/ai-data-analyst-agent](https://github.com/fafa-ai-data-lab/ai-data-analyst-agent) | 46 | MIT | Methodology and templates: metric registry first, a separate read-only validator agent, a growing rule list, a provenance footer on every number ([README](https://github.com/fafa-ai-data-lab/ai-data-analyst-agent)) | Provenance footer (metric definition, data freshness, source table, who checked it) on each fact in the answer card | Reuse OK (MIT) |

## By theme

### Text-to-SQL agents

- [vercel-labs/oss-data-analyst](https://github.com/vercel-labs/oss-data-analyst): Next.js agent with Planning, Building, Execution, Reporting steps ([search result](https://vercel.com/templates/ai/oss-data-analyst-agent-reference-architecture)). Take: the four-stage flow maps to our pipeline. Stars/license not checked; one result says it is deprecated.
- [Dataherald/dataherald](https://github.com/Dataherald/dataherald): NL-to-SQL engine, 3651 stars, Apache-2.0, last push 2024-07-24; YC profile says the company is [inactive](https://www.ycombinator.com/companies/dataherald). Take: golden question/SQL pairs as context. Treat as dated.
- [Sinaptik-AI/pandas-ai](https://github.com/Sinaptik-AI/pandas-ai): chat with dataframes by generating Python; 23957 stars, license NOASSERTION; docs say it is [not meant for production](https://pypi.org/project/pandasai/). Take: avoid generated-Python execution; our SELECT-only SQL path is safer.
- [holoviz/lumen](https://github.com/holoviz/lumen): agent framework for SQL, charts and dashboards; 356 stars, BSD-3-Clause ([README](https://github.com/holoviz/lumen)). Take: every LLM output is inspectable and editable by the user.
- [eosphoros-ai/DB-GPT](https://github.com/eosphoros-ai/DB-GPT) (20320 stars, MIT), [CodePhiliaX/Chat2DB](https://github.com/CodePhiliaX/Chat2DB) (28370 stars, NOASSERTION), [defog-ai/sqlcoder](https://github.com/defog-ai/sqlcoder) (4045 stars, Apache-2.0): large general tools and a fine-tuned SQL model. Take: nothing needed; too heavy for a case study. [DB-GPT-Hub](https://github.com/csunny/DB-GPT-Hub) is the benchmarking side ([paper](https://arxiv.org/html/2406.11434v1)).
- DIN-SQL: four steps (schema linking, classification/decomposition, generation, self-correction), prompting only ([survey text](https://arxiv.org/html/2406.11434v1)). Take: schema linking before generation helps on big schemas; ours is small, so the semantic layer does this job.
- [Datus](https://pypi.org/project/datus-agent/0.3.7/) and [OpenChatBI](https://zhongyu09.github.io/openchatbi): agent products with built-in eval and chat BI ([search result](https://raw.githubusercontent.com/zhongyu09/openchatbi/HEAD/README.md)). Take: Datus ships a BIRD/Spider evaluation framework.
- [LangChain SQL agent docs](https://docs.langchain.com/oss/javascript/langchain/sql-agent): the write ban is only prompt text unless you add a gate ([analysis](https://open-agent-ai-security.github.io/praxen/tests/baselines/v0.7.7-claude48/langchain-sql/langchain-sql-analysis-2026-05-29-170813.html)). Take: never rely on prompts for safety. [LlamaIndex DuckDB example](https://developers.llamaindex.ai/python/examples/index_structs/struct_indices/duckdb_sql_query/) warns of the same risk.

### Semantic layers

- [dbt Labs: semantic layer vs text-to-SQL, 2026](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026): vendor benchmark, semantic layer more accurate and declines what it cannot model. Take: "decline" is a feature; add a `cannot_answer` path.
- [dbt-labs/metricflow](https://github.com/dbt-labs/metricflow): 1888 stars, Apache-2.0. Take: metric types (ratio, simple) and dimension joins as the vocabulary for our YAML.
- [Cube](https://cube.dev/articles/semantic-layer-for-ai-agents-2026) ([cube-js/cube](https://github.com/cube-js/cube), 21267 stars, NOASSERTION): agents request certified metrics and dimensions, not raw tables ([MCP article](https://cube.dev/articles/analytics-mcp-server)). Take: same principle, marketing source.
- [Canner/WrenAI](https://github.com/Canner/WrenAI): see Top 10.
- [arXiv 2608.16663](https://arxiv.org/pdf/2608.16663): "Bounded Semantic Planning and Deterministic Compilation": the LLM interprets the question, code writes the SQL. Not read beyond the title and summary. Take: LLM outputs a plan, a compiler writes SQL.
- [get-dst/dst](https://github.com/get-dst/dst) (18 stars, Apache-2.0), [ralforion/orionbelt-semantic-layer](https://github.com/ralforion/orionbelt-semantic-layer) (104 stars, license "other"): small semantic-layer-plus-MCP projects seen in search only.

### SQL safety and validation

- [sql-guardrail (PyPI)](https://pypi.org/project/sql-guardrail/): sqlglot-based allowlist of SELECT/UNION/INTERSECT/EXCEPT, rejects data-modifying CTEs. Take: test the WITH-wrapped write case explicitly.
- [readonly-sql-guard (PyPI)](https://pypi.org/project/readonly-sql-guard/): argues shape checks are not enough (a SELECT can read files or open connections). Take: block file/network functions (DuckDB `read_csv`, `httpfs`) and disable external access in the connection.
- [Atlas survey on query validation gates](https://laoujin.github.io/Atlas/research/2026-06-09-audit-and-harden-text-to-sql-pipelines-2026/query-validation-and-safety-gates/): layered chain: statement-type allowlist, AST check, schema binding, policy injection, read-only connection; warns that LLM repair loops can drop safety filters. Take: re-validate after every repair, and never let repair remove a role filter.
- [7-layer NL2SQL guardrail write-up](https://dev.to/soham__11/how-i-built-a-7-layer-nl2sql-guardrail-stack-for-a-fortune-500-enterprise-2jgi) and [safe text-to-SQL write-up](https://dev.to/kowshik_jallipalli_a7e0a5/safe-text-to-sql-giving-an-agent-database-access-without-dropping-tables-or-leaking-pii-i47): blog overviews. Take: PII column blocking by role.
- [sparklingneuronics/access-aware-text-to-sql](https://github.com/sparklingneuronics/access-aware-text-to-sql) (3 stars, MIT): deterministic guard enforcing each user's data-access rules. Take: role-to-table/column allowlist enforced in code.
- [Azoqoz/Text-to-SQL-with-Guardrails](https://github.com/Azoqoz/Text-to-SQL-with-Guardrails) (4 stars, no license): read-only execution plus role-based access. Ideas only.
- [chaithanyabs441-ux/text2sql-with-guardrails](https://github.com/chaithanyabs441-ux/text2sql-with-guardrails) (0 stars, MIT): AST policy checks, read-only sandbox. Small, unverified.
- [tobymao/sqlglot](https://github.com/tobymao/sqlglot): 9809 stars, MIT; the parser we already plan to use.
- Code-search hits for `guard.py` / `sql_guard.py` files, e.g. [PruthviVKadam/sql-copilot](https://github.com/PruthviVKadam/sql-copilot), [Vanshpanchal/query_smith](https://github.com/Vanshpanchal/query_smith): many small guard implementations exist; license not checked.

### Evaluation of text-to-SQL

- [Execution accuracy vs exact match, Spider/BIRD](https://arxiv.org/pdf/2407.07313v4): EX compares result sets; exact match misses equivalent SQL; EX has known false-positive limits ([ETM paper](https://arxiv.org/pdf/2407.07313v4)). Take: grade by result set, with tolerance for column order and float rounding.
- [taoyds/test-suite-sql-eval](https://github.com/taoyds/test-suite-sql-eval): see Top 10.
- [NVIDIA/auto-ontology-eval](https://github.com/NVIDIA/auto-ontology-eval): 184 stars, Apache-2.0; A/B arms (schema-only control vs treatment), deterministic verifier, lists questions fixed and broken ([README](https://github.com/NVIDIA/auto-ontology-eval)). Take: run the same eval with and without the semantic layer to prove it helps.
- [IBM/text2sql-eval-toolkit](https://github.com/IBM/text2sql-eval-toolkit) (19 stars, Apache-2.0) and [timescale/text-to-sql-eval](https://github.com/timescale/text-to-sql-eval) (3 stars, PostgreSQL license): modular eval frameworks seen in search only.
- [jlcoto/the_honest_agent](https://github.com/jlcoto/the_honest_agent): see Top 10.
- BIRD/Spider scores for context: BIRD-Dev about 70-73% for strong systems ([search summary](https://arxiv.org/pdf/2510.17586)). Take: public benchmarks are not our target; a small domain gold set is.

### Automated driver and mix-vs-rate analysis

- [Koji: mix shift decomposition](https://www.koji.so/docs/mix-shift-rate-composition-decomposition): Kitagawa split into rate and composition parts. [MetricGate Kitagawa page](https://metricgate.com/docs/kitagawa-decomposition/) gives the symmetric formula: rate effect = sum of average weights times rate differences; composition effect = sum of average rates times weight differences; they add to the total. Take: use this symmetric form so the two parts sum exactly.
- [TryAnalyze worked example](https://www.tryanalyze.ai/answers/why-did-conversions-fall-after-traffic-shifted-to-different-landing-pages): counterfactual (current rates with old weights); LLM only summarizes the numbers. Take: same pipeline, deterministic math first.
- [Sequoia: mix shift](https://articles.sequoiacap.com/metrics-mix-shift) and [Spotify Simpson's paradox](https://confidence.spotify.com/glossary/simpsons-paradox): plain explanations for the answer card. Caveat from Koji: it shows where, not why.
- [Microsoft Lumos paper](https://arxiv.org/pdf/2006.12793.pdf) ([HTML](https://ar5iv.labs.arxiv.org/html/2006.12793)): diagnoses metric regressions and separates population-mix shifts from real changes. Repo path microsoft/lumos returned 404, so paper only.
- [key-drivers (PyPI)](https://pypi.org/project/key-drivers): pandas helper that decomposes a metric change and flags small segments with large share of change. License not checked.
- [empower-ai/dsensei](https://github.com/empower-ai/dsensei): see Top 10.
- [LinkedIn ThirdEye](https://engineering.linkedin.com/blog/2020/analyzing-anomalies-with-thirdeye): anomaly detection plus RCA heatmaps of contributing dimensions ([StarTree docs](https://startree.ai/docs/concepts/what-is-startree/about-startree-thirdeye)). Take: top-contributors view per dimension.
- [DoWhy root-cause docs](https://py-why.github.io/dowhy/main/user_guide/causal_tasks/root_causing_and_explaining/index.html) ([py-why/dowhy](https://github.com/py-why/dowhy), 8410 stars, MIT): causal attribution of distribution change. Take: skip for the build; needs a causal graph we do not have. [Additivity paper](https://arxiv.org/pdf/2604.26266): contributions must sum to the total change, a good unit test.
- [salesforce/PyRCA](https://github.com/salesforce/PyRCA): 572 stars, BSD-3-Clause; system/service RCA, not business KPIs ([docs](https://opensource.salesforce.com/PyRCA/latest/index.html)). Take: nothing for payments.
- [Sisu (BigDataWire)](https://bigdatawire.com/2020/05/18/sisu-seeks-to-answer-why) and [Outlier](https://prnewswire.com/news-releases/outlier-introduces-ai-powered-automated-business-analysis-platform-300728413.html): commercial "why did the KPI move" products. Take: the product framing: drivers ranked by contribution.

### Payments analytics

- [Stripe acceptance analytics](https://docs.stripe.com/declines/acceptance-rate): separates payment success rate (all attempts, including 3DS and fraud blocks) from authorization rate (issuer approvals over network attempts). Take: define both in the semantic layer, with exact denominators.
- [Razorpay success rate analytics](https://razorpay.com/docs/payments/payments/success-rate-analytics/) and [Razorpay SR dashboard](https://razorpay.com/docs/payments/optimizer/success-rate/): SR cuts by method, bank, gateway. Take: our segment list.
- [Checkout.com authorization analytics](https://www.checkout.com/docs/business-operations/monitor-payment-performance/authorization-analytics): declines segmented by issuing country, issuing bank, BIN, payment method. Take: segment order for the decomposition.
- [Cashfree docs](https://www.cashfree.com/docs/payments/quick-guide/payment.md): sudden drops often come from bank downtime or network issues, not integration. Take: first hypothesis to test is a single-bank outage.
- [Recurly payments hub](https://docs.recurly.com/recurly-subscriptions/docs/navigate-scale-payments-hub-payment-processing) and [Zoho Payments failures](https://www.zoho.com/in/payments/help/reports/payment-failures/index.md): failure taxonomy (issuer decline, network error, customer abandonment). Take: group failure codes into these buckets in the metric layer.
- [satyamInsights/PhonePe-Payment-Insights-Dashboard](https://github.com/satyamInsights/PhonePe-Payment-Insights-Dashboard) (2 stars, license not checked): Power BI on PhonePe data. Only finding on GitHub for payments dashboards; the `payment success rate` searches returned mostly noise.

### Streamlit AI analyst apps

- [rranjanyyadav/late-delivery-investigator](https://github.com/rranjanyyadav/late-delivery-investigator): see Top 10 (Streamlit + DuckDB, charts chosen by result shape).
- [Ask Your Data write-up](https://yx-yan.github.io/posts/ask-your-data-ai-analytics-app): question to SQL to chart to insights on DuckDB. Take: auto-chart from result shape.
- [MotherDuck: DuckDB + Streamlit](https://motherduck.com/videos/duckdb-streamlit-crafting-dynamic-dashboards-and-data-apps/): local-first app pattern. Take: DuckDB in-process is enough.
- [IshaanLabs/langgraph-text-to-sql-agent](https://github.com/IshaanLabs/langgraph-text-to-sql-agent): Streamlit UI over SQLite ([search result](https://github.com/IshaanLabs/langgraph-text-to-sql-agent)). Stars not checked.
- [ishant2034/AI-Business-Analyst](https://github.com/ishant2034/AI-Business-Analyst) (0 stars, no license): text-to-SQL agent with self-correction and auto insights. Portfolio level.
- [SaneethSunkari/Ai-Business-Analyst](https://github.com/SaneethSunkari/Ai-Business-Analyst) (0 stars, no license): live DB Q&A with schema introspection and read-only SQL validation.
- [sarusarvesh993-cyber/Executive-AI-Business-Analyst](https://github.com/sarusarvesh993-cyber/Executive-AI-Business-Analyst) (8 stars, MIT): React/FastAPI executive summary app; different stack.
- [Drunal999/ask-your-data](https://github.com/Drunal999/ask-your-data) (0 stars, no license seen): semantic layer, LLM planner, glossary RAG, guardrails.
- [gopalmani/QueryMindAI](https://github.com/gopalmani/QueryMindAI) (18 stars, MIT) and [lanerchenbuna/QueryForge](https://github.com/lanerchenbuna/QueryForge) (13 stars, license not shown): governed NL analytics with a mandatory semantic layer; code not read.
- [MoonMao42/ReceiptBI](https://github.com/MoonMao42/ReceiptBI) (38 stars, MIT): turns CSV/read-only DB into verified, editable reports. Take: "verified" label per number.

### Pine Labs-specific finds (official and public context)

- [Pine Labs online MCP server](https://github.com/plural-pinelabs/pinelabs-online-mcp): official, 2 stars, Apache-2.0, last push 2026-07-16. Take: the real transaction/settlement vocabulary Pine Labs uses.
- [Pine Labs AI docs](https://www.pinelabs.com/docs/online-payments/ai.md): MCP server, agent toolkit, n8n nodes. Take: terminology for the case-study write-up.
- [YourStory, Nov 2026](https://yourstory.com/2026/11/how-pine-labs-is-building-for-the-agent-economy-cto-sanjeev-kumar-on-trust-control-and-execution): CTO talks about trust, control and execution for agents. Take: lead with controls (validation, roles, audit trail) in the pitch.
- [Inc42 on Pine Labs AI R&D](https://inc42.com/buzz/pine-labs-invests-%e2%82%b924-cr-in-ai-rd-in-fy26-cuts-testing-time-by-over-95/): reports 25% developer productivity gain and 80% faster incident analysis. Take: frame our tool by time saved on diagnosis.
- [Pine Labs AI Associate PM posting](https://www.foundit.in/job/ai-associate-product-manager-pine-labs-bengaluru-bangalore-60189525): "first builder", prototypes with LLM/agent tools. Take: expectation is a working prototype plus product thinking.
- No public "Pine Labs AI Business Analyst" repo or write-up was found by web queries 17-18.

## Pine Labs-specific

Everything below is **ideas only, do not copy (fellow-candidate submission)**, even where a license is shown. None of these is confirmed to be the same case study as ours; several come from a separate Pine Labs hackathon (2026), so the task may differ.

- [coolpinkzz/pinelabs-ai-merchant-copilot](https://github.com/coolpinkzz/pinelabs-ai-merchant-copilot): "ask simple questions about your transactions, refunds, and settlements" (0 stars, no license, pushed 2026-03-14). README empty, so approach unknown. Ideas only, do not copy (fellow-candidate submission).
- [gkdivya/pine_labs_assistant](https://github.com/gkdivya/pine_labs_assistant): React chat UI for merchant analytics talking to a backend on port 8000 with a `/query` proxy ([README](https://github.com/gkdivya/pine_labs_assistant)); 0 stars, no license. Front end only. Ideas only, do not copy (fellow-candidate submission).
- [krishnadev-ss/pine-ai](https://github.com/krishnadev-ss/pine-ai) ("PayIntent"): checkout abandonment recovery with funnel dashboard by drop-off stage and bank API health ([README](https://github.com/krishnadev-ss/pine-ai)). Take: drop-off stage taxonomy (OTP timeout etc.) as failure-reason buckets. Ideas only, do not copy (fellow-candidate submission).
- [arnavgupta28/checkoutiq-pinelabs](https://github.com/arnavgupta28/checkoutiq-pinelabs): CheckoutIQ, two-layer agentic checkout; deterministic "insight engine" runs before any LLM call, with a non-LLM fallback ([README](https://github.com/arnavgupta28/checkoutiq-pinelabs)). Take: compute with code first, use the LLM only to explain, and have a fallback when the LLM fails. Ideas only, do not copy (fellow-candidate submission).
- [jmegha27/customer-segmentation-etl](https://github.com/jmegha27/customer-segmentation-etl): described as "Assignment for Pine Labs" (0 stars, pushed 2026-05-15). Not opened. Ideas only, do not copy (fellow-candidate submission).
- Other repos from the same hackathon searches, not opened: [anujmenta/cache-money](https://github.com/anujmenta/cache-money), [madhufyi/pinelabs-ai-marketplace](https://github.com/madhufyi/pinelabs-ai-marketplace), [AlokM98/checkoutiq-pinelabs-ai](https://github.com/AlokM98/checkoutiq-pinelabs-ai), [tojochacko/pinelabs-hackathon-](https://github.com/tojochacko/pinelabs-hackathon-), [aashishparuvada/pinelabs-hackathon](https://github.com/aashishparuvada/pinelabs-hackathon). Ideas only, do not copy (fellow-candidate submission).

The repo `aaryan-pradhan/pinelabs-ai-analyst` also appeared in `pinelabs ai` results; it is our own repo and was ignored.

## Recommended ideas for our build

- Plan, don't free-write: have the LLM return a JSON plan (`metric` / `sql` / `drilldown` / `cannot_answer`) and compile SQL from the YAML semantic layer, as [late-delivery-investigator](https://github.com/rranjanyyadav/late-delivery-investigator) does. Allow raw SQL only as a validated fallback. Supporting evidence: [dbt benchmark](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026).
- Add an explicit `cannot_answer` path so out-of-scope questions are declined instead of guessed ([dbt post](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)).
- Validate with sqlglot in layers: single statement, root is SELECT, reject data-modifying CTEs, schema/column binding, role allowlist, forced LIMIT ([sql-guardrail](https://pypi.org/project/sql-guardrail/), [text-to-sql-agent-system](https://github.com/fengyede79/text-to-sql-agent-system), [Atlas survey](https://laoujin.github.io/Atlas/research/2026-06-09-audit-and-harden-text-to-sql-pipelines-2026/query-validation-and-safety-gates/)).
- Lock down DuckDB too: a SELECT-only check is not enough because a SELECT can read files or open connections ([readonly-sql-guard](https://pypi.org/project/readonly-sql-guard/)); disable external file/network access and set a query timeout. Keep safety in code, not the prompt ([LangChain analysis](https://open-agent-ai-security.github.io/praxen/tests/baselines/v0.7.7-claude48/langchain-sql/langchain-sql-analysis-2026-05-29-170813.html)).
- Cap repair retries, re-validate after each repair, and stop on destructive intent, so the repair loop cannot strip a role filter ([text-to-sql-agent-system](https://github.com/fengyede79/text-to-sql-agent-system), [Atlas survey](https://laoujin.github.io/Atlas/research/2026-06-09-audit-and-harden-text-to-sql-pipelines-2026/query-validation-and-safety-gates/)).
- Mix-vs-rate in plain code with the symmetric Kitagawa form so rate and mix effects sum exactly to the change in success rate ([MetricGate](https://metricgate.com/docs/kitagawa-decomposition/)); unit-test that the sum equals the total ([additivity paper](https://arxiv.org/pdf/2604.26266)); report absolute counts next to rates ([TryAnalyze](https://www.tryanalyze.ai/answers/why-did-conversions-fall-after-traffic-shifted-to-different-landing-pages)).
- Rank segments by share of the change vs share of volume to find the culprit bank or method ([KPI-change article](https://towardsdatascience.com/making-sense-of-kpi-changes/), [key-drivers](https://pypi.org/project/key-drivers)); segment by method, issuer bank and failure bucket as payments vendors do ([Checkout.com](https://www.checkout.com/docs/business-operations/monitor-payment-performance/authorization-analytics), [Razorpay](https://razorpay.com/docs/payments/payments/success-rate-analytics/)).
- Define success rate and authorization rate separately with explicit denominators ([Stripe](https://docs.stripe.com/declines/acceptance-rate)); make "single-bank or network outage" the first hypothesis to test ([Cashfree](https://www.cashfree.com/docs/payments/quick-guide/payment.md)).
- Run data-quality checks before answering and show them in the card: duplicate ids, nulls, orphan keys, source mismatch ([late-delivery-investigator loader](https://github.com/rranjanyyadav/late-delivery-investigator), [dltHub toolkit notes](https://dlthub.com/blog/dq-toolkit-preview)). Critical failures should block or caveat the answer.
- Known-answer eval: 20-30 questions with gold SQL or expected behavior, graded on result-set match, not SQL text ([execution accuracy paper](https://arxiv.org/pdf/2407.07313v4)); also check provenance, meaning the SQL read the expected tables ([the_honest_agent](https://github.com/jlcoto/the_honest_agent)); include refusal and injection cases and an independent no-LLM ground-truth query ([chartersense](https://github.com/Prennoy99/chartersense)).
- Prove the semantic layer helps: run the eval with and without it and list questions fixed and broken ([auto-ontology-eval](https://github.com/NVIDIA/auto-ontology-eval)). Use test data variants so wrong queries cannot pass by luck ([test-suite-sql-eval](https://github.com/taoyds/test-suite-sql-eval)).
- Answer card: put a provenance footer on each fact (metric definition, source table, SQL, data freshness) ([fafa-ai-data-lab](https://github.com/fafa-ai-data-lab/ai-data-analyst-agent)); let the LLM use only numbers present in the result set ([late-delivery-investigator](https://github.com/rranjanyyadav/late-delivery-investigator)); compute with code before the LLM and keep a non-LLM fallback ([checkoutiq-pinelabs](https://github.com/arnavgupta28/checkoutiq-pinelabs), ideas only).
- Pitch angle for Pine Labs: lead with trust and control, which Pine Labs' CTO names as the focus ([YourStory](https://yourstory.com/2026/11/how-pine-labs-is-building-for-the-agent-economy-cto-sanjeev-kumar-on-trust-control-and-execution)).
