"""Seam 1: the analyst, driven with a fake LLM that returns a fixed plan."""
import json
import re
import shutil

import duckdb
import pytest

from analyst import AskBack, ask
from llm import ModelUnavailable
from validator import ANALYST, Rejected, Role

WK6_PLAN = {"metric": "success_rate", "weeks": [5, 6]}
WK7_CARD_PLAN = {"metric": "success_rate", "weeks": [6, 7], "filters": {"payment_method": "card"}}


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
    answer = ask("Why did success rate drop in week 6?", ANALYST, fake_llm(WK6_PLAN, prompts), db_path)

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
    assert "weeks" not in answer.assumptions  # the question named its Weeks


def test_wk7_card_drop_names_the_bank_that_got_worse(db_path):
    prompts = []
    answer = ask("Which bank got worse on cards in week 7?", ANALYST, fake_llm(WK7_CARD_PLAN, prompts), db_path)

    d = answer.decomposition
    assert d["dimension"] == "bank"
    assert d["rate"] / d["total"] >= 0.8
    coastal = next(s for s in d["segments"] if s["segment"] == "Coastal Bank")  # planted in story (b)
    assert 0.90 < coastal["rate_before"] < 0.94
    assert 0.76 < coastal["rate_after"] < 0.80
    computed = prompts[1].split("Computed headline: ")[1].split("\n")[0]
    assert "rate change within banks" in computed
    assert re.search(r"Coastal Bank went from 9[12]\.\d% to 7[78]\.\d%", computed)
    assert "Coastal Bank" in {row["segment"] for row in answer.chart}
    for fact in answer.facts:
        assert fact.filters == ["payment_method = card"]
        assert "payment_method = 'card'" in fact.sql


def test_model_narrates_but_facts_come_only_from_executed_sql(db_path, con):
    narration = {
        "headline": "Success rate fell 99pp in week 6",
        "hypotheses": ["Festive sale pushed traffic to netbanking"],
        "recommendations": ["Watch wallet success during sales"],
        "facts": [{"label": "invented", "value": 0.5, "unit": "%"}],
    }
    replies = iter([json.dumps(WK6_PLAN), json.dumps(narration)])

    answer = ask("Why did success rate drop in week 6?", ANALYST, lambda prompt, check: next(replies), db_path)

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


def test_wk5_settlements_fall_short_for_one_category(db_path):
    prompts = []
    plan = {"metric": "settlement_gap", "weeks": [5]}
    answer = ask("Do settlements match transactions in week 5?", ANALYST, fake_llm(plan, prompts), db_path)

    gaps = {row["segment"]: row["gap"] for row in answer.chart}
    assert len(gaps) == 6  # every category
    assert [c for c, gap in gaps.items() if abs(gap) > 0.005] == ["electronics"]  # planted in story (d)
    assert gaps["electronics"] == pytest.approx(-0.03, abs=1e-9)
    computed = prompts[1].split("Computed headline: ")[1].split("\n")[0]
    assert "electronics" in computed and "3.0%" in computed
    assert answer.dq["mismatch"]
    assert any("Source mismatch" in line for line in answer.dq["caveats"])
    for fact in answer.facts:
        assert "settlements" in fact.tables
        assert fact.window == "wk5"


WEEK = "CAST(FLOOR(date_diff('day', DATE '2026-09-28', CAST(ts AS DATE)) / 7) AS INTEGER) + 1"


def test_duplicates_are_counted_exactly_and_excluded(db_path, con):
    answer = ask("Why did success rate drop in week 6?", ANALYST, fake_llm(WK6_PLAN), db_path)

    rows, attempts = con.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT txn_id) FROM transactions WHERE {WEEK} IN (5, 6)").fetchone()
    assert answer.dq["duplicates"] == rows - attempts > 0
    assert any(f"{rows - attempts:,} Duplicates" in line for line in answer.dq["caveats"])
    overall = con.execute(answer.facts[0].sql).df()
    assert overall["attempts"].sum() == attempts


