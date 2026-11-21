"""The analyst seam: (question, role, llm) -> Answer. No Streamlit in here.

`llm(prompt, check)` returns the model's text, preferring a reply that passes
`check`: first the plan, then the narration (headline, Hypotheses, Recommendations).
"""
import json
from dataclasses import dataclass

from compiler import compile_sql
from decomposition import decompose
from executor import run
from generator import DB_PATH
from llm import ModelUnavailable
from semantic import DIMENSIONS, METRICS
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


SPLITS = [d for d in DIMENSIONS if d != "week"]  # weeks are chosen separately
WEEKS = range(1, 9)  # wk1 = 28 Sep 2026 ... wk8 = 16-22 Nov 2026


def plan_prompt(question):
    return (
        "Choose a plan for the question from the semantic layer. Reply with JSON only, e.g.\n"
        '{"metric": "success_rate", "dimensions": ["payment_method"], "weeks": [5, 6]}\n'
        "weeks is [base week, current week] as integers 1-8 (wk8 is the latest).\n"
        f"Metrics: {', '.join(METRICS)}\nDimensions: {', '.join(SPLITS)}\n"
        f"Question: {question}"
    )


def usable(plan):
    weeks = plan.get("weeks")
    return (plan.get("metric") in METRICS and plan.get("dimensions")
            and set(plan["dimensions"]) <= set(SPLITS)
            and isinstance(weeks, list) and len(weeks) == 2
            and all(type(w) is int and w in WEEKS for w in weeks))


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
DEFAULT_PLAN = {"metric": "success_rate", "dimensions": ["payment_method"], "weeks": [7, 8]}


def planned_sql(plan):
    """(sql, tables) for the overall and per-segment queries of a plan."""
    return [validate(compile_sql(["attempts", "success_rate"], dims, plan["weeks"]))
            for dims in (["week"], ["week", plan["dimensions"][0]])]


def ask(question, role, llm, db_path=DB_PATH):
    try:
        plan = reply(llm, plan_prompt(question), usable)
    except ModelUnavailable as e:
        e.sql = [sql for sql, _ in planned_sql(DEFAULT_PLAN)]
        raise
    weeks = plan["weeks"]
    base, current = weeks
    dim = plan["dimensions"][0]
    window = f"wk{base} vs wk{current}"

    (overall_sql, overall_tables), (seg_sql, seg_tables) = planned_sql(plan)
    overall, seg = run(overall_sql, db_path), run(seg_sql, db_path)

    by_week = {w: {r[dim]: (r["attempts"], r["success_rate"]) for _, r in g.iterrows()}
               for w, g in seg.groupby("week")}
    d = {"dimension": dim, **decompose(by_week[base], by_week[current])}

    rates = overall.set_index("week")["success_rate"]
    facts = [Fact(f"Success rate wk{w}", float(rates[w]), overall_sql, overall_tables, [], window, "%")
             for w in weeks]
    facts += [Fact(f"{s['segment']} Success rate change", s["rate_after"] - s["rate_before"],
                   seg_sql, seg_tables, [], window, "pp") for s in d["segments"]]

    try:
        story = reply(llm, narration_prompt(question, headline(d, base, current), facts), narrated)
    except ModelUnavailable as e:
        e.sql = [overall_sql, seg_sql]
        raise
    return Answer(story["headline"], facts, d,
                  [{k: s[k] for k in ("segment", "mix", "rate")} for s in d["segments"]],
                  story["hypotheses"], story["recommendations"])


def headline(d, base, current):
    label = d["dimension"].replace("_", " ")
    direction = "fell" if d["total"] < 0 else "rose"
    if abs(d["mix"]) >= abs(d["rate"]):
        driver = f"a mix shift: traffic moved between {label}s, while rates within each {label} held"
        share = d["mix"] / d["total"]
    else:
        driver = f"a rate change within {label}s, not a shift in traffic mix"
        share = d["rate"] / d["total"]
    return (f"Success rate {direction} {abs(d['total']) * 100:.1f}pp from wk{base} to wk{current}; "
            f"{share:.0%} of it is {driver}.")
