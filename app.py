import json
import os
import textwrap
from html import escape

import pandas as pd
import streamlit as st

import evaluate
import generator
import llm
from analyst import WEEKS, AskBack, ask, shown
from validator import ANALYST, Rejected, Role

COL = 86  # characters per line: the 774px column at 9px per Source Code Pro character

st.set_page_config(page_title="AI Business Analyst")
st.html("""<style>
.block-container {max-width: 870px; padding: 54px 48px 108px}
.stMain {counter-reset: ln}
.stMain [data-testid="stVerticalBlock"] {gap: 0}
header[data-testid="stHeader"] {background: transparent}
section[data-testid="stSidebar"] {min-width: 280px}
.doc {text-transform: uppercase; line-height: 27px}
.ln {position: relative; min-height: 27px; white-space: pre-wrap}
.stMain .ln::before {counter-increment: ln; content: counter(ln); position: absolute; left: -40px; width: 24px;
      text-align: right; font-size: 10px; color: #9a9a9a; text-transform: none}
.row {display: flex; justify-content: space-between; gap: 18px}
.c {text-align: center}
.rule {display: block; overflow: hidden; white-space: nowrap}
.inv {background: #111; color: #fff; padding: 0 13.5px}
.band {background: #0a0a0a; color: #f2f2f2; box-shadow: 0 0 0 100vmax #0a0a0a; clip-path: inset(0 -100vmax);
       padding: 27px 0; margin: 27px 0}
.band .ln::before {color: #5c5c5c}
.dim {color: #8a8a8a}
.g {display: grid; grid-template-columns: 14ch 1fr 1fr; column-gap: 2ch}
.g1 {display: grid; grid-template-columns: 22ch 1fr; column-gap: 2ch}
.bar {display: inline-block; height: 9px; margin-right: 9px;
      background: radial-gradient(circle, #8a8a8a 1px, transparent 1.4px) 0 0 / 4px 4px}
.bar.on {background: #f2f2f2}
.meter {letter-spacing: 2px}
.head {position: relative}
.forest {position: absolute; top: 4px; right: 0; width: 344px; height: 100px}
.forest i {position: absolute; left: 0; top: 0}
.forest .t {width: 344px; height: 96px; animation: grow .6s steps(6, end) both}
.forest .px {width: 3px; height: 3px}
.forest .ground {top: 96px; width: 344px; height: 1px;
       background: repeating-linear-gradient(90deg, #111 0 3px, transparent 3px 8px)}
.forest .w {animation: wind 3.2s steps(1, end) infinite; animation-delay: var(--d)}
@keyframes grow {from {transform: scaleY(0)}}
@keyframes wind {50% {transform: translateX(4px)}}
.forest .snow {width: 2px; height: 2px; background: #9a9a9a; animation: snow 6s steps(24, end) infinite}
@keyframes snow {to {transform: translateY(94px)}}
@media (prefers-reduced-motion: reduce) {.forest * {animation: none !important}}
@media (max-width: 760px) {.forest {display: none}}
summary {list-style: none; cursor: pointer}
summary::-webkit-details-marker {display: none}
summary:hover {background: #f4f4f4}
details > summary > span:first-child::before {content: "+ "}
details[open] > summary > span:first-child::before {content: "- "}
details pre {text-transform: none; background: #f4f4f4; margin: 0; padding: 13.5px; font-size: 13px;
       line-height: 20px; white-space: pre-wrap}
details div.ln {color: #6b6b6b}
[data-testid="stTextInput"] input {font-size: 15px; padding: 10px 13.5px}
[data-testid="stPopover"] button {border: 0; background: transparent; padding: 0 4.5px; min-height: 27px}
[data-testid="stPopover"] button:hover {background: #111; color: #fff}
[data-testid="stPopover"] button p {text-transform: uppercase; font-size: 15px}
[data-testid="stPopover"] button p::before {content: "["}
[data-testid="stPopover"] button p::after {content: "]"}
</style>""")  # ponytail: data-testid selectors are Streamlit internals; recheck on an upgrade


