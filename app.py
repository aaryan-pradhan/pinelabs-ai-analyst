import json
import os
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import evaluate
import generator
import llm
from analyst import WEEKS, AskBack, ask, shown
from validator import ANALYST, Rejected, Role

ACCENT, MUTED, GRID, INK = "#ffc400", "#484f58", "#21262d", "#8b949e"  # D36 palette, as in config.toml
MONO = "IBM Plex Mono, ui-monospace, monospace"

st.set_page_config(page_title="AI Business Analyst", layout="wide")
st.html("""<style>
.block-container {max-width: 1180px; padding: 3rem 3rem 6rem}
.sw {display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin: 0 .3rem 0 .9rem}
header[data-testid="stHeader"] {background: transparent}
.lbl {font-family: 'IBM Plex Mono', monospace; font-size: .72rem; letter-spacing: .08em;
      text-transform: uppercase; color: #8b949e; margin: 0 0 .35rem}
.lbl b {color: #ffc400; font-weight: 500}
.lead {color: #8b949e; margin: -.4rem 0 1.4rem; max-width: 60ch}
.headline {font-size: 1.65rem; line-height: 1.3; font-weight: 500; letter-spacing: -.01em;
           color: #e6edf3; margin: .1rem 0 .2rem; max-width: 46ch}
.tag {display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: .7rem; color: #8b949e;
      border: 1px solid #30363d; border-radius: 4px; padding: .05rem .4rem; margin-left: .5rem;
      text-transform: none; letter-spacing: 0}
.meter {display: inline-flex; gap: 3px; margin-right: .6rem; vertical-align: middle}
.meter i {width: 14px; height: 6px; border-radius: 1px; background: #30363d}
.meter i.on {background: #ffc400}
[data-testid="stTextInput"] input {font-size: 1.05rem; padding: .85rem 1rem}
[data-testid="stMetricValue"] {font-family: 'IBM Plex Mono', monospace; font-size: 1.5rem}
[data-testid="stMetricLabel"] p {font-family: 'IBM Plex Mono', monospace; font-size: .75rem; color: #8b949e}
[data-testid="stPopover"] button p, [data-testid="stExpander"] summary p {font-family: 'IBM Plex Mono', monospace;
      font-size: .78rem}
[data-testid="stCaptionContainer"] {font-family: 'IBM Plex Mono', monospace; font-size: .75rem}
</style>""")


def label(text, tag=""):
    st.html(f'<p class="lbl">{text}{f"<span class=tag>{tag}</span>" if tag else ""}</p>')


def styled(fig, title, height=300):
    fig.update_layout(
        title={"text": title, "font": {"family": MONO, "size": 12, "color": INK}, "x": 0, "y": .97},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=height,
        font={"family": MONO, "size": 11, "color": INK}, margin={"l": 0, "r": 0, "t": 36, "b": 0},
        bargap=.35, bargroupgap=.08, hoverlabel={"font": {"family": MONO}}, showlegend=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, showticklabels=False, showline=False)  # bars carry labels
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont={"color": "#c9d1d9"}, automargin=True)
    return fig


def plot(fig):
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})


def week_bars(segments, key, weeks, title):
    """One panel: a Segment value in the base Week (muted) against the current one (accent)."""
    fig = go.Figure()
    for week, color, suffix in ((weeks[0], MUTED, "_before"), (weeks[1], ACCENT, "_after")):
        fig.add_bar(name=week, x=[s["segment"] for s in segments], y=[s[key + suffix] * 100 for s in segments],
                    marker={"color": color}, texttemplate="%{y:.1f}", textposition="outside",
                    hovertemplate="%{x} " + week + ": %{y:.2f}%<extra></extra>",
                    textfont={"color": INK, "size": 10}, cliponaxis=False)
    return styled(fig, title)


generator.ensure(generator.DB_PATH)
try:
    os.environ.setdefault("OPENROUTER_API_KEY", st.secrets["OPENROUTER_API_KEY"])
except (KeyError, FileNotFoundError):  # no key: the app still starts, questions show why
    pass

with st.sidebar:
    label("Signed in as")
    role = ANALYST  # auth is mocked: the viewer picks a role (D15)
    if st.selectbox("Role", ["Analyst", "Merchant manager"], label_visibility="collapsed") == "Merchant manager":
        role = Role("Merchant manager", st.selectbox("Category", generator.CATEGORIES))
    st.caption("A Merchant manager sees only their category; the SQL validator enforces it.")
    st.divider()
    label("Quality check")
    run_eval = st.button("Run eval", use_container_width=True)
    st.caption("Grades 10 known-answer questions on the free model.")

