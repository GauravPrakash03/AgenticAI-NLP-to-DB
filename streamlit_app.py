import ast
import sys
from pathlib import Path

import streamlit as st
from langchain_core.messages import HumanMessage
from Models.schema import DataAgentSchema


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
def load_sql_agent():
    from agents.sql_analyst import sql_agent_graph

    return sql_agent_graph.compile()


@st.cache_resource(show_spinner=False)
def load_etl_agent():
    from agents.etl_analyst import etl_analyst

    return etl_analyst


@st.cache_resource(show_spinner=False)
def load_router_agent():
    from agents.data_agent import data_agent

    return data_agent


def make_sql_input(question: str) -> dict[str, object]:
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


DATA_FILE_EXTENSIONS = {
    ".csv": "text/csv",
    ".json": "application/json",
    ".jsonl": "application/json",
    ".parquet": "application/octet-stream",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".feather": "application/octet-stream",
}
IGNORED_DIRECTORIES = {".git", ".venv", "__pycache__", ".pytest_cache"}


def find_data_files() -> list[Path]:
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in DATA_FILE_EXTENSIONS:
            continue
        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)


def render_downloadable_files() -> None:
    data_files = find_data_files()
    st.markdown('<div class="section-label">Generated data files</div>', unsafe_allow_html=True)
    if not data_files:
        st.caption("No generated data files found in the workspace yet.")
        return

    st.caption("Files created by the backend are available here for download.")
    for index, path in enumerate(data_files):
        relative_path = path.relative_to(ROOT).as_posix()
        size_kb = max(path.stat().st_size / 1024, 0.1)
        with open(path, "rb") as data_file:
            file_bytes = data_file.read()
        st.download_button(
            f"Download {relative_path} ({size_kb:.1f} KB)",
            data=file_bytes,
            file_name=path.name,
            mime=DATA_FILE_EXTENSIONS[path.suffix.lower()],
            key=f"download_{index}_{relative_path}",
            use_container_width=True,
        )


def render_sql_result(result: dict[str, object], question: str = "") -> None:
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
    render_downloadable_files()


def message_text(message: object) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part if isinstance(part, str) else str(part.get("text", part))
            for part in content
        )
    return str(content)


def render_etl_result(result: dict[str, object], question: str = "") -> None:
    messages = result.get("messages", [])
    final_message = message_text(messages[-1]) if messages else "No ETL response returned."

    st.markdown('<div class="section-label">ETL response</div>', unsafe_allow_html=True)
    st.markdown('<div class="answer-box">', unsafe_allow_html=True)
    st.markdown(final_message)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Agent trace", expanded=False):
        for index, message in enumerate(messages, start=1):
            st.markdown(f"**Step {index}**")
            st.code(message_text(message))
    render_downloadable_files()


def render_router_result(result: dict[str, object], question: str = "") -> None:
    messages = result.get("messages", [])
    route = str(result.get("route_response") or "unknown").upper()
    final_message = message_text(messages[-1]) if messages else "No routed response returned."

    st.markdown('<div class="section-label">Routed response</div>', unsafe_allow_html=True)
    route_columns = st.columns(2)
    with route_columns[0]:
        st.metric("Selected agent", route)
    with route_columns[1]:
        st.metric("Pipeline complete", "Yes" if messages else "No")

    st.markdown('<div class="answer-box">', unsafe_allow_html=True)
    st.markdown(str(result.get("final_answer") or final_message))
    st.markdown('</div>', unsafe_allow_html=True)

    if route == "SQL":
        render_sql_result(result, question)
    else:
        render_etl_result(result, question)

    with st.expander("Router trace", expanded=False):
        for index, message in enumerate(messages, start=1):
            st.markdown(f"**Step {index}**")
            st.code(message_text(message))


with st.sidebar:
    st.markdown("## DATA AGENT")
    st.caption("Natural-language questions over your PostgreSQL data.")
    st.markdown("---")
    st.markdown("**Capabilities**")
    st.caption("Automatic routing, SQL analysis, and API-based ETL workflows")
    st.markdown("---")
    st.caption("Backend: existing LangGraph agent")
    st.caption("Frontend: Streamlit")