def ln(html="", cls=""):
    """One numbered line of the document; `html` is already escaped."""
    return f'<div class="ln {cls}">{html}</div>'


def lines(text, first="", rest=""):
    """Plain text wrapped to the column, one numbered line per wrapped line, with an optional hanging prefix."""
    wrapped = textwrap.wrap(text, COL - len(first)) or [""]
    return "".join(ln(escape((first if i == 0 else rest) + part)) for i, part in enumerate(wrapped))


def row(left, right=""):
    return ln(f"<span>{left}</span><span>{right}</span>", "row")


BLANK, RULE = ln(), ln(f'<span class="rule">{"=" * COL}</span>')


def doc(*parts, cls=""):
    st.html(f'<div class="doc {cls}">{"".join(parts)}</div>')


def notice(tag, text):
    doc(BLANK, ln(f'<span class="inv">{escape(tag)}</span>'), BLANK, lines(text), BLANK)


def bar(value, top, on, width):
    """A bar `width` px long at `top`, solid for the series that matters and dotted for the other."""
    return f'<i class="bar{" on" if on else ""}" style="width:{abs(value) / (top or 1) * width:.0f}px"></i>'


def forest():
    """A pixel-art pine forest: each tree grows in on load, its crown sways a pixel in the wind, and snow falls.
    Pixels are box-shadows on one element, since st.html strips <svg>."""
    trees = []
    for i, (x, tiers) in enumerate(((0, 2), (10, 4), (24, 5), (40, 3), (51, 4), (66, 2), (75, 3))):
        widths = [t + r for t in range(tiers) for r in range(4)] + [0, 0]  # tiers stepping in 2px, then a trunk
        h, cx = len(widths), x + tiers + 2
        crown, rest = [], []
        for y, w in enumerate(widths):
            (crown if y < h // 3 else rest).extend(  # dithered light on the left side
                f"{(cx + dx) * 4}px {(24 - h + y) * 4}px {'#9a9a9a' if dx < 0 and (dx + y) % 3 == 0 else '#111'}"
                for dx in range(-w, w + 1))
        trees.append(f'<i class="t" style="--d:{-i * .7:.1f}s;animation-delay:{i * .12:.2f}s;'
                     f'transform-origin:{cx * 4}px 96px"><i class="px" style="box-shadow:{",".join(rest)}"></i>'
                     f'<i class="px w" style="box-shadow:{",".join(crown)}"></i></i>')
    snow = "".join(f'<i class="snow" style="left:{x}px;animation-delay:{-d}s"></i>'
                   for x, d in ((22, 0), (70, 3.1), (128, 1.4), (183, 4.6), (236, 2.2), (290, 5.3), (330, .7)))
    return f'<div class="forest" aria-hidden="true">{"".join(trees)}{snow}<i class="ground"></i></div>'


generator.ensure(generator.DB_PATH)
try:
    os.environ.setdefault("OPENROUTER_API_KEY", st.secrets["OPENROUTER_API_KEY"])
except (KeyError, FileNotFoundError):  # no key: the app still starts, questions show why
    pass

with st.sidebar:
    doc(ln("Signed in as"))
    role = ANALYST  # auth is mocked: the viewer picks a role (D15)
    if st.selectbox("Role", ["Analyst", "Merchant manager"], label_visibility="collapsed") == "Merchant manager":
        role = Role("Merchant manager", st.selectbox("Category", generator.CATEGORIES))
    st.caption("A Merchant manager sees only their category; the SQL validator enforces it.")
    st.divider()
    doc(ln("Quality check"))
    run_eval = st.button("Run eval", width="stretch")
    st.caption("Grades 10 known-answer questions on the free model.")

doc(forest(), ln("Pine Labs"), ln("Payments analytics"), ln(f"{len(WEEKS)} Weeks of payment Attempts, wk{WEEKS[0]} - wk{WEEKS[-1]}"),
    BLANK, ln('<span class="inv">AI Business Analyst: ask about Success rate, GMV or Settlements</span>'), BLANK,
    lines("Every number below comes from SQL that ran on the data. Anything a model wrote is labelled as such."),
    BLANK, cls="head")