def test_unknown_bank_segment_keeps_totals_and_null_caveat_fires(db_path, con):
    answer = ask("Which bank got worse on cards in week 7?", ANALYST, fake_llm(WK7_CARD_PLAN), db_path)

    assert "Unknown bank" in {row["segment"] for row in answer.chart}
    overall = con.execute(answer.facts[0].sql).df().set_index("week")["attempts"]
    by_bank = con.execute(answer.facts[-1].sql).df().groupby("week")["attempts"].sum()
    assert (by_bank == overall).all()
    assert any("bank_id" in line and "Unknown bank" in line for line in answer.dq["caveats"])

    wk6 = ask("Why did success rate drop in week 6?", ANALYST, fake_llm(WK6_PLAN), db_path)
    assert not any("bank_id" in line for line in wk6.dq["caveats"])  # only columns the answer uses


def edited_copy(db_path, tmp_path, sql):
    """A copy of the database with `sql` applied."""
    path = tmp_path / "edited.duckdb"
    shutil.copy(db_path, path)
    with duckdb.connect(str(path)) as c:
        c.execute(sql)
    return path


def test_segment_under_200_attempts_is_low_confidence(db_path, tmp_path):
    thin = edited_copy(db_path, tmp_path, f"DELETE FROM transactions WHERE payment_method = 'wallet'"
                                          f" AND {WEEK} = 5 AND txn_id % 10 <> 0")
    answer = ask("Why did success rate drop in week 6?", ANALYST, fake_llm(WK6_PLAN), thin)

    assert any("wallet" in line and "200 Attempts" in line for line in answer.dq["caveats"])
    assert answer.dq["confidence"].startswith("Low")

    clean = ask("Why did success rate drop in week 6?", ANALYST, fake_llm(WK6_PLAN), db_path)
    assert clean.dq["confidence"].startswith("High")


def test_missing_day_is_a_coverage_gap(db_path, tmp_path):
    gap = edited_copy(db_path, tmp_path, "DELETE FROM transactions WHERE CAST(ts AS DATE) = DATE '2026-10-29'")
    answer = ask("Why did success rate drop in week 6?", ANALYST, fake_llm(WK6_PLAN), gap)

    assert any("2026-10-29" in line for line in answer.dq["caveats"])
    clean = ask("Why did success rate drop in week 6?", ANALYST, fake_llm(WK6_PLAN), db_path)
    assert not any("coverage" in line.lower() for line in clean.dq["caveats"])


def down(prompt, check):
    raise ModelUnavailable("free model limit reached, try again in a minute")


def test_model_down_after_planning_carries_the_planned_sql(db_path):
    replies = iter([json.dumps(WK6_PLAN)])

    def llm(prompt, check):
        return next(replies, None) or down(prompt, check)

    with pytest.raises(ModelUnavailable) as err:
        ask("Why did success rate drop in week 6?", ANALYST, llm, db_path)
    assert err.value.sql
    assert all(s.startswith("SELECT") and "IN (5, 6)" in s for s in err.value.sql)


def test_model_down_before_planning_carries_the_default_plan_sql(db_path):
    with pytest.raises(ModelUnavailable) as err:
        ask("How are payments doing lately?", ANALYST, down, db_path)
    assert err.value.sql
    assert all(s.startswith("SELECT") and "IN (7, 8)" in s for s in err.value.sql)


def test_unusable_plan_from_the_model_is_refused_not_run(db_path):
    real_reply = {"metric": "success_rate", "dimensions": ["week", "payment_method"],
                  "weeks": ["week_5", "week_6"]}  # nemotron, 21 Nov

    with pytest.raises(ModelUnavailable, match="unusable reply") as err:
        ask("Why did success rate drop in week 6?", ANALYST, fake_llm(real_reply), db_path)
    assert all("IN (7, 8)" in s for s in err.value.sql)


def test_plan_for_a_metric_the_analyst_cannot_answer_is_refused(db_path):
    gmv = {"metric": "gmv", "dimensions": ["payment_method"], "weeks": [7, 8]}

    with pytest.raises(ModelUnavailable, match="unusable reply"):
        ask("What was GMV by payment method in week 8?", ANALYST, fake_llm(gmv), db_path)


def test_narration_that_is_not_json_is_refused_with_the_executed_sql(db_path):
    replies = iter([json.dumps(WK6_PLAN), "Sorry, I can't help with that."])

    with pytest.raises(ModelUnavailable, match="unusable") as err:
        ask("Why did success rate drop in week 6?", ANALYST, lambda prompt, check: next(replies), db_path)
    assert all("IN (5, 6)" in s for s in err.value.sql)


