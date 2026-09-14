import ast
import sys
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


st.set_page_config(
    page_title="Data Agent",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --ink: #17211b; --muted: #6c776f; --paper: #f4f5ef; --line: #d9ded5; --accent: #d5683d; --mint: #dce9dd; }
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stSidebar"] { background: #1d2b24; border-right: 0; }
    [data-testid="stSidebar"] * { color: #edf2e9; }
    [data-testid="stSidebar"] .stCaption { color: #aab8ad; }
    .eyebrow { color: var(--accent); font: 700 0.72rem 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; margin-bottom: .7rem; }
    h1 { font-size: clamp(2.5rem, 5vw, 4.8rem) !important; line-height: .98 !important; letter-spacing: -.06em; margin: 0 0 1rem !important; max-width: 760px; }
    .lede { color: var(--muted); font-size: 1.06rem; max-width: 650px; line-height: 1.7; margin-bottom: 2.1rem; }
    .section-label { color: var(--muted); font: 500 .72rem 'DM Mono', monospace; text-transform: uppercase; letter-spacing: .08em; margin: 1.6rem 0 .65rem; }
    .answer-box { background: var(--mint); border-left: 4px solid var(--accent); padding: 1.2rem 1.35rem; line-height: 1.7; font-size: 1.06rem; }
    .status-pill { display: inline-block; font: 500 .72rem 'DM Mono', monospace; padding: .35rem .6rem; border: 1px solid var(--line); border-radius: 99px; color: var(--muted); }
    code, pre, .stCode { font-family: 'DM Mono', monospace !important; }
    .stButton > button { border-radius: 3px; font-weight: 700; padding: .65rem 1.2rem; }
    .stTextArea textarea { border: 1px solid var(--line); border-radius: 3px; background: #fbfcf8; font-size: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def load_agent():
    from agents.sql_analyst import sql_agent_graph

    return sql_agent_graph.compile()


def make_input(question: str) -> dict[str, object]:
    return {
        "messages": [],
        "user_question": question,
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": "",
    }


def render_result(result: dict[str, object]) -> None:
    st.markdown('<div class="section-label">Response</div>', unsafe_allow_html=True)
    final_answer = result.get("final_answer") or "The agent did not return a final answer."
    st.markdown('<div class="answer-box">', unsafe_allow_html=True)
    st.markdown(str(final_answer))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">Run details</div>', unsafe_allow_html=True)
    detail_columns = st.columns(3)
    with detail_columns[0]:
        st.metric("Safety", str(result.get("is_safe", "Unknown")))
    with detail_columns[1]:
        st.metric("Query generated", "Yes" if result.get("generated_sql_query") else "No")
    with detail_columns[2]:
        st.metric("Data returned", "Yes" if result.get("sql_query_execution_result") else "No")

    with st.expander("Generated SQL", expanded=True):
        st.code(str(result.get("generated_sql_query") or "No SQL was generated."), language="sql")
    with st.expander("Execution result"):
        raw_result = result.get("sql_query_execution_result")
        try:
            st.dataframe(ast.literal_eval(str(raw_result)), use_container_width=True)
        except (SyntaxError, ValueError, TypeError):
            st.code(str(raw_result or "No execution result."))
    with st.expander("Safety review"):
        st.write(result.get("comments") or "No safety comments returned.")
    with st.expander("Curated question"):
        st.write(result.get("curated_ques") or "No curated question returned.")


with st.sidebar:
    st.markdown("## DATA AGENT")
    st.caption("Natural-language questions over your PostgreSQL data.")
    st.markdown("---")
    st.markdown("**Pipeline**")
    st.caption("Curate question  →  Generate SQL  →  Safety review  →  Execute  →  Explain")
    st.markdown("---")
    st.caption("Backend: existing LangGraph agent")
    st.caption("Frontend: Streamlit")


st.markdown('<div class="eyebrow">PostgreSQL / conversational analytics</div>', unsafe_allow_html=True)
st.title("Ask your data\nplainly.")
st.markdown(
    '<div class="lede">Turn a question into a reviewed SQL query and a readable answer. The agent keeps the database work visible, so every result has a trail.</div>',
    unsafe_allow_html=True,
)

with st.form("question_form"):
    question = st.text_area(
        "Your question",
        placeholder="Which payment methods are used most often?",
        height=120,
        label_visibility="visible",
    )
    submitted = st.form_submit_button("Run analysis", type="primary", use_container_width=False)

if submitted:
    question = question.strip()
    if not question:
        st.warning("Enter a question before running the analysis.")
    else:
        try:
            with st.status("Working through the data agent...", expanded=False) as status:
                agent = load_agent()
                result = agent.invoke(make_input(question))
                status.update(label="Analysis complete", state="complete")
            st.session_state["last_result"] = result
            st.session_state["last_question"] = question
        except Exception as error:
            st.error("The backend could not complete this request.")
            st.exception(error)

if "last_result" in st.session_state:
    st.caption(f'Last question: {st.session_state["last_question"]}')
    render_result(st.session_state["last_result"])