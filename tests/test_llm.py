"""Seam 2: the OpenRouter adapter, driven with a fake HTTP post."""
from urllib.error import HTTPError

import pytest

import llm
from llm import ModelUnavailable, complete


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def fake_post(replies, calls):
    """replies maps model -> text, or an exception to raise."""
    def post(model, prompt, key):
        calls.append(model)
        reply = replies[model]
        if isinstance(reply, Exception):
            raise reply
        return reply
    return post


def rate_limited():
    return HTTPError("https://openrouter.ai", 429, "Too Many Requests", {}, None)


def test_rate_limited_model_falls_back_to_the_next_free_model(tmp_path):
    calls = []
    post = fake_post({"nvidia/nemotron-3.5-super-vl:free": rate_limited(),
                      "inclusionai/ling-3.2-flash:free": "plan"}, calls)

    assert complete("p", post, tmp_path) == "plan"
    assert calls == ["nvidia/nemotron-3.5-super-vl:free", "inclusionai/ling-3.2-flash:free"]


def test_every_model_down_raises_the_free_limit_message(tmp_path):
    calls = []
    post = fake_post({m: rate_limited() for m in llm.MODELS}, calls)

    with pytest.raises(ModelUnavailable, match="free model limit reached, try again in a minute"):
        complete("p", post, tmp_path)
    assert calls == ["nvidia/nemotron-3.5-super-vl:free", "inclusionai/ling-3.2-flash:free",
                     "google/gemma-4-31b-it:free"]


def test_identical_prompt_replays_the_saved_response(tmp_path):
    calls = []
    post = fake_post({"nvidia/nemotron-3.5-super-vl:free": "plan"}, calls)

    complete("same prompt", post, tmp_path)
    assert complete("same prompt", post, tmp_path) == "plan"
    assert len(calls) == 1


def test_no_key_raises_without_calling_a_model(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY")
    calls = []

    with pytest.raises(ModelUnavailable):
        complete("p", fake_post({}, calls), tmp_path)
    assert calls == []
