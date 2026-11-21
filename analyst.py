"""The analyst seam: (question, role, llm) -> Answer. No Streamlit in here.

`llm(prompt, check)` returns the model's text, preferring a reply that passes
`check`: first the plan, then the narration (headline, Hypotheses, Recommendations).
"""
import json
from dataclasses import dataclass

from compiler import compile_sql
from decomposition import decompose, explained
import dq
from executor import run
from generator import DB_PATH
from llm import ModelUnavailable
from semantic import DIMENSIONS
from validator import validate


@dataclass
class Fact:
    label: str
    value: float
    sql: str
    tables: list
    filters: list
    window: str
    unit: str  # "%" for a rate, "pp" for a change in rate


@dataclass
class Answer:
    headline: str
    facts: list
    decomposition: dict
    chart: list
    hypotheses: list  # model narration, not evidence
    recommendations: list  # model narration, not evidence
    dq: dict  # data-quality numbers, caveats and confidence
    assumptions: dict  # defaults chosen for what the question left open, editable by the user


class AskBack(Exception):
    """The question has no sensible default to assume; the message asks the user."""


FILTERABLE = [d for d in DIMENSIONS if d not in ("week", "failure_reason")]  # weeks are chosen separately
# Metrics ask() has an answer shape for: (weeks in the plan, dimensions it may filter on).
# A Success rate decomposition compares two Weeks; a Settlement gap reads one, unfiltered,
# since the Source mismatch check covers the whole Week. Other metrics wait in the semantic layer.
ANSWERED = {"success_rate": (2, FILTERABLE), "settlement_gap": (1, [])}
LEADS = ["payment_method", "bank", "category"]  # decomposed every time; the best one leads (D24)
WEEKS = range(1, 9)  # wk1 = 28 Sep 2026 ... wk8 = 16-22 Nov 2026


def plan_prompt(question):
    return (
        "Choose a plan for the question from the semantic layer. Reply with JSON only, e.g.\n"
        '{"metric": "success_rate", "weeks": [6, 7], "filters": {"payment_method": "card"}}\n'
        "weeks is [base week, current week] as integers 1-8 (wk8 is the latest); "
        "omit weeks when the question names no week.\n"
        "For whether Settlements match transactions, use settlement_gap with one week, e.g.\n"
        '{"metric": "settlement_gap", "weeks": [5]}\n'
        "filters is optional: {dimension: value} when the question names one Segment, "
        "e.g. payment_method is upi, card, netbanking or wallet.\n"
        f"Metrics: {', '.join(ANSWERED)}\nFilter dimensions (success_rate only): {', '.join(FILTERABLE)}\n"
        "Only if the question names none of these metrics, reply instead with "
        '{"ask": <one short question back to the user>}.\n'
        f"Question: {question}"
    )


def usable(plan):
    weeks, filters = plan.get("weeks"), plan.get("filters", {})
    if "ask" in plan:
        return isinstance(plan["ask"], str)
    if plan.get("metric") not in ANSWERED:
        return False
    n_weeks, dims = ANSWERED[plan["metric"]]
    return (isinstance(filters, dict) and set(filters) <= set(dims)
            and all(isinstance(v, str) for v in filters.values())
            and (weeks is None or isinstance(weeks, list) and len(weeks) == n_weeks
                 and all(type(w) is int and w in WEEKS for w in weeks)))


def narration_prompt(question, computed_headline, facts):
    lines = "\n".join(f"- {f.label}: {f.value * 100:.2f}{f.unit}" for f in facts)
    return (
        "You are a payments analyst. Using only the computed headline and Facts below, reply with JSON only:\n"
        '{"headline": <one sentence>, "hypotheses": [<possible cause>], "recommendations": [<next step>]}\n'
        f"Question: {question}\nComputed headline: {computed_headline}\nFacts:\n{lines}"
    )


def parse(text, fits):
    """The JSON object in `text` if it `fits`, else ValueError."""
    # ponytail: outermost {...} span, which handles prose and code fences; breaks if the
    # model adds a second JSON object. Use a JSON-mode request if that shows up.
    data = json.loads(text[text.find("{"):text.rfind("}") + 1])
    if not isinstance(data, dict) or not fits(data):
        raise ValueError(f"unusable reply: {text[:200]}")
    return data


def reply(llm, prompt, fits):
    """The model's JSON reply; `llm` gets the check so it can try another model."""
    text = llm(prompt, lambda t: parse(t, fits))
    try:
        return parse(text, fits)
    except ValueError:
        raise ModelUnavailable(f"the free model returned an unusable reply, try rephrasing: {text[:200]}")


def narrated(story):
    return (isinstance(story.get("headline"), str) and isinstance(story.get("hypotheses"), list)
            and isinstance(story.get("recommendations"), list))


# Latest complete Week vs the one before (D16); its SQL is shown when the model is down.
DEFAULT_PLAN = {"metric": "success_rate", "weeks": [7, 8], "filters": {}}


def leads(plan):
    """Lead dimensions worth splitting: a filtered one has a single Segment."""
    return [d for d in LEADS if d not in plan["filters"]]


def planned_sql(plan):
    """(sql, tables) for the overall query, then one per-Segment query per lead dimension."""
    return [validate(compile_sql(["attempts", "success_rate"], dims, plan["weeks"], plan["filters"]))
            for dims in [["week"]] + [["week", d] for d in leads(plan)]]


