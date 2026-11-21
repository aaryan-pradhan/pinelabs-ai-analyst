"""Free-model adapter: prompt -> text through OpenRouter. Never a paid call.

Tries each free model in order. An identical prompt replays the saved
response, so reruns cost no quota (OpenRouter free tier: 50 requests/day).
"""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

MODELS = [  # all ":free" variants; a failed model is skipped, never a paid one
    "nvidia/nemotron-3.5-super-vl:free",
    "inclusionai/ling-3.2-flash:free",
    "google/gemma-4-31b-it:free",
]
CACHE_DIR = Path(__file__).parent / ".llm_cache"
URL = "https://openrouter.ai/api/v1/chat/completions"


class ModelUnavailable(Exception):
    sql = ()  # the SQL the answer would have run, shown with the message


def post(model, prompt, key):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = Request(URL, body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urlopen(req, timeout=60) as resp:
        text = json.load(resp)["choices"][0]["message"]["content"]
    if not text:
        raise ValueError(f"{model} returned an empty reply")
    return text


def complete(prompt, post=post, cache_dir=CACHE_DIR):
    saved = Path(cache_dir) / f"{hashlib.sha256(prompt.encode()).hexdigest()}.txt"
    if saved.exists():
        return saved.read_text()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise ModelUnavailable("no OpenRouter key set: add OPENROUTER_API_KEY to Streamlit secrets")
    for model in MODELS:
        try:
            text = post(model, prompt, key)
        except (OSError, KeyError, IndexError, ValueError):  # HTTP 429/5xx, timeout, bad body
            continue
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(text)
        return text
    raise ModelUnavailable("free model limit reached, try again in a minute")