if run_eval:  # 10 known-answer questions (D26)
    try:
        with st.spinner("Running the 10 eval questions on the free model"):
            result, source = evaluate.live(), "Run now on the free model (identical prompts replay saved replies)"
    except llm.NoQuota as e:  # no key or quota: the committed result, labelled
        result = json.loads(evaluate.RESULT_PATH.read_text())
        source = f"Free model unavailable ({e}), so this is the last committed result from {result['date']}"
    with st.expander(f"Eval pass rate: {result['passed']}/{result['total']}", expanded=True):
        st.caption(f"{source}. Models: {', '.join(result['models'])}. Graded on structured fields only.")
        st.dataframe(pd.DataFrame(result["results"])[["passed", "role", "question", "why"]], hide_index=True)
question = st.text_input("Ask a question", "Why did success rate drop in week 6?", label_visibility="collapsed",
                         placeholder="Ask a question about payments")
if st.session_state.get("asked") != question:  # a new question drops the edited window
    st.session_state.asked, st.session_state.weeks = question, None
if question:
    replayed = []  # demo prompts served from the replay cache (D30)
    try:
        with st.spinner("Planning, running SQL, checking data quality"):
            answer = ask(question, role, llm.with_replay(llm.complete, replayed), weeks=st.session_state.weeks)
    except (Rejected, AskBack, llm.ModelUnavailable) as e:
        answer = e  # shown after the banner, since st.stop() drops anything drawn later
    if replayed:
        notice("Replay mode", "The free model is unavailable (no key or rate-limited), so this demo question "
               "replays a cached model reply. Numbers, SQL and charts still come from running the pipeline; any "
               "cached headline, Hypotheses and Recommendations were written with Claude Code during development.")
    if isinstance(answer, Rejected):
        notice("Rejected", str(answer))
        for sql in answer.sql:
            st.code(sql, language="sql")
        st.stop()
    if isinstance(answer, AskBack):
        notice("Question back", str(answer))
        st.stop()
    if isinstance(answer, llm.ModelUnavailable):
        notice("Model unavailable", str(answer) + " SQL for this question:")
        for sql in answer.sql:
            st.code(sql, language="sql")
        st.stop()
    writer = "Claude Code during development" if replayed else "a free model"

    doc(BLANK, RULE, BLANK, row('<span class="inv">Answer</span>', "" if answer.result else f"headline by {writer}"),
        BLANK, lines(answer.headline), BLANK)
    chips = st.container(horizontal=True, gap="small")
    if "weeks" in answer.assumptions:
        weeks = answer.assumptions["weeks"]
        with chips.popover("Window: " + " vs ".join(f"wk{w}" for w in weeks)):
            # A comparison is always the chosen Week against the one before it.
            current = st.selectbox("Week", WEEKS[len(weeks) - 1:], index=weeks[-1] - len(weeks))
            if st.button("Re-run", type="primary"):
                st.session_state.weeks = list(range(current - len(weeks) + 1, current + 1))
                st.rerun()
    if "scope" in answer.assumptions:
        with chips.popover(f"Scope: {answer.assumptions['scope']}"):
            st.caption(f"A {role.name} sees only their category.")
    if "denominator" in answer.assumptions:
        with chips.popover(f"Denominator: {answer.assumptions['denominator']}"):
            st.caption("The only Success rate denominator the semantic layer defines (D19).")

    if answer.result:  # an ad-hoc question: the rows its model-written SQL returned
        doc(BLANK, ln("Exhibit A: result of model-written SQL", "c"), row(f"Tables: {escape(', '.join(answer.result['tables']))}"), BLANK)
        st.dataframe(answer.result["rows"], hide_index=True)
        st.code(answer.result["sql"], language="sql")
    else:
        d = answer.decomposition  # empty for a by-category answer (GMV, Settlement gap)
        if d:
            by = escape(d["dimension"].replace("_", " "))
            w0, w1 = answer.facts[0].window.split(" vs ")
            top = {k: max(s[k + w] for s in d["segments"] for w in ("_before", "_after")) for k in ("share", "rate")}

            def cell(s, key, after):
                v = s[key + ("_after" if after else "_before")]
                return f'<span class="{"" if after else "dim"}">{bar(v, top[key], after, 230)}{v * 100:.1f}</span>'

            band = [ln("Exhibit A: why it moved", "c"),
                    row(f"By {by}, {w0} vs {w1}", f'{bar(1, 1, False, 18)}{w0}  {bar(1, 1, True, 18)}{w1}'), BLANK,
                    ln("<span></span><span>Share of Attempts, %</span><span>Success rate, %</span>", "g")]
            for s in d["segments"]:
                band += [ln(f"<span>{escape(s['segment'])}</span>{cell(s, 'share', False)}{cell(s, 'rate', False)}", "g"),
                         ln(f"<span></span>{cell(s, 'share', True)}{cell(s, 'rate', True)}", "g")]
            band += [BLANK, lines(f"Total {d['total'] * 100:+.2f}pp = Mix effect {d['mix'] * 100:+.2f}pp + Rate effect "
                                  f"{d['rate'] * 100:+.2f}pp. Mix effect: Attempts moving between {by}s. Rate "
                                  "effect: rates changing within them.")]
        else:
            gmv = "gmv" in answer.chart[0]
            values = [c["gmv" if gmv else "gap"] * (1 if gmv else 100) for c in answer.chart]
            hi = max(range(len(values)), key=lambda i: abs(values[i]))  # the bar the headline names
            peak = abs(values[hi])
            band = [ln("Exhibit A: by category", "c"),
                    row("GMV, successful Attempts, Duplicates removed" if gmv
                        else "Settlement gap, % of successful Attempt value", escape(answer.facts[0].window)), BLANK]
            for i, (c, v) in enumerate(zip(answer.chart, values)):
                band.append(ln(f"<span>{escape(c['segment'])}</span><span class=\"{'' if i == hi else 'dim'}\">"
                               f"{bar(v, peak, i == hi, 420)}{f'₹{v:,.0f}' if gmv else f'{v:+.2f}%'}</span>", "g1"))
        doc(*band, cls="band")

        facts = "".join(
            f'<details><summary class="ln row"><span>{escape(f.label)}</span>'
            f'<span>{f"{f.value * 100:+.2f}pp" if f.unit == "pp" else escape(shown(f))}</span></summary>'
            f"<pre>{escape(f.sql)}</pre>{ln('Tables: ' + escape(', '.join(f.tables)))}"
            f"{ln('Filters: ' + escape(', '.join(f.filters) or 'none'))}{ln('Window: ' + escape(f.window))}</details>"
            for f in answer.facts)
        doc(ln("Exhibit B: Facts from executed SQL", "c"), row("Fact, click for its SQL", "Value"), facts, BLANK)

    narration = [(t, i) for t, i in (("Hypotheses", answer.hypotheses), ("Recommendations", answer.recommendations)) if i]
    if narration:
        parts = [RULE, BLANK, ln("Exhibit C: model narration", "c"),
                 lines(f"Written by {writer}. Not evidence: check it against Exhibit B."), BLANK]
        for title, items in narration:
            parts += [ln(title), *(lines(item, f"{title[0]}{n}  ", "    ") for n, item in enumerate(items, 1)), BLANK]
        doc(*parts)

    level, _, why = answer.dq["confidence"].partition(": ")
    lit = {"High": 3, "Medium": 2}.get(level, 1)
    doc(RULE, BLANK, row('<span class="inv">Caveats</span>',
                         f'{escape(level)} confidence <span class="meter">{"■" * lit}{"□" * (3 - lit)}</span>'),
        BLANK, lines(why), *(lines(c, "- ", "  ") for c in answer.dq["caveats"]))
