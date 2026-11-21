# pinelabs-ai-analyst

```
pip install -r requirements.txt
streamlit run app.py   # builds payments.duckdb from the seed on first run
pytest
```

Live questions use a free OpenRouter model (no paid calls). Put your key in
`.streamlit/secrets.toml` (gitignored) or the Streamlit Cloud secrets:

```
OPENROUTER_API_KEY = "sk-or-..."
```

Without a key the app still starts and shows the SQL it would run. Identical
prompts replay from `.llm_cache/`, so reruns cost no quota.

Replay mode: when there is no key or the free model is rate-limited, the demo
questions replay cached replies from `demo/replay.json`, with a banner. The
plans in it are the free model's own replies. The headline, Hypotheses and
Recommendations were written with Claude Code during development, from the
Facts of real pipeline runs. Numbers, SQL and charts are always computed by
the pipeline. The demo questions are:

1. Why did success rate drop in week 6?
2. Which bank got worse on cards in wk7?
3. How's success rate lately?
4. Show me settlements (as a Merchant manager)
5. How many duplicate transactions are there?
6. The Run eval button (falls back to the last committed result)
