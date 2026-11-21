import json
import os
import re
import textwrap
from html import escape

import pandas as pd
import streamlit as st

import evaluate
import generator
import llm
import garden
from analyst import WEEKS, AskBack, ask, shown
from validator import ANALYST, Rejected, Role

COL = 86  # characters per line: the 774px column at 9px per Source Code Pro character

st.set_page_config(page_title="AI Business Analyst", page_icon=garden.icon())
st.html("""<style>
:root {--paper: #fdfcf7; --ink: #1d2f2a; --mute: #6f7f76; --rule: #d9d1bd; --label: #1d3a33; --field: #f1eee4;
       --up: #2b6cb0; --down: #e8572e}
html[data-mode=night] {--paper: #13241f; --ink: #efe6d2; --mute: #8fa59a; --rule: #2e4a40; --label: #f2b25a;
       --field: #1b302a; --up: #3d8bd9; --down: #e0683a}  /* rise and fall pass the colour-blind check */
.stApp, .stMain, header[data-testid="stHeader"] {background: transparent !important; color: var(--ink)}
.stApp *, .stMain * {color: inherit}
.block-container {max-width: 870px; padding: 54px 48px 108px; background: var(--paper); margin: 48px auto 120px;
       box-shadow: 0 0 0 4px var(--label), 0 0 0 8px var(--paper), 0 0 0 12px var(--label), 16px 16px 0 12px rgba(0,0,0,.3);
       position: relative; z-index: 2}
.stMain {counter-reset: ln}
.stMain [data-testid="stVerticalBlock"] {gap: 0}
section[data-testid="stSidebar"] {min-width: 280px; z-index: 3; color: var(--ink);
       background: color-mix(in srgb, var(--paper) 88%, transparent) !important}
input, textarea, [data-baseweb="select"] > div, [data-testid="stTextInput"] > div > div, button {
       background: var(--field) !important; color: var(--ink) !important; border-color: var(--rule) !important}
.doc {text-transform: uppercase; line-height: 27px}
.ln {position: relative; min-height: 27px; white-space: pre-wrap}
.stMain .ln::before {counter-increment: ln; content: counter(ln); position: absolute; left: -40px; width: 24px;
      text-align: right; font-size: 10px; color: var(--mute); text-transform: none}
.row {display: flex; justify-content: space-between; gap: 18px}
.c {text-align: center}
.rule {display: block; overflow: hidden; white-space: nowrap}
.inv {background: var(--label); color: var(--paper); padding: 0 13.5px}
.band {padding: 27px 0; margin: 27px 0}
.dim {color: var(--mute)}
.g {display: grid; grid-template-columns: 14ch 1fr 1fr; column-gap: 2ch}
.g1 {display: grid; grid-template-columns: 22ch 1fr; column-gap: 2ch}
.w {display: grid; grid-template-columns: 26ch 1fr 16ch; column-gap: 2ch}
.w > span:last-child {text-align: right}
.wt {position: relative; display: block; height: 27px}
.wt i {position: absolute}
.w0 {top: 2px; bottom: 2px; width: 1px; background: var(--rule)}
.wb {top: 9px; height: 9px; background: var(--up)}
.wb.down {background: var(--down)}
.wb.tot {background: var(--ink)}
.wb.noise {opacity: .4}
.wk {top: 10px; height: 7px; color: var(--ink); border: solid currentColor; border-width: 0 1px;
     background: linear-gradient(currentColor, currentColor) center / 100% 1px no-repeat}
.bar {display: inline-block; height: 9px; margin-right: 9px;
      background: radial-gradient(circle, var(--mute) 1px, transparent 1.4px) 0 0 / 4px 4px}
.bar.on {background: var(--ink)}
.meter {letter-spacing: 2px}
summary {list-style: none; cursor: pointer}
summary::-webkit-details-marker {display: none}
summary:hover {background: var(--field)}
details > summary > span:first-child::before {content: "+ "}
details[open] > summary > span:first-child::before {content: "- "}
details pre {text-transform: none; background: var(--field); margin: 0; padding: 13.5px; font-size: 13px;
       line-height: 20px; white-space: pre-wrap}
details div.ln {color: var(--mute)}
[data-testid="stTextInput"] input {font-size: 15px; padding: 10px 13.5px}
[data-testid="stPopover"] button {border: 0; background: transparent !important; padding: 0 4.5px; min-height: 27px}
[data-testid="stPopover"] button:hover {background: var(--label) !important; color: var(--paper) !important}
[data-testid="stPopover"] button p {text-transform: uppercase; font-size: 15px}
[data-testid="stPopover"] button p::before {content: "["}
[data-testid="stPopover"] button p::after {content: "]"}
</style>""")  # ponytail: data-testid selectors are Streamlit internals; recheck on an upgrade