st.markdown('<div class="eyebrow">PostgreSQL / conversational analytics</div>', unsafe_allow_html=True)
st.title("Ask your data\nplainly.")
st.markdown(
    '<div class="lede">Turn a question into a reviewed SQL query and a readable answer. The agent keeps the database work visible, so every result has a trail.</div>',
    unsafe_allow_html=True,
)

mode = st.radio(
    "Workflow",
    ["Auto Router", "SQL Analyst", "ETL Analyst"],
    horizontal=True,
)

if mode == "Auto Router":
    with st.form("router_question_form"):
        question = st.text_area(
            "Your request",
            placeholder="Ask a database question or describe an ETL task.",
            height=120,
        )
        submitted = st.form_submit_button("Route and run", type="primary")

    if submitted:
        question = question.strip()
        if not question:
            st.warning("Enter a request before running the agent.")
        else:
            try:
                with st.status("Routing request and running the selected agent...", expanded=False) as status:
                    result = load_router_agent().invoke(
                        DataAgentSchema(
                            messages=[HumanMessage(content=question)],
                            route_response="",
                        )
                    )
                    status.update(label="Routed workflow complete", state="complete")
                st.session_state["last_result"] = result
                st.session_state["last_mode"] = mode
                st.session_state["last_question"] = question
            except Exception as error:
                st.error("The routed backend could not complete this request.")
                st.exception(error)

elif mode == "SQL Analyst":
    with st.form("sql_question_form"):
        question = st.text_area(
            "Your question",
            placeholder="Which payment methods are used most often?",
            height=120,
        )
        submitted = st.form_submit_button("Run SQL analysis", type="primary")

    if submitted:
        question = question.strip()
        if not question:
            st.warning("Enter a question before running the analysis.")
        else:
            try:
                with st.status("Running the SQL analyst...", expanded=False) as status:
                    result = load_sql_agent().invoke(make_sql_input(question))
                    status.update(label="SQL analysis complete", state="complete")
                st.session_state["last_result"] = result
                st.session_state["last_mode"] = mode
                st.session_state["last_question"] = question
            except Exception as error:
                st.error("The SQL backend could not complete this request.")
                st.exception(error)
else:
    with st.form("etl_question_form"):
        api_url = st.text_input("API endpoint", placeholder="https://pokeapi.co/api/v2/pokemon/")
        etl_columns = st.columns(3)
        with etl_columns[0]:
            output_folder = st.text_input("Output folder", value="data/extract")
        with etl_columns[1]:
            output_format = st.selectbox("Output format", ["csv", "json", "parquet"])
        with etl_columns[2]:
            transform_folder = st.text_input("Transform folder", value="data/transform")
        transform_request = st.text_area(
            "Transformation request (optional)",
            placeholder="Filter records and save the transformed result.",
            height=90,
        )
        submitted = st.form_submit_button("Run ETL workflow", type="primary")

    if submitted:
        if not api_url.strip():
            st.warning("Enter an API endpoint before running the ETL workflow.")
        else:
            transform_text = transform_request.strip() or "Keep the extracted data unchanged."
            question = (
                f"Extract data from the API endpoint '{api_url.strip()}' and save it to "
                f"{output_folder.strip()} in {output_format} format. Then transform the "
                f"data and save it to {transform_folder.strip()}. {transform_text}"
            )
            try:
                with st.status("Running the ETL analyst...", expanded=False) as status:
                    result = load_etl_agent().invoke(
                        {"messages": [HumanMessage(content=question)]}
                    )
                    status.update(label="ETL workflow complete", state="complete")
                st.session_state["last_result"] = result
                st.session_state["last_mode"] = mode
                st.session_state["last_question"] = question
            except Exception as error:
                st.error("The ETL backend could not complete this request.")
                st.exception(error)


if "last_result" in st.session_state:
    st.caption(
        f'{st.session_state["last_mode"]} · {st.session_state["last_question"]}'
    )
    if st.session_state["last_mode"] == "Auto Router":
        render_router_result(
            st.session_state["last_result"],
            st.session_state["last_question"],
        )
    elif st.session_state["last_mode"] == "SQL Analyst":
        render_sql_result(
            st.session_state["last_result"],
            st.session_state["last_question"],
        )
    else:
        render_etl_result(
            st.session_state["last_result"],
            st.session_state["last_question"],
        )