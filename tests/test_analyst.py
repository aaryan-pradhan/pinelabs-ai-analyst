"""Seam 1: the analyst, driven with a fake LLM that returns a fixed plan."""
import json

import pytest

from analyst import ask

WK6_PLAN = {"metric": "success_rate", "dimensions": ["payment_method"], "weeks": [5, 6]}


def fake_llm(plan):
    return lambda prompt: json.dumps(plan)


def test_wk6_drop_is_a_mix_shift(db_path):
    answer = ask("Why did success rate drop in week 6?", "analyst", fake_llm(WK6_PLAN), db_path)

    d = answer.decomposition
    assert d["dimension"] == "payment_method"
    assert -0.05 < d["total"] < -0.03
    assert d["mix"] / d["total"] >= 0.8
    assert d["mix"] + d["rate"] == pytest.approx(d["total"], abs=1e-12)
    assert "mix" in answer.headline.lower()
    assert {row["segment"] for row in answer.chart} == {"upi", "card", "netbanking", "wallet"}

    assert answer.facts
    for fact in answer.facts:
        assert fact.sql.upper().startswith("SELECT")
        assert "LIMIT 10000" in fact.sql
        assert fact.tables == ["transactions"]
        assert fact.window == "wk5 vs wk6"