def ln(html="", cls=""):
    """One numbered line of the document; `html` is already escaped."""
    return f'<div class="ln {cls}">{html}</div>'


def spell(text):
    """Write out the pipeline's short forms for the reader: wk5 as Week 5, 4.00pp as 4.00 percentage points."""
    return re.sub(r"(\d)pp\b", r"\1 percentage points", re.sub(r"\bwk(\d+)", r"Week \1", text))


def lines(text, first="", rest=""):
    """Plain text wrapped to the column, one numbered line per wrapped line, with an optional hanging prefix."""
    wrapped = textwrap.wrap(spell(text), COL - len(first)) or [""]
    return "".join(ln(escape((first if i == 0 else rest) + part)) for i, part in enumerate(wrapped))


def row(left, right=""):
    return ln(f"<span>{left}</span><span>{right}</span>", "row")


BLANK, RULE = ln(), ln(f'<span class="rule">{"=" * COL}</span>')


def doc(*parts, cls=""):
    st.html(f'<div class="doc {cls}">{"".join(parts)}</div>')


def label(text):
    return f'<span class="inv">{escape(text)}</span>'


def notice(tag, text):
    doc(BLANK, ln(label(tag)), BLANK, lines(text), BLANK)


def bar(value, top, on, width):
    """A bar `width` px long at `top`, solid for the series that matters and dotted for the other."""
    return f'<i class="bar{" on" if on else ""}" style="width:{abs(value) / (top or 1) * width:.0f}px"></i>'


def bridge(d, start, end, by, w0, w1):
    """The change as a walk: the start rate, the Mix effect, each Segment's Rate effect with its 95% interval, the end rate."""
    segs = sorted(d["segments"], key=lambda s: -abs(s["rate"]))
    steps = [("Mix effect", d["mix"], None, f"Attempts moving between {by}s")]
    for s in segs[:6]:
        e = s["ci"] and s["ci"] * (s["share_before"] + s["share_after"]) / 2  # the interval, scaled like the effect
        steps.append((f"{s['segment']} rate effect", s["rate"], e, f"Success rate within {s['segment']}: "
                      f"{s['rate_before'] * 100:.2f}% in {w0}, {s['rate_after'] * 100:.2f}% in {w1}"))
    if segs[6:]:
        steps.append((f"{len(segs) - 6} other {by}s", sum(s["rate"] for s in segs[6:]), None, "The smaller rate effects together"))
    walk = [0.0]
    for _, v, e, _ in steps:
        walk.append(walk[-1] + v)
    lo, hi = min(walk), max(walk)
    pad = (hi - lo or 1e-4) * .08
    lo, hi = lo - pad, hi + pad

    def at(x):
        return f"{max(0.0, min(100.0, (x - lo) / (hi - lo) * 100)):.2f}%"

    def line(name, a, b, value, tip, cls="", e=None):
        left, right = sorted((a, b))
        track = f'<i class="w0" style="left:{at(0)}"></i>'
        if a != b:
            track += f'<i class="wb {cls}" style="left:{at(left)};width:calc({at(right)} - {at(left)} + 2px)"></i>'
        if e:
            track += f'<i class="wk" style="left:{at(b - e)};width:calc({at(b + e)} - {at(b - e)})"></i>'
        return ln(f'<span>{escape(name)}</span><span class="wt" title="{escape(tip)}">{track}</span>'
                  f"<span>{value}</span>", "w")

    out = [row(f"How the {by} explains the change", "Percentage points"), BLANK,
           line(f"{w0} Success rate", 0, 0, f"{start * 100:.2f}%", "Where the walk starts")]
    for (name, v, e, tip), a in zip(steps, walk):
        noise = e is not None and abs(v) <= e
        value = f"{v * 100:+.2f}" + (f" ± {e * 100:.2f}" if e else "")
        out.append(line(name, a, a + v, value, tip + (". Within its 95% interval: could be noise" if noise else ""),
                        ("down" if v < 0 else "") + (" noise" if noise else ""), e))
    out.append(line(f"{w1} Success rate", 0, d["total"], f"{end * 100:.2f}%",
                    f"Net change {d['total'] * 100:+.2f} percentage points", "tot"))
    return out


