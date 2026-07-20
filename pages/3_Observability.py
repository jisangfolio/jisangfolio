import streamlit as st
import pandas as pd
from datetime import datetime
from ui import apply_style
from observability import get_traces, clear_traces

st.set_page_config(page_title="JisangFolio · Observability", page_icon="📈")
apply_style()

with st.sidebar:
    if st.button("← Home", use_container_width=True):
        st.switch_page("jisangfolio.py")
    if st.button("💬 Chat", use_container_width=True):
        st.switch_page("pages/1_Chat.py")
    st.divider()
    if st.button("🗑 Clear traces", use_container_width=True):
        clear_traces()
        st.rerun()

st.title("📈 LLM Observability")
st.caption(
    "Self-hosted-style tracing for every chat / data-analysis turn — latency, model, routing, "
    "and guardrail verdicts. Same idea as Langfuse / Arize Phoenix, built in-house to match my "
    "on-prem, no-external-SaaS approach."
)

traces = get_traces()
if not traces:
    st.info("No traces yet. Ask something on the Chat or Data Analysis page — traces appear here live.")
    st.stop()

df = pd.DataFrame(traces)
df["time"] = df["ts"].apply(lambda t: datetime.fromtimestamp(t).strftime("%H:%M:%S"))
df["nodes_str"] = df["nodes"].apply(lambda n: ", ".join(n) if isinstance(n, list) else "")

# --- Metrics ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Turns", len(df))
c2.metric("Avg latency", f"{int(df['latency_ms'].mean())} ms")
c3.metric("P95 latency", f"{int(df['latency_ms'].quantile(0.95))} ms")
c4.metric("Guardrail blocks", int((df["guard"] != "ok").sum()))

st.divider()

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Routing")
    st.bar_chart(df["route"].value_counts())
with col_b:
    st.subheader("Latency (ms) by turn")
    st.line_chart(df.reset_index()[["latency_ms"]], height=260)

st.subheader("Recent traces")
show = df[["time", "page", "route", "model", "latency_ms", "guard", "nodes_str"]].iloc[::-1].head(50)
show = show.rename(columns={"latency_ms": "latency(ms)", "nodes_str": "graph nodes"})
st.dataframe(show, use_container_width=True, hide_index=True)
