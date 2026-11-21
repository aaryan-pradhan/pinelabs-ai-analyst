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
from semantic import DIMENSIONS, TABLES
from validator import Rejected, validate


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
    result: dict = None  # ad-hoc answers only: {"sql", "tables", "rows"}, rows as a DataFrame
    narrated: bool = True  # False: the model was unavailable, so the headline is the computed one


class AskBack(Exception):
    """The question has no sensible default to assume; the message asks the user."""


FILTERABLE = [d for d in DIMENSIONS if d not in ("week", "failure_reason")]  # weeks are chosen separately
# Metrics ask() has an answer shape for: (weeks in the plan, dimensions it may filter on).
# A Success rate decomposition compares two Weeks; a Settlement gap reads one, unfiltered,
# since the Source mismatch check covers the whole Week. Other metrics wait in the semantic layer.
ANSWERED = {"success_rate": (2, FILTERABLE), "settlement_gap": (1, []), "gmv": (1, [])}
# One Week, split by category: metric -> (label, Fact unit, chart key).
BY_CATEGORY = {"settlement_gap": ("Settlement gap", "%", "gap"), "gmv": ("GMV", "₹", "gmv")}
LEADS = ["payment_method", "bank", "category"]  # decomposed every time; the best one leads (D24)
TABLE_LIST = "; ".join(f"{t}({', '.join(cols)})" for t, cols in TABLES.items())
WEEKS = range(1, 9)  # wk1 = 28 Sep 2026 ... wk8 = 16-22 Nov 2026


def plan_prompt(question):
    return (
        "Choose a plan for the question from the semantic layer. Reply with JSON only, e.g.\n"
        '{"metric": "success_rate", "weeks": [6, 7], "filters": {"payment_method": "card"}}\n'
        "weeks is [base week, current week] as integers 1-8 (wk8 is the latest); "
        "omit weeks when the question names no week.\n"
        "For whether Settlements match transactions, use settlement_gap with one week, e.g.\n"
        '{"metric": "settlement_gap", "weeks": [5]}\n'
        'For GMV, use gmv with one week; it is split by category, e.g. {"metric": "gmv", "weeks": [8]}\n'
        "filters is optional: {dimension: value} when the question names one Segment, "
        "e.g. payment_method is upi, card, netbanking or wallet.\n"
        f"Metrics: {', '.join(ANSWERED)}\nFilter dimensions (success_rate only): {', '.join(FILTERABLE)}\n"
        "If no metric above fits but these tables can answer it, reply instead with the one DuckDB "
        'statement the question asks for, e.g. {"sql": "SELECT transactions.status, COUNT(*) AS n '
        'FROM transactions GROUP BY 1 ORDER BY n DESC"}\n'
        f"Tables: {TABLE_LIST}. Join merchants and banks to transactions on merchant_id and bank_id; "
        "write full table names, never table aliases.\n"
        "Only if the question is too vague for either, reply instead with "
        '{"ask": <one short question back to the user>}.\n'
        f"Question: {question}"
    )


def usable(plan):
    weeks, filters = plan.get("weeks"), plan.get("filters", {})
    for free_text in ("ask", "sql"):
        if free_text in plan:
            return isinstance(plan[free_text], str) and bool(plan[free_text].strip())
    if plan.get("metric") not in ANSWERED:
        return False
    n_weeks, dims = ANSWERED[plan["metric"]]
    return (isinstance(filters, dict) and set(filters) <= set(dims)
            and all(isinstance(v, str) for v in filters.values())
            and (weeks is None or isinstance(weeks, list) and len(weeks) == n_weeks
                 and all(type(w) is int and w in WEEKS for w in weeks)))


def narration_prompt(question, computed_headline, facts):
    lines = "\n".join(f"- {f.label}: {shown(f)}" for f in facts)
    return (
        "You are a payments analyst. Using only the computed headline and Facts below, reply with JSON only:\n"
        '{"headline": <one sentence>, "hypotheses": [<possible cause>], "recommendations": [<next step>]}\n'
        f"Question: {question}\nComputed headline: {computed_headline}\nFacts:\n{lines}"
    )


def shown(fact):
    # + 0.0 turns a rounded -0.0 into 0.0: a zero's sign is float noise that would change the prompt.
    return f"₹{fact.value:,.2f}" if fact.unit == "₹" else f"{round(fact.value * 100, 2) + 0.0:.2f}{fact.unit}"


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


def planned_sql(plan, role):
    """(sql, tables) for the overall query, then one per-Segment query per lead dimension."""
    return [validate(compile_sql(["attempts", "success_rate"], dims, plan["weeks"], plan["filters"]), role)
            for dims in [["week"]] + [["week", d] for d in leads(plan)]]


