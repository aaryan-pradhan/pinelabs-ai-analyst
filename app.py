import json

import pandas as pd
import plotly.express as px
import streamlit as st

import generator
from analyst import ask

# ponytail: fixed wk6 plan stands in for the model until the live LLM ticket.
WK6_PLAN = {"metric": "success_rate", "dimensions": ["payment_method"], "weeks": [5, 6]}


def fake_llm(prompt):
    return json.dumps(WK6_PLAN)


st.set_page_config(page_title="AI Business Analyst")
st.title("AI Business Analyst")
generator.ensure(generator.DB_PATH)

question = st.text_input("Ask a question", "Why did success rate drop in week 6?")
if question:
    answer = ask(question, "analyst", fake_llm)
    st.subheader(answer.headline)

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