label("Pine Labs · Payments · wk1 – wk8")
st.title("AI Business Analyst")
st.html('<p class="lead">Ask about Success rate, GMV or Settlements. Every number below comes from SQL '
        "that ran on 8 weeks of payment Attempts; anything a model wrote is labelled.</p>")

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
        st.info("Replay mode: the free model is unavailable (no key or rate-limited), so this demo "
                "question replays a cached model reply. Numbers, SQL and charts still come from "
                "running the pipeline; any cached headline, Hypotheses and Recommendations were "
                "written with Claude Code during development.")
    if isinstance(answer, Rejected):
        st.error(str(answer))
        for sql in answer.sql:
            st.code(sql, language="sql")
        st.stop()
    if isinstance(answer, AskBack):
        st.info(str(answer))
        st.stop()
    if isinstance(answer, llm.ModelUnavailable):
        st.warning(str(answer))
        st.caption("SQL for this question:")
        for sql in answer.sql:
            st.code(sql, language="sql")
        st.stop()
    writer = "Claude Code during development" if replayed else "a free model"

    with st.container(border=True):
        label("Answer", "" if answer.result else f"headline written by {writer}")
        st.html(f'<p class="headline">{escape(answer.headline)}</p>')
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
            with chips.popover("Denominator: all Attempts excl. Duplicates"):
                st.caption(f"{answer.assumptions['denominator']}: the only Success rate denominator "
                           "the semantic layer defines (D19).")

    if answer.result:  # an ad-hoc question: the rows its model-written SQL returned
        with st.container(border=True):
            label("Result", "model-written SQL")
            st.dataframe(answer.result["rows"], hide_index=True)
            st.code(answer.result["sql"], language="sql")
            st.caption(f"Tables: {', '.join(answer.result['tables'])}")
    else:
        d = answer.decomposition  # empty for a by-category answer (GMV, Settlement gap)
        with st.container(border=True):
            if d:
                by = d["dimension"].replace("_", " ")
                weeks = answer.facts[0].window.split(" vs ")
                st.html(f'<p class="lbl">Why it moved · by {by}<span class="sw" style="background:{MUTED}"></span>'
                        f'{weeks[0]}<span class="sw" style="background:{ACCENT}"></span>{weeks[1]}</p>')
                left, right = st.columns(2, gap="large")
                with left:
                    plot(week_bars(d["segments"], "share", weeks, f"Traffic share by {by} (%)"))
                with right:
                    plot(week_bars(d["segments"], "rate", weeks, f"Success rate by {by} (%)"))
                st.caption(f"Total {d['total'] * 100:+.2f}pp = mix {d['mix'] * 100:+.2f}pp (traffic moving "
                           f"between {by}s) + rate {d['rate'] * 100:+.2f}pp (rates changing within them).")
            else:
                gmv = "gmv" in answer.chart[0]
                key = "gmv" if gmv else "gap"
                values = [c[key] * (1 if gmv else 100) for c in answer.chart]
                top = max(range(len(values)), key=lambda i: abs(values[i]))  # the bar the headline names
                fig = go.Figure(go.Bar(
                    x=[c["segment"] for c in answer.chart], y=values, showlegend=False, cliponaxis=False,
                    marker={"color": [ACCENT if i == top else MUTED for i in range(len(values))]},
                    texttemplate="₹%{y:,.3s}" if gmv else "%{y:+.2f}%", textposition="outside",
                    textfont={"color": INK, "size": 10}))
                label("By category · " + answer.facts[0].window)
                plot(styled(fig, "GMV (successful Attempts, Duplicates removed)" if gmv
                            else "Settlement gap (% of successful Attempt value)"))

        with st.container(border=True):
            label("Facts", "from executed SQL")
            for row in range(0, len(answer.facts), 3):
                for col, fact in zip(st.columns(3, gap="large"), answer.facts[row:row + 3]):
                    with col:
                        st.metric(fact.label, f"{fact.value * 100:+.2f}pp" if fact.unit == "pp" else shown(fact))
                        with st.expander("SQL"):
                            st.code(fact.sql, language="sql")
                            st.caption(f"Tables: {', '.join(fact.tables)}  \n"
                                       f"Filters: {', '.join(fact.filters) or 'none'}  \n"
                                       f"Window: {fact.window}")

    narration = [(t, i) for t, i in (("Hypotheses", answer.hypotheses), ("Recommendations", answer.recommendations)) if i]
    if narration:
        with st.container(border=True):
            label("Model narration", f"written by {writer}, not evidence; check it against the Facts")
            for col, (title, items) in zip(st.columns(len(narration), gap="large"), narration):
                with col:
                    st.markdown(f"**{title}**")
                    st.markdown("\n".join(f"- {item}" for item in items))

    with st.container(border=True):
        level, _, why = answer.dq["confidence"].partition(": ")
        lit = {"High": 3, "Medium": 2}.get(level, 1)
        label("Caveats")
        st.html(f'<p style="margin:0"><span class="meter">{"".join("<i class=on></i>" if i < lit else "<i></i>" for i in range(3))}'
                f'</span><b>{escape(level)} confidence</b> <span style="color:#8b949e">· {escape(why)}</span></p>')
        if answer.dq["caveats"]:
            st.markdown("\n".join(f"- {line}" for line in answer.dq["caveats"]))
