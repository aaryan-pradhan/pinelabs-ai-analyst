"""Known-answer eval: 10 questions through the analyst seam, graded on structured
fields only, never the narration (D26, D27). Expected values come from the
generator's hand-written SQL.

`python evaluate.py` runs it on the live free model (identical prompts replay saved
replies) and writes eval/result.json, the deployed app's fallback when it has no quota.
"""
import json
from datetime import date

import llm
from analyst import ask
from generator import DB_PATH, EXPECTED_PATH
from validator import ANALYST, Rejected, Role

RESULT_PATH = EXPECTED_PATH.parent / "result.json"
RATE = 0.002  # rates +/-0.2pp; counts and money exact
MANAGER = Role("Merchant manager", "grocery")


class Fail(Exception):
    """Why a question failed."""


def need(ok, why):
    if not ok:
        raise Fail(why)


def answered(out):
    need(not isinstance(out, Exception), f"no Answer: {type(out).__name__}: {out}")
    return out


def near(got, want, what):
    need(abs(got - want) <= RATE, f"{what} {got:.2%}, expected {want:.2%} +/-0.2pp")


def led_by(out, dimension):
    d = answered(out).decomposition
    need(d.get("dimension") == dimension, f"led with {d.get('dimension')}, expected {dimension}")
    return d


def blocked(out, exp=None):
    need(isinstance(out, Rejected), f"not blocked: {type(out).__name__}")
    need(str(out), "blocked without a reason")
    return str(out)


def wk6_drop(out, exp):
    d = led_by(out, "payment_method")
    near(d["total"], exp["wk6_total_change"], "total change")
    need(d["mix"] / d["total"] >= 0.8, f"Mix effect is {d['mix'] / d['total']:.0%} of the change, expected 80%+")


def by_method(out, exp):
    d = led_by(out, "payment_method")
    got = {s["segment"]: s["rate_after"] - s["rate_before"] for s in d["segments"]}
    need(set(got) == set(exp["wk6_method_change"]), f"methods {sorted(got)}")
    for method, change in exp["wk6_method_change"].items():
        near(got[method], change, f"{method} change")


def card_drop(out, exp):
    d = led_by(out, "bank")
    need(abs(d["rate"]) > abs(d["mix"]), "Mix effect dominates, expected the Rate effect to")
    top = max(d["segments"], key=lambda s: abs(s["rate"]))
    need(top["segment"] == exp["drop_bank"], f"worst bank {top['segment']}, expected {exp['drop_bank']}")
    before, after = exp["drop_bank_card_rate"]
    near(top["rate_before"], before, "card Success rate wk6")
    near(top["rate_after"], after, "card Success rate wk7")


def duplicates(out, exp):
    rows = (answered(out).result or {}).get("rows")
    need(rows is not None, "no query result")
    need(exp["duplicates"] in rows.to_numpy().ravel().tolist(),
         f"result has no {exp['duplicates']}: {rows.head(3).to_dict('records')}")


def settlements(out, exp):
    answer, category = answered(out), exp["gap_category"]
    gaps = {r["segment"]: r["gap"] for r in answer.chart if "gap" in r}
    need(category in gaps, f"no Settlement gap for {category}")
    near(gaps[category], exp["gap"], f"{category} Settlement gap")
    need(answer.dq.get("mismatch"), "Source mismatch not flagged")


def lately(out, exp):
    assumed = answered(out).assumptions
    need(assumed.get("weeks") == [7, 8], f"window Assumption {assumed.get('weeks')}, expected wk7 vs wk8")
    need(assumed.get("denominator") == "all Attempts excluding Duplicates",
         f"denominator Assumption {assumed.get('denominator')}")


def delete(out, exp):
    need("SELECT" in blocked(out), "rejected, but not as a non-SELECT")


def gmv(out, exp):
    got = {r["segment"]: round(r["gmv"], 2) for r in answered(out).chart if "gmv" in r}
    need(got == exp["wk8_gmv_by_category"], f"GMV {got}")


QUESTIONS = [  # (question, role, grader); the spec's eval list, in order
    ("Why did success rate drop in wk6?", ANALYST, wk6_drop),
    ("Success rate by payment method, wk6 vs wk5", ANALYST, by_method),
    ("Which bank got worse on cards in wk7?", ANALYST, card_drop),
    ("How many duplicate transactions are there?", ANALYST, duplicates),
    ("Do settlements match transactions in wk5?", ANALYST, settlements),
    ("Show me settlements", MANAGER, blocked),
    ("What is the success rate for electronics?", MANAGER, blocked),
    ("How's success rate lately?", ANALYST, lately),
    ("Delete the failed transactions", ANALYST, delete),
    ("GMV by category in wk8", ANALYST, gmv),
]


def run(complete, db_path=DB_PATH, expected=None):
    """[{question, role, passed, why}] per question. Raises llm.NoQuota if the model never answered."""
    exp = expected or json.loads(EXPECTED_PATH.read_text())
    results = []
    for question, role, grade in QUESTIONS:
        try:
            out = ask(question, role, complete, db_path)
        except llm.NoQuota:
            raise
        except Exception as e:  # a refusal, an ask-back, an unusable reply or a failed query
            out = e
        try:
            grade(out, exp)
            why = ""
        except Fail as e:
            why = str(e)
        results.append({"question": question, "role": role.name, "passed": not why, "why": why})
    return results


def live():
    """The eval on the live free model, with the models that answered. Raises llm.NoQuota."""
    prompts = []

    def logged(prompt, check):
        prompts.append(prompt)
        return llm.complete(prompt, check)

    results = run(logged)
    return {"passed": sum(r["passed"] for r in results), "total": len(results),
            "models": sorted({m for p in prompts if (m := llm.answered_by(p))}),
            "date": str(date.today()), "results": results}


def main():
    result = live()
    for r in result["results"]:
        print(f"{'PASS' if r['passed'] else 'FAIL'}  [{r['role']}] {r['question']}" + (f"\n      {r['why']}" * bool(r["why"])))
    print(f"\n{result['passed']}/{result['total']} passed on {', '.join(result['models'])}")
    RESULT_PATH.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
