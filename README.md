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
