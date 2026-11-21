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
    first, second = llm.MODELS[:2]
    post = fake_post({first: rate_limited(), second: "plan"}, calls)

    assert complete("p", post=post, cache_dir=tmp_path) == "plan"
    assert calls == [first, second]


def test_every_model_down_raises_the_free_limit_message(tmp_path):
    calls = []
    post = fake_post({m: rate_limited() for m in llm.MODELS}, calls)

    with pytest.raises(ModelUnavailable, match="free model limit reached, try again in a minute"):
        complete("p", post=post, cache_dir=tmp_path)
    assert calls == llm.MODELS


def test_identical_prompt_replays_the_saved_response(tmp_path):
    calls = []
    post = fake_post({llm.MODELS[0]: "plan"}, calls)

    complete("same prompt", post=post, cache_dir=tmp_path)
    assert complete("same prompt", post=post, cache_dir=tmp_path) == "plan"
    assert len(calls) == 1


def test_no_key_raises_without_calling_a_model(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY")
    calls = []

    with pytest.raises(ModelUnavailable):
        complete("p", post=fake_post({}, calls), cache_dir=tmp_path)
    assert calls == []


def must_be_json(text):
    if not text.startswith("{"):
        raise ValueError(text)


def test_unusable_reply_falls_back_and_is_not_saved(tmp_path):
    first, second = llm.MODELS[:2]
    calls = []
    post = fake_post({first: "Sorry, no.", second: "{}"}, calls)

    assert complete("p", must_be_json, post, tmp_path) == "{}"
    assert calls == [first, second]
    complete("p", must_be_json, post, tmp_path)
    assert calls == [first, second]  # replayed the usable reply, not the refusal


def test_every_reply_unusable_says_so_not_limit_reached(tmp_path):
    post = fake_post({m: "Sorry, no." for m in llm.MODELS}, [])

    with pytest.raises(ModelUnavailable, match="unusable reply"):
        complete("p", must_be_json, post, tmp_path)


def test_the_model_that_answered_is_known_on_replay(tmp_path):
    first, second = llm.MODELS[:2]
    post = fake_post({first: rate_limited(), second: "plan"}, [])

    complete("p", post=post, cache_dir=tmp_path)
    complete("p", post=post, cache_dir=tmp_path)
    assert llm.answered_by("p", cache_dir=tmp_path) == second
    assert llm.answered_by("never asked", cache_dir=tmp_path) is None
