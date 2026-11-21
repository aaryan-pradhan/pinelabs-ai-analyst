"""The eval runner over Seam 1, driven with a fake LLM that returns fixed plans."""
import json

import pytest

import evaluate
import generator
import llm

NARRATION = {"headline": "h", "hypotheses": [], "recommendations": []}
RIGHT_PLANS = [  # in the order of evaluate.QUESTIONS
    {"metric": "success_rate", "weeks": [5, 6]},
    {"metric": "success_rate", "weeks": [5, 6]},
    {"metric": "success_rate", "weeks": [6, 7], "filters": {"payment_method": "card"}},
    {"sql": "SELECT COUNT(*) - COUNT(DISTINCT txn_id) AS duplicates FROM transactions"},
    {"metric": "settlement_gap", "weeks": [5]},
    {"metric": "settlement_gap"},
    {"metric": "success_rate", "filters": {"category": "electronics"}},
    {"metric": "success_rate"},
    {"sql": "DELETE FROM transactions WHERE status = 'failed'"},
    {"metric": "gmv", "weeks": [8]},
]


def fake_llm(plans):
    """Replies to a plan prompt with that question's plan, and to anything else with narration."""
    by_question = dict(zip([q for q, _, _ in evaluate.QUESTIONS], plans))

    def complete(prompt, check):
        if prompt.startswith("Choose a plan"):
            return json.dumps(by_question[prompt.split("Question: ")[-1]])
        return json.dumps(NARRATION)
    return complete


@pytest.fixture(scope="module")
def expected(db_path):
    return generator.expected(db_path)


def test_right_plans_pass_all_ten(db_path, expected):
    results = evaluate.run(fake_llm(RIGHT_PLANS), db_path, expected)

    assert [r["why"] for r in results if not r["passed"]] == []
    assert len(results) == 10


def test_a_wrong_plan_fails_its_question_with_a_reason(db_path, expected):
    wrong = list(RIGHT_PLANS)
    wrong[0] = {"metric": "success_rate", "weeks": [6, 7]}  # wk6 drop asked about the wrong weeks
    wrong[8] = {"ask": "Which transactions?"}  # the delete request not rejected

    results = evaluate.run(fake_llm(wrong), db_path, expected)

    failed = [i for i, r in enumerate(results) if not r["passed"]]
    assert failed == [0, 8]
    assert all(results[i]["why"] for i in failed)


def test_no_quota_stops_the_run(db_path, expected):
    def spent(prompt, check):
        raise llm.NoQuota("free model limit reached, try again in a minute")

    with pytest.raises(llm.NoQuota):
        evaluate.run(spent, db_path, expected)