def ask(question, role, llm, db_path=DB_PATH, weeks=None):
    """`weeks` re-runs the question with an edited window Assumption."""
    try:
        plan = reply(llm, plan_prompt(question), usable)
    except ModelUnavailable as e:
        e.sql = [sql for sql, _ in planned_sql(DEFAULT_PLAN, role)]
        raise
    if "ask" in plan:
        raise AskBack(plan["ask"])
    if "sql" in plan:
        return ad_hoc_answer(plan["sql"], role, db_path)
    assumptions = {}
    if weeks is not None:
        plan["weeks"] = assumptions["weeks"] = weeks
        if not usable(plan):
            raise ValueError(f"not a window for {plan['metric']}: {weeks}")
    if plan.get("weeks") is None:  # latest complete Week(s) (D16)
        plan["weeks"] = assumptions["weeks"] = DEFAULT_PLAN["weeks"][-ANSWERED[plan["metric"]][0]:]
    weeks = plan["weeks"]
    if plan["metric"] in BY_CATEGORY:
        return category_answer(question, role, llm, plan["metric"], weeks[0], db_path, assumptions)
    assumptions["denominator"] = "all Attempts excluding Duplicates"  # D19
    base, current = weeks
    filters = plan.setdefault("filters", {})
    if role.category is not None:  # the validator scopes the SQL anyway
        filters.setdefault("category", role.category)
        assumptions["scope"] = role.category
    cited = [f"{k} = {v}" for k, v in filters.items()]
    window = f"wk{base} vs wk{current}"

    (overall_sql, overall_tables), *split_sql = planned_sql(plan, role)
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

    computed = headline(d, base, current, filters)
    checks = dq.check(db_path, weeks, [overall_sql, seg_sql], by_week, role.category)
    try:
        story = reply(llm, narration_prompt(question, computed, facts), narrated)
    except ModelUnavailable:  # the Facts stand without narration, e.g. an edited window the replay cache lacks
        story = None
        checks["caveats"].append("The free model was unavailable, so the headline is computed from the Facts "
                                 "and there are no Hypotheses or Recommendations.")
    return Answer(story["headline"] if story else computed, facts, d,
                  [{k: s[k] for k in ("segment", "mix", "rate")} for s in d["segments"]],
                  story["hypotheses"] if story else [], story["recommendations"] if story else [], checks,
                  assumptions, narrated=story is not None)


def ad_hoc_answer(sql, role, db_path):
    """Model-written SQL for a question the semantic layer's metrics cannot express (D6)."""
    try:
        sql, tables = validate(sql, role)
        rows = run(sql, db_path)
    except Rejected as e:
        e.sql = [sql]
        raise
    assumptions = {} if role.category is None else {"scope": role.category}
    caveats = ["Model-written SQL outside the semantic layer's metrics: it reads raw tables, "
               "so Duplicates are counted unless the SQL removes them. Check the SQL before relying on it."]
    return Answer("Ad-hoc query: model-written SQL, checked by the validator before it ran.",
                  facts=[], decomposition={}, chart=[], hypotheses=[], recommendations=[],
                  dq={"confidence": "Low: the SQL was written by a free model.", "caveats": caveats},
                  assumptions=assumptions, result={"sql": sql, "tables": tables, "rows": rows})


def category_answer(question, role, llm, metric, week, db_path, assumptions):
    """A metric by category for one Week: GMV, or the Settlement gap (D22)."""
    label, unit, key = BY_CATEGORY[metric]
    window = f"wk{week}"
    sql, tables = validate(compile_sql([metric], ["category"], [week]), role)  # a manager is scoped here
    if role.category is not None:
        assumptions["scope"] = role.category
    rows = run(sql, db_path)
    values = {c: float(v) for c, v in zip(rows["category"], rows[metric])}
    facts = [Fact(f"{c} {label} {window}", v, sql, tables, [], window, unit) for c, v in values.items()]
    computed = gap_headline(values, window) if metric == "settlement_gap" else gmv_headline(values, window)
    try:
        story = reply(llm, narration_prompt(question, computed, facts), narrated)
    except ModelUnavailable as e:
        e.sql = [sql]
        raise
    return Answer(story["headline"], facts, {}, [{"segment": c, key: v} for c, v in values.items()],
                  story["hypotheses"], story["recommendations"],
                  dq.check(db_path, [week], [sql], {}, role.category), assumptions)


def gmv_headline(gmv, window):
    top = max(gmv, key=gmv.get)
    total = sum(gmv.values())
    return f"GMV in {window} was ₹{total:,.0f}; {top} led with ₹{gmv[top]:,.0f} ({gmv[top] / total:.0%})."


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
