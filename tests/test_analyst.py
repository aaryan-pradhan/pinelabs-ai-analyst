"""Seam 1: the analyst, driven with a fake LLM that returns a fixed plan."""
import json
import re
import shutil

import duckdb
import pytest

import generator
from analyst import AskBack, ask
from llm import ModelUnavailable, NoQuota, with_replay
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
    assert "-0.00%" not in prompts[1]  # a zero gap's sign is float noise; it would change the replay key
    assert answer.dq["mismatch"]
    assert any("Source mismatch" in line for line in answer.dq["caveats"])
    for fact in answer.facts:
        assert "settlements" in fact.tables
        assert fact.window == "wk5"


def test_gmv_by_category_excludes_duplicates(db_path):
    answer = ask("GMV by category in wk8", ANALYST, fake_llm({"metric": "gmv", "weeks": [8]}), db_path)

    gmv = {row["segment"]: round(row["gmv"], 2) for row in answer.chart}
    assert gmv == generator.expected(db_path)["wk8_gmv_by_category"]  # hand-written SQL, Duplicates removed
    assert any("left out of GMV" in line for line in answer.dq["caveats"])  # null amounts
    for fact in answer.facts:
        assert fact.unit == "₹" and fact.window == "wk8"


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


@pytest.mark.parametrize("narration", [None, "Sorry, I can't help with that."])  # down, or unusable
def test_without_narration_the_answer_keeps_its_computed_headline(db_path, narration):
    replies = iter([json.dumps(WK6_PLAN), narration])

    def llm(prompt, check):
        return next(replies) or down(prompt, check)

    answer = ask("Why did success rate drop in week 6?", ANALYST, llm, db_path)
    assert answer.narrated is False
    assert answer.headline.startswith("Success rate fell") and "wk5" in answer.headline
    assert answer.hypotheses == answer.recommendations == []
    assert [f.label for f in answer.facts][:2] == ["Success rate wk5", "Success rate wk6"]
    assert any("model was unavailable" in c for c in answer.dq["caveats"])


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
    assert own.assumptions["scope"] == "grocery"  # shown even when the question named it
    assert all(f.sql.count("merchants.category = 'grocery'") == 1 for f in own.facts)


def test_merchant_manager_plan_that_sneaks_in_settlements_is_blocked(db_path):
    sneaky = {"metric": "settlement_gap", "weeks": [5]}  # a success rate question, planned as Settlements

    with pytest.raises(Rejected, match="Merchant manager cannot see Settlements"):
        ask("Why did success rate drop in week 5?", GROCERY, fake_llm(sneaky), db_path)


def test_merchant_manager_default_plan_sql_is_scoped_by_the_validator(db_path):
    with pytest.raises(ModelUnavailable) as err:  # no plan, so only the validator scopes it
        ask("How are payments doing lately?", GROCERY, down, db_path)
    assert all("merchants.category = 'grocery'" in s for s in err.value.sql)


def test_merchant_manager_caveats_count_only_their_category(db_path, con):
    answer = ask("Why did success rate drop in week 6?", GROCERY, fake_llm(WK6_PLAN), db_path)

    rows, attempts = con.execute(
        "SELECT COUNT(*), COUNT(DISTINCT txn_id) FROM transactions JOIN merchants USING (merchant_id)"
        f" WHERE category = 'grocery' AND {WEEK} IN (5, 6)").fetchone()
    assert answer.dq["duplicates"] == rows - attempts
    assert answer.dq["caveats"][0].startswith(f"{rows - attempts:,} Duplicates ({(rows - attempts) / rows:.1%}")


def ad_hoc(sql):
    return fake_llm({"sql": sql})


def test_destructive_request_is_rejected_as_not_a_select(db_path, con):
    failed = con.execute("SELECT COUNT(*) FROM transactions WHERE status = 'failed'").fetchone()[0]

    delete = "DELETE FROM transactions WHERE status = 'failed'"
    with pytest.raises(Rejected, match="Only a single SELECT") as refused:
        ask("Delete the failed transactions", ANALYST, ad_hoc(delete), db_path)
    assert refused.value.sql == [delete]  # shown on the card beside the reason
    assert con.execute("SELECT COUNT(*) FROM transactions WHERE status = 'failed'").fetchone()[0] == failed


def test_ad_hoc_sql_runs_with_the_missing_limit_added(db_path, con):
    assert con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] > 10000

    answer = ask("List every transaction id", ANALYST, ad_hoc("SELECT txn_id FROM transactions"), db_path)
    assert answer.result["sql"] == "SELECT txn_id FROM transactions LIMIT 10000"
    assert answer.result["tables"] == ["transactions"]
    assert len(answer.result["rows"]) == 10000


@pytest.mark.parametrize("join", [
    "FROM transactions, merchants",
    "FROM transactions CROSS JOIN merchants",
    "FROM transactions JOIN merchants ON 1 = 1",
    "FROM transactions JOIN merchants ON merchants.merchant_id = transactions.merchant_id OR 1 = 1",
    "FROM transactions JOIN merchants ON merchants.merchant_id = merchants.merchant_id",
])
def test_join_without_a_key_is_rejected(join, db_path):
    with pytest.raises(Rejected, match="Join without a key"):
        ask("Count transactions per merchant name", ANALYST, ad_hoc(f"SELECT name, COUNT(*) {join} GROUP BY name"),
            db_path)


def test_ad_hoc_sql_may_order_by_its_own_alias(db_path):
    sql = "SELECT status, COUNT(*) AS n FROM transactions GROUP BY status ORDER BY n DESC"
    rows = ask("Which status is most common?", ANALYST, ad_hoc(sql), db_path).result["rows"]
    assert rows["status"].iloc[0] == "success"


def no_model(prompt, check):
    raise NoQuota("no OpenRouter key set")


@pytest.mark.parametrize("question", ["Why did success rate drop in week 6?",
                                      "Which bank got worse on cards in wk7?", "How's success rate lately?"])
def test_demo_question_answers_from_the_replay_cache_with_no_model(question, db_path):
    replayed = []
    answer = ask(question, ANALYST, with_replay(no_model, replayed), db_path)

    assert len(replayed) == 2  # plan and narration; a miss means the cache is stale
    assert answer.facts and answer.hypotheses and answer.recommendations


def test_demo_merchant_manager_settlements_block_replays_with_no_model(db_path):
    with pytest.raises(Rejected, match="Merchant manager"):
        ask("Show me settlements", Role("Merchant manager", "grocery"), with_replay(no_model, []), db_path)


def test_demo_duplicates_question_replays_with_no_model(db_path):
    replayed = []
    answer = ask("How many duplicate transactions are there?", ANALYST, with_replay(no_model, replayed), db_path)

    assert len(replayed) == 2  # plan and narration
    assert "Duplicates" in answer.dq["caveats"][0]
    assert "2,252" in answer.headline and answer.hypotheses and answer.recommendations


def test_ad_hoc_answer_is_narrated_from_the_rows_it_returned(db_path):
    prompts = []
    sql = "SELECT status, COUNT(*) AS n FROM transactions GROUP BY status ORDER BY n DESC"
    answer = ask("Which status is most common?", ANALYST, fake_llm({"sql": sql}, prompts), db_path)

    assert answer.headline == "h" and answer.narrated
    assert "status,n\nsuccess," in prompts[1]
