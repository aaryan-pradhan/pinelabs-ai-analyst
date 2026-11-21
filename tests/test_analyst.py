"""Seam 1: the analyst, driven with a fake LLM that returns a fixed plan."""
import json

import pytest

from analyst import ask
from llm import ModelUnavailable

WK6_PLAN = {"metric": "success_rate", "dimensions": ["payment_method"], "weeks": [5, 6]}


NARRATION = {"headline": "h", "hypotheses": [], "recommendations": []}


def fake_llm(plan, prompts=None):
    """Replies with the plan, then the narration; records prompts if given a list."""
    replies = iter([json.dumps(plan), json.dumps(NARRATION)])

    def llm(prompt, check):
        if prompts is not None:
            prompts.append(prompt)
        return next(replies)
    return llm


def test_wk6_drop_is_a_mix_shift(db_path):
    prompts = []
    answer = ask("Why did success rate drop in week 6?", "analyst", fake_llm(WK6_PLAN, prompts), db_path)

    d = answer.decomposition
    assert d["dimension"] == "payment_method"
    assert -0.05 < d["total"] < -0.03
    assert d["mix"] / d["total"] >= 0.8
    assert d["mix"] + d["rate"] == pytest.approx(d["total"], abs=1e-12)
    assert "mix shift" in prompts[1]  # the computed headline the model narrates from
    assert {row["segment"] for row in answer.chart} == {"upi", "card", "netbanking", "wallet"}

    assert answer.facts
    for fact in answer.facts:
        assert fact.sql.upper().startswith("SELECT")
        assert "LIMIT 10000" in fact.sql
        assert fact.tables == ["transactions"]
        assert fact.window == "wk5 vs wk6"


def test_model_narrates_but_facts_come_only_from_executed_sql(db_path, con):
    narration = {
        "headline": "Success rate fell 99pp in week 6",
        "hypotheses": ["Festive sale pushed traffic to netbanking"],
        "recommendations": ["Watch wallet success during sales"],
        "facts": [{"label": "invented", "value": 0.5, "unit": "%"}],
    }
    replies = iter([json.dumps(WK6_PLAN), json.dumps(narration)])

    answer = ask("Why did success rate drop in week 6?", "analyst", lambda prompt, check: next(replies), db_path)

    assert answer.headline == "Success rate fell 99pp in week 6"
    assert answer.hypotheses == ["Festive sale pushed traffic to netbanking"]
    assert answer.recommendations == ["Watch wallet success during sales"]
    assert "invented" not in str(answer.facts)
    for fact in answer.facts:
        rows = con.execute(fact.sql).df()
        if fact.unit == "%":  # a rate straight from the query
            assert fact.value in rows["success_rate"].to_numpy()
        else:  # a change in rate: wk6 minus wk5 for one segment of the query
            rate = rows.pivot(index="payment_method", columns="week", values="success_rate")
            assert fact.value in (rate[6] - rate[5]).to_numpy()


def down(prompt, check):
    raise ModelUnavailable("free model limit reached, try again in a minute")


def test_model_down_after_planning_carries_the_planned_sql(db_path):
    replies = iter([json.dumps(WK6_PLAN)])

    def llm(prompt, check):
        return next(replies, None) or down(prompt, check)

    with pytest.raises(ModelUnavailable) as err:
        ask("Why did success rate drop in week 6?", "analyst", llm, db_path)
    assert err.value.sql
    assert all(s.startswith("SELECT") and "IN (5, 6)" in s for s in err.value.sql)


def test_model_down_before_planning_carries_the_default_plan_sql(db_path):
    with pytest.raises(ModelUnavailable) as err:
        ask("How are payments doing lately?", "analyst", down, db_path)
    assert err.value.sql
    assert all(s.startswith("SELECT") and "IN (7, 8)" in s for s in err.value.sql)


def test_unusable_plan_from_the_model_is_refused_not_run(db_path):
    real_reply = {"metric": "success_rate", "dimensions": ["week", "payment_method"],
                  "weeks": ["week_5", "week_6"]}  # nemotron, 21 Nov

    with pytest.raises(ModelUnavailable, match="unusable reply") as err:
        ask("Why did success rate drop in week 6?", "analyst", fake_llm(real_reply), db_path)
    assert all("IN (7, 8)" in s for s in err.value.sql)


def test_narration_that_is_not_json_is_refused_with_the_executed_sql(db_path):
    replies = iter([json.dumps(WK6_PLAN), "Sorry, I can't help with that."])

    with pytest.raises(ModelUnavailable, match="unusable") as err:
        ask("Why did success rate drop in week 6?", "analyst", lambda prompt, check: next(replies), db_path)
    assert all("IN (5, 6)" in s for s in err.value.sql)