def ask(question, role, llm, db_path=DB_PATH, weeks=None):
    """`weeks` re-runs the question with an edited window Assumption."""
    try:
        plan = reply(llm, plan_prompt(question), usable)
    except ModelUnavailable as e:
        e.sql = [sql for sql, _ in planned_sql(DEFAULT_PLAN)]
        raise
    if "ask" in plan:
        raise AskBack(plan["ask"])
    assumptions = {}
    if weeks is not None:
        plan["weeks"] = assumptions["weeks"] = weeks
        if not usable(plan):
            raise ValueError(f"not a window for {plan['metric']}: {weeks}")
    if "weeks" not in plan:  # latest complete Week(s) (D16)
        plan["weeks"] = assumptions["weeks"] = DEFAULT_PLAN["weeks"][-ANSWERED[plan["metric"]][0]:]
    weeks = plan["weeks"]
    if plan["metric"] == "settlement_gap":
        return settlement_answer(question, llm, weeks[0], db_path, assumptions)
    assumptions["denominator"] = "all Attempts excluding Duplicates"  # D19
    base, current = weeks
    filters = plan.setdefault("filters", {})
    cited = [f"{k} = {v}" for k, v in filters.items()]
    window = f"wk{base} vs wk{current}"

    (overall_sql, overall_tables), *split_sql = planned_sql(plan)
    overall = run(overall_sql, db_path)
    if set(overall["week"]) != set(weeks):  # e.g. a filter value the data does not have
        e = ModelUnavailable(f"No Attempts match {', '.join(cited)} in {window}; try rephrasing.")
        e.sql = [overall_sql]
        raise e
    splits = []
    for dim, (sql, tables) in zip(leads(plan), split_sql):
        seg = run(sql, db_path)
        by_week = {w: {r[dim]: (r["attempts"], r["success_rate"]) for _, r in g.iterrows()}
                   for w, g in seg.groupby("week")}
        splits.append(({"dimension": dim, **decompose(by_week[base], by_week[current])}, sql, tables, by_week))
    d, seg_sql, seg_tables, by_week = max(splits, key=lambda s: explained(s[0]))

    rates = overall.set_index("week")["success_rate"]
    facts = [Fact(f"Success rate wk{w}", float(rates[w]), overall_sql, overall_tables, cited, window, "%")
             for w in weeks]
    facts += [Fact(f"{s['segment']} Success rate change", s["rate_after"] - s["rate_before"],
                   seg_sql, seg_tables, cited, window, "pp") for s in d["segments"]]

    try:
        story = reply(llm, narration_prompt(question, headline(d, base, current, filters), facts), narrated)
    except ModelUnavailable as e:
        e.sql = [overall_sql] + [sql for _, sql, _, _ in splits]
        raise
    return Answer(story["headline"], facts, d,
                  [{k: s[k] for k in ("segment", "mix", "rate")} for s in d["segments"]],
                  story["hypotheses"], story["recommendations"], dq.check(db_path, weeks, [overall_sql, seg_sql], by_week),
                  assumptions)


def settlement_answer(question, llm, week, db_path, assumptions):
    """Settlement gap by category for one Week (D22)."""
    window = f"wk{week}"
    sql, tables = validate(compile_sql(["settlement_gap"], ["category"], [week]))
    rows = run(sql, db_path)
    gaps = {c: float(g) for c, g in zip(rows["category"], rows["settlement_gap"])}
    facts = [Fact(f"{c} Settlement gap {window}", g, sql, tables, [], window, "%") for c, g in gaps.items()]
    try:
        story = reply(llm, narration_prompt(question, gap_headline(gaps, window), facts), narrated)
    except ModelUnavailable as e:
        e.sql = [sql]
        raise
    return Answer(story["headline"], facts, {}, [{"segment": c, "gap": g} for c, g in gaps.items()],
                  story["hypotheses"], story["recommendations"], dq.check(db_path, [week], [sql], {}), assumptions)


def gap_headline(gaps, window):
    off = {c: g for c, g in gaps.items() if abs(g) > dq.MISMATCH}
    if not off:
        return f"Settlements match successful Attempt value within {dq.MISMATCH:.1%} for every category in {window}."
    worst = max(off, key=lambda c: abs(off[c]))
    side = "below" if off[worst] < 0 else "above"
    return (f"Settlements for {worst} are {abs(off[worst]):.1%} {side} successful Attempt value in {window}; "
            f"{len(gaps) - len(off)} of {len(gaps)} categories match within {dq.MISMATCH:.1%}.")


def headline(d, base, current, filters):
    scope = "".join(f" for {v}" for v in filters.values())
    label = d["dimension"].replace("_", " ")
    direction = "fell" if d["total"] < 0 else "rose"
    if abs(d["mix"]) >= abs(d["rate"]):
        driver = f"a mix shift: traffic moved between {label}s, while rates within each {label} held"
        share = d["mix"] / d["total"]
    else:
        top = max(d["segments"], key=lambda s: abs(s["rate"]))
        driver = (f"a rate change within {label}s, not a shift in traffic mix; {top['segment']} "
                  f"went from {top['rate_before']:.1%} to {top['rate_after']:.1%}")
        share = d["rate"] / d["total"]
    return (f"Success rate{scope} {direction} {abs(d['total']) * 100:.1f}pp from wk{base} to wk{current}; "
            f"{share:.0%} of it is {driver}.")