def test_filter_that_matches_no_attempts_is_refused_with_its_sql(db_path):
    plan = {"metric": "success_rate", "weeks": [6, 7], "filters": {"payment_method": "Cards' OR '1'='1"}}

    with pytest.raises(ModelUnavailable, match="No Attempts match") as err:
        ask("Which bank got worse on cards in week 7?", ANALYST, fake_llm(plan), db_path)
    assert all("Cards'' OR ''1''=''1'" in s for s in err.value.sql)


def test_vague_question_defaults_to_latest_weeks_and_all_attempts(db_path):
    answer = ask("How's success rate lately?", ANALYST, fake_llm({"metric": "success_rate"}), db_path)

    assert answer.assumptions == {"weeks": [7, 8], "denominator": "all Attempts excluding Duplicates"}
    assert all(fact.window == "wk7 vs wk8" for fact in answer.facts)
    null = ask("How's success rate lately?", ANALYST, fake_llm({"metric": "success_rate", "weeks": None}), db_path)
    assert null.assumptions["weeks"] == [7, 8]  # a null window is no window


def test_edited_window_reruns_for_the_edited_weeks(db_path):
    answer = ask("How's success rate lately?", ANALYST, fake_llm({"metric": "success_rate"}), db_path,
                 weeks=[5, 6])

    assert answer.assumptions["weeks"] == [5, 6]
    assert all(fact.window == "wk5 vs wk6" for fact in answer.facts)
    assert answer.decomposition["dimension"] == "payment_method"  # the planted wk6 mix shift
    assert -0.05 < answer.decomposition["total"] < -0.03


def test_question_with_no_sensible_default_is_asked_back(db_path):
    back = {"ask": "Which metric do you mean: Success rate or Settlement gap?"}

    with pytest.raises(AskBack, match="Which metric do you mean"):
        ask("How are things?", ANALYST, fake_llm(back), db_path)
    with pytest.raises(ModelUnavailable, match="unusable reply"):  # nothing to ask the user
        ask("How are things?", ANALYST, fake_llm({"ask": " "}), db_path)


GROCERY = Role("Merchant manager", "grocery")


def test_merchant_manager_is_scoped_to_their_category(db_path, con):
    answer = ask("Why did success rate drop in week 6?", GROCERY, fake_llm(WK6_PLAN), db_path)

    assert answer.assumptions["scope"] == "grocery"
    expected = dict(con.execute(
        f"SELECT {WEEK}, AVG(CASE WHEN status = 'success' THEN 1.0 ELSE 0.0 END)"
        " FROM (SELECT DISTINCT ON (txn_id) * FROM transactions) JOIN merchants USING (merchant_id)"
        f" WHERE category = 'grocery' AND {WEEK} IN (5, 6) GROUP BY 1").fetchall())
    rates = {f.label: f.value for f in answer.facts if f.unit == "%"}
    assert rates == pytest.approx({"Success rate wk5": expected[5], "Success rate wk6": expected[6]})
    assert answer.decomposition["dimension"] != "category"  # one Segment explains nothing
    for fact in answer.facts:
        assert "merchants.category = 'grocery'" in fact.sql
        assert "category = grocery" in fact.filters


def test_merchant_manager_naming_another_category_is_blocked(db_path):
    plan = {**WK6_PLAN, "filters": {"category": "electronics"}}

    with pytest.raises(Rejected, match="Merchant manager for grocery cannot see electronics"):
        ask("Why did electronics success rate drop in week 6?", GROCERY, fake_llm(plan), db_path)
    own = ask("Why did grocery success rate drop in week 6?", GROCERY,
              fake_llm({**WK6_PLAN, "filters": {"category": "grocery"}}), db_path)
    assert "scope" not in own.assumptions  # the question named the category
    assert all(f.sql.count("merchants.category = 'grocery'") == 1 for f in own.facts)


def test_merchant_manager_plan_that_sneaks_in_settlements_is_blocked(db_path):
    sneaky = {"metric": "settlement_gap", "weeks": [5]}  # a success rate question, planned as Settlements

    with pytest.raises(Rejected, match="Merchant manager cannot see Settlements"):
        ask("Why did success rate drop in week 5?", GROCERY, fake_llm(sneaky), db_path)
