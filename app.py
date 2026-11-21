import os

import pandas as pd
import plotly.express as px
import streamlit as st

import generator
import llm
from analyst import ask


st.set_page_config(page_title="AI Business Analyst")
st.title("AI Business Analyst")
generator.ensure(generator.DB_PATH)
try:
    os.environ.setdefault("OPENROUTER_API_KEY", st.secrets["OPENROUTER_API_KEY"])
except (KeyError, FileNotFoundError):  # no key: the app still starts, questions show why
    pass

question = st.text_input("Ask a question", "Why did success rate drop in week 6?")
if question:
    try:
        answer = ask(question, "analyst", llm.complete)
    except llm.ModelUnavailable as e:
        st.warning(str(e))
        st.caption("SQL for this question:")
        for sql in e.sql:
            st.code(sql, language="sql")
        st.stop()
    st.subheader(answer.headline)
    st.caption("Headline written by a free model; only the numbers in Facts come from executed SQL.")

    d = answer.decomposition
    chart = pd.DataFrame(answer.chart).melt(id_vars="segment", var_name="effect", value_name="pp")
    chart["pp"] *= 100
    st.plotly_chart(px.bar(
        chart, x="segment", y="pp", color="effect", barmode="group",
        title=f"Mix vs rate effect by {d['dimension'].replace('_', ' ')} "
              f"(total {d['total'] * 100:+.2f}pp = mix {d['mix'] * 100:+.2f}pp "
              f"+ rate {d['rate'] * 100:+.2f}pp)",
    ))

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
