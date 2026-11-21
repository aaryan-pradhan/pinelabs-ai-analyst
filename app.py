import os

import pandas as pd
import plotly.express as px
import streamlit as st

import generator
import llm
from analyst import AskBack, ask


st.set_page_config(page_title="AI Business Analyst")
st.title("AI Business Analyst")
generator.ensure(generator.DB_PATH)
try:
    os.environ.setdefault("OPENROUTER_API_KEY", st.secrets["OPENROUTER_API_KEY"])
except (KeyError, FileNotFoundError):  # no key: the app still starts, questions show why
    pass

question = st.text_input("Ask a question", "Why did success rate drop in week 6?")
if st.session_state.get("asked") != question:  # a new question drops the edited window
    st.session_state.asked, st.session_state.weeks = question, None
if question:
    try:
        answer = ask(question, "analyst", llm.complete, weeks=st.session_state.weeks)
    except AskBack as e:
        st.info(str(e))
        st.stop()
    except llm.ModelUnavailable as e:
        st.warning(str(e))
        st.caption("SQL for this question:")
        for sql in e.sql:
            st.code(sql, language="sql")
        st.stop()
    st.subheader(answer.headline)
    st.caption("Headline written by a free model; only the numbers in Facts come from executed SQL.")

    chips = st.columns(len(answer.assumptions) or 1)
    if "weeks" in answer.assumptions:
        weeks = answer.assumptions["weeks"]
        with chips[0].popover("Window: " + " vs ".join(f"wk{w}" for w in weeks)):
            # A comparison is always the chosen Week against the one before it.
            current = st.selectbox("Week", range(len(weeks), 9), index=weeks[-1] - len(weeks))
            if st.button("Re-run"):
                st.session_state.weeks = list(range(current - len(weeks) + 1, current + 1))
                st.rerun()
    if "denominator" in answer.assumptions:
        with chips[-1].popover(f"Denominator: {answer.assumptions['denominator']}"):
            st.caption("The only Success rate denominator the semantic layer defines (D19).")

    d = answer.decomposition  # empty for a Settlement gap answer
    unit = "pp" if d else "%"
    chart = pd.DataFrame(answer.chart).melt(id_vars="segment", var_name="effect", value_name=unit)
    chart[unit] *= 100
    title = (f"Mix vs rate effect by {d['dimension'].replace('_', ' ')} "
             f"(total {d['total'] * 100:+.2f}pp = mix {d['mix'] * 100:+.2f}pp "
             f"+ rate {d['rate'] * 100:+.2f}pp)" if d
             else "Settlement gap by category (% of successful Attempt value)")
    st.plotly_chart(px.bar(chart, x="segment", y=unit, color="effect", barmode="group", title=title))

    st.markdown("### Facts")
    for fact in answer.facts:
        value = f"{fact.value * 100:.2f}%" if fact.unit == "%" else f"{fact.value * 100:+.2f}pp"
        st.markdown(f"**{fact.label}:** {value}")
        with st.expander("SQL, tables, filters, window"):
            st.code(fact.sql, language="sql")
            st.markdown(f"Tables: {', '.join(fact.tables)}  \n"
                        f"Filters: {', '.join(fact.filters) or 'none'}  \n"
                        f"Window: {fact.window}")

    for title, items in (("Hypotheses", answer.hypotheses), ("Recommendations", answer.recommendations)):
        st.markdown(f"### {title}")
        st.caption("Model narration from a free model, not evidence. Check against the Facts above.")
        for item in items:
            st.markdown(f"- {item}")

    st.markdown("### Caveats")
    st.markdown(f"**Confidence:** {answer.dq['confidence']}")
    for line in answer.dq["caveats"]:
        st.markdown(f"- {line}")