generator.ensure(generator.DB_PATH)
try:
    os.environ.setdefault("OPENROUTER_API_KEY", st.secrets["OPENROUTER_API_KEY"])
except (KeyError, FileNotFoundError):  # no key: the app still starts, questions show why
    pass

with st.sidebar:
    doc(ln(label("Signed in as")), BLANK)
    role = ANALYST  # auth is mocked: the viewer picks a role (D15)
    if st.selectbox("Role", ["Analyst", "Merchant manager"], label_visibility="collapsed") == "Merchant manager":
        role = Role("Merchant manager", st.selectbox("Category", generator.CATEGORIES))
    st.caption("A Merchant manager sees only their category; the SQL validator enforces it.")
    st.divider()
    doc(ln(label("Quality check")), BLANK)
    run_eval = st.button("Run eval", width="stretch")
    st.caption("Grades 10 known-answer questions on the free model.")

garden.mount(night=role.name == "Merchant manager")
doc(ln("Pine Labs"), ln("Payments analytics"), ln(f"{len(WEEKS)} Weeks of payment Attempts, Week {WEEKS[0]} to Week {WEEKS[-1]}"),
    BLANK, ln('<span class="inv">AI Business Analyst: ask about Success rate, GMV or Settlements</span>'), BLANK,
    lines("Every number below comes from SQL that ran on the data. Anything a model wrote is labelled as such."),
    BLANK)

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

    if not answer.narrated:
        writer = "the pipeline, as the free model was unavailable"
    doc(BLANK, RULE, BLANK, row(label("Answer"), f"headline by {writer}"),
        BLANK, lines(answer.headline), BLANK)
    chips = st.container(horizontal=True, gap="small")
    if "weeks" in answer.assumptions:
        weeks = answer.assumptions["weeks"]
        with chips.popover("Window: " + " vs ".join(f"Week {w}" for w in weeks)):
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
        doc(BLANK, ln(label("Exhibit A: result of model-written SQL")), BLANK, row(f"Tables: {escape(', '.join(answer.result['tables']))}"), BLANK)
        st.dataframe(answer.result["rows"], hide_index=True)
        st.code(answer.result["sql"], language="sql")
    else:
        d = answer.decomposition  # empty for a by-category answer (GMV, Settlement gap)
        if d:
            by = escape(d["dimension"].replace("_", " "))
            w0, w1 = spell(answer.facts[0].window).split(" vs ")
            top = {k: max(s[k + w] for s in d["segments"] for w in ("_before", "_after")) for k in ("share", "rate")}

            def cell(s, key, after):
                v = s[key + ("_after" if after else "_before")]
                return f'<span class="{"" if after else "dim"}">{bar(v, top[key], after, 230)}{v * 100:.1f}</span>'

            rates = [f.value for f in answer.facts if f.unit == "%"]
            band = [ln(label("Exhibit A: why it moved")), BLANK, *bridge(d, rates[0], rates[-1], by, w0, w1), BLANK,
                    lines(f"Read it top to bottom: the walk starts at the {w0} Success rate and adds each effect in turn "
                          f"to reach {w1}. The Mix effect is Attempts moving between {by}s; a rate effect is the Success "
                          f"rate changing within one {by}. The ± is the 95% interval of that change. A faded bar sits "
                          "inside its interval, so it could be noise."), BLANK,
                    row(f"The data behind it, by {by}", f'{bar(1, 1, False, 18)}{w0}  {bar(1, 1, True, 18)}{w1}'), BLANK,
                    ln("<span></span><span>Share of Attempts, %</span><span>Success rate, %</span>", "g")]
            for s in d["segments"]:
                band += [ln(f"<span>{escape(s['segment'])}</span>{cell(s, 'share', False)}{cell(s, 'rate', False)}", "g"),
                         ln(f"<span></span>{cell(s, 'share', True)}{cell(s, 'rate', True)}", "g")]
            band += [BLANK, lines(f"Mix effect {d['mix'] * 100:+.2f} plus Rate effect {d['rate'] * 100:+.2f} equals the "
                                  f"total change of {d['total'] * 100:+.2f} percentage points. The midpoint method "
                                  "splits the change exactly, with nothing left over.")]
        else:
            gmv = "gmv" in answer.chart[0]
            values = [c["gmv" if gmv else "gap"] * (1 if gmv else 100) for c in answer.chart]
            hi = max(range(len(values)), key=lambda i: abs(values[i]))  # the bar the headline names
            peak = abs(values[hi])
            band = [ln(label("Exhibit A: by category")), BLANK,
                    row("GMV, successful Attempts, Duplicates removed" if gmv
                        else "Settlement gap, % of successful Attempt value", escape(spell(answer.facts[0].window))), BLANK]
            for i, (c, v) in enumerate(zip(answer.chart, values)):
                band.append(ln(f"<span>{escape(c['segment'])}</span><span class=\"{'' if i == hi else 'dim'}\">"
                               f"{bar(v, peak, i == hi, 420)}{f'₹{v:,.0f}' if gmv else f'{v:+.2f}%'}</span>", "g1"))
        doc(*band, cls="band")

        facts = "".join(
            f'<details><summary class="ln row"><span>{escape(spell(f.label))}</span>'
            f'<span>{spell(f"{f.value * 100:+.2f}pp") if f.unit == "pp" else escape(shown(f))}</span></summary>'
            f"<pre>{escape(f.sql)}</pre>{ln('Tables: ' + escape(', '.join(f.tables)))}"
            f"{ln('Filters: ' + escape(', '.join(f.filters) or 'none'))}{ln('Window: ' + escape(spell(f.window)))}</details>"
            for f in answer.facts)
        doc(BLANK, row(label("Facts"), "Click a fact to see the SQL behind it"), BLANK, facts, BLANK)

    narration = [(t, i) for t, i in (("Hypotheses", answer.hypotheses), ("Recommendations", answer.recommendations)) if i]
    if narration:
        parts = [RULE, BLANK]
        for title, items in narration:
            parts += [row(label(title), f"written by {writer}"), BLANK,
                      *(lines(item, f"{n}. ", "   ") for n, item in enumerate(items, 1)), BLANK]
        parts.append(lines("These are not evidence. Check each one against the Facts above."))
        doc(*parts)

    level, _, why = answer.dq["confidence"].partition(": ")
    lit = {"High": 3, "Medium": 2}.get(level, 1)
    doc(RULE, BLANK, row(label("Caveats"),
                         f'{escape(level)} confidence <span class="meter">{"■" * lit}{"□" * (3 - lit)}</span>'),
        BLANK, lines(why), *(lines(c, "- ", "  ") for c in answer.dq["caveats"]))
