"""The analyst seam: (question, role, llm) -> Answer. No Streamlit in here.

`llm` is any callable taking a prompt string and returning the plan as JSON.
"""
import json
from dataclasses import dataclass

from compiler import compile_sql
from decomposition import decompose
from executor import run
from generator import DB_PATH
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


def plan_prompt(question):
    return (
        "Choose a plan for the question from the semantic layer. Reply with JSON only:\n"
        '{"metric": <metric>, "dimensions": [<dimension>], "weeks": [<base week>, <current week>]}\n'
        f"Metrics: {', '.join(METRICS)}\nDimensions: {', '.join(DIMENSIONS)}\n"
        f"Question: {question}"
    )


def ask(question, role, llm, db_path=DB_PATH):
    plan = json.loads(llm(plan_prompt(question)))
    weeks = plan["weeks"]
    base, current = weeks
    dim = plan["dimensions"][0]
    window = f"wk{base} vs wk{current}"

    def query(dimensions):
        sql, tables = validate(compile_sql(["attempts", "success_rate"], dimensions, weeks))
        return run(sql, db_path), sql, tables

    overall, overall_sql, overall_tables = query(["week"])
    seg, seg_sql, seg_tables = query(["week", dim])

    by_week = {w: {r[dim]: (r["attempts"], r["success_rate"]) for _, r in g.iterrows()}
               for w, g in seg.groupby("week")}
    d = {"dimension": dim, **decompose(by_week[base], by_week[current])}

    rates = overall.set_index("week")["success_rate"]
    facts = [Fact(f"Success rate wk{w}", float(rates[w]), overall_sql, overall_tables, [], window, "%")
             for w in weeks]
    facts += [Fact(f"{s['segment']} Success rate change", s["rate_after"] - s["rate_before"],
                   seg_sql, seg_tables, [], window, "pp") for s in d["segments"]]

    return Answer(headline(d, base, current), facts, d,
                  [{k: s[k] for k in ("segment", "mix", "rate")} for s in d["segments"]])


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
