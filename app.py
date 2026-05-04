import streamlit as st
import os
from agent import run_agent

st.set_page_config(
    page_title="Pipeline Failure Agent",
    page_icon="🔍",
    layout="wide"
)

st.title("Pipeline Failure Diagnosis Agent")
st.caption("Paste a pipeline error log — the AI agent will find the root cause and give you a fix.")

SAMPLES = {
    "Schema change error": "2024-01-15 03:22:11 ERROR pipeline: user_events | Task failed: Column 'user_id' expected INT but got VARCHAR. Schema mismatch in source table. Records processed: 0",
    "Timeout error": "2024-01-15 07:45:02 ERROR pipeline: sales_sync | Connection timed out after 30s. Source API not responding. Retry 3/3 failed. Task aborted.",
    "Null values error": "2024-01-15 09:10:55 ERROR pipeline: crm_import | Null constraint violation on column 'email'. Found 1243 null values in batch. Pipeline halted.",
    "Memory error": "2024-01-15 11:30:44 ERROR pipeline: events_aggregator | java.lang.OutOfMemoryError: GC overhead limit exceeded. Executor memory: 4g. Dataset size: 48GB",
    "Permissions error": "2024-01-15 14:05:23 ERROR pipeline: s3_loader | Access Denied: Service account lacks permission to read s3://prod-bucket/data/. Check IAM policy.",
    "Duplicate data error": "2024-01-15 16:22:09 ERROR pipeline: orders_pipeline | Unique constraint violation on primary key 'order_id'. Duplicate records detected in staging table."
}

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "Groq API Key (free)",
        type="password",
        placeholder="gsk_...",
        help="Get your free key from console.groq.com"
    )
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
        st.success("API key set!")

    st.divider()
    st.header("Sample Logs")
    st.caption("Click any sample to load it")
    for name, log in SAMPLES.items():
        if st.button(name, use_container_width=True):
            st.session_state.log_input = log

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("Input")
    log_text = st.text_area(
        "Paste your error log here",
        value=st.session_state.get("log_input", ""),
        height=200,
        placeholder="Paste any pipeline error log here..."
    )

    ready = log_text and os.environ.get("GROQ_API_KEY")
    run_btn = st.button(
        "Diagnose with AI Agent",
        type="primary",
        use_container_width=True,
        disabled=not ready
    )

    if not os.environ.get("GROQ_API_KEY"):
        st.warning("Add your free Groq API key in the sidebar to run the agent.")

with col2:
    st.subheader("Agent Reasoning")

    if run_btn and log_text:
        result_data = None
        for step in run_agent(log_text):
            if step["title"] == "DONE":
                result_data = step["result"]
            else:
                with st.status(step["title"], state="complete"):
                    st.markdown(step["content"])

        if result_data:
            st.divider()
            st.subheader("Diagnosis Report")
            m1, m2 = st.columns(2)
            m1.metric("Error Type", result_data["error_type"].replace("_", " ").title())
            m2.metric("Confidence", f"{result_data['confidence']}%")
            st.markdown("**Root Cause**")
            st.info(result_data["root_cause"])
            st.markdown("**Upstream Finding**")
            st.warning(result_data["upstream"])
            st.markdown("**Recommended Fix**")
            st.success(result_data["fix_summary"])
            st.markdown("**Code Fix**")
            st.code(result_data["code"], language="python")
            st.markdown("**Prevention**")
            st.markdown(f"> {result_data['prevention']}")
    else:
        st.info("Select a sample log from the sidebar or paste your own, then click Diagnose.")