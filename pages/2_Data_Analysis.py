import time
import os
import streamlit as st
import pandas as pd
from langchain_core.messages import ChatMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from prompts import ROUTER_PROMPT_TEMPLATE
from ui import apply_style
# Heavy torch/faiss deps (FAISS · HuggingFaceEmbeddings) are imported lazily,
# only when embedding is actually needed — keeps first render light.

st.set_page_config(page_title="JisangFolio · Data Analysis", page_icon="📂")
apply_style()

try:
    groq_api_key = st.secrets["groq_api_key"]
except KeyError:
    st.error("⚠️ groq_api_key is not set in Secrets.")
    st.stop()

GROQ_MODEL = "qwen/qwen3.6-27b"
SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "..", "tebo_sample.xlsx")
SAMPLE_NAME = "tebo_sample.xlsx"
TEBO_SAMPLE_QUESTIONS = [
    "Compare the average Path_Length by Study",
    "Visualize the record count by Condition",
    "Who are the top 5 by Rambling_Y_LF_Power?",
    "What's the overall mean difference between Rambling and Trembling?",
]

# --- Sidebar ---
with st.sidebar:
    if st.button("← Home"):
        st.switch_page("jisangfolio.py")
    if st.button("💬 Chat"):
        st.switch_page("pages/1_Chat.py")
    st.divider()
    st.header("Upload a file")
    uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])
    if not uploaded_file:
        st.divider()
        st.markdown("**💡 Sample questions (TEBO data)**")
        for q in TEBO_SAMPLE_QUESTIONS:
            if st.button(q, use_container_width=True, key=f"tebo_{q}"):
                st.session_state["data_pending"] = q
                st.rerun()
    st.divider()
    st.caption("This analysis runs on AI-generated code. If the numbers matter, double-check against the source data :)")

# --- File processing ---
@st.cache_resource(show_spinner="Analyzing the uploaded file...")
def build_vectorstore(file_bytes: bytes, file_name: str):
    import io
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    try:
        if file_name.endswith(".csv"):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="cp949")
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
    except Exception as e:
        st.error(f"❌ Failed to read the file: {e}")
        return None, None

    if df.empty:
        st.error("❌ The file has no data.")
        return None, None

    documents = []
    for idx, row in df.iterrows():
        content_parts = [
            f"{col}: {row[col]}"
            for col in df.columns
            if pd.notna(row[col]) and str(row[col]).strip() != ""
        ]
        documents.append(Document(
            page_content="\n".join(content_parts),
            metadata={"row": idx, "source": file_name, "summary_title": str(row[df.columns[0]])[:50]},
        ))

    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100).split_documents(documents)
    if not splits:
        st.error("❌ Could not process the data.")
        return None, None

    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    progress_bar = st.progress(0, text="Building embeddings...")
    vectorstore = None
    batch_size = 10

    for i in range(0, len(splits), batch_size):
        batch = splits[i : i + batch_size]
        for attempt in range(4):
            try:
                if vectorstore is None:
                    vectorstore = FAISS.from_documents(batch, embedding=embedding)
                else:
                    vectorstore.add_documents(batch)
                break
            except Exception as e:
                if attempt == 3:
                    st.error(f"Embedding error: {e}")
                    return None, None
                time.sleep(2 ** attempt)

        percent = min((i + batch_size) / len(splits), 1.0)
        progress_bar.progress(percent, text=f"Building embeddings... ({int(percent * 100)}%)")

    progress_bar.empty()
    st.sidebar.success(f"✅ Indexed records: {vectorstore.index.ntotal}")

    k = max(1, min(10, vectorstore.index.ntotal // 5))
    return df, vectorstore.as_retriever(search_kwargs={"k": k})


def get_df_info(df: pd.DataFrame) -> str:
    """Build a DataFrame summary to pass to the LLM."""
    info_parts = [f"Columns: {list(df.columns)}"]
    info_parts.append(f"Rows: {len(df)}")
    info_parts.append(f"Dtypes:\n{df.dtypes.to_string()}")
    info_parts.append(f"First 3 rows:\n{df.head(3).to_string()}")
    return "\n".join(info_parts)


def classify_question(llm, question: str, df_info: str) -> str:
    """The LLM decides whether to handle the question with pandas (codegen) or RAG search."""
    # The router prompt is shared from prompts.py (SSOT) — the eval harness scores the same prompt.
    prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
    result = (prompt | llm).invoke({"question": question, "df_info": df_info})
    answer = result.content.strip().upper()
    if "PANDAS" in answer:
        return "PANDAS"
    return "RAG"


def generate_and_run_code(llm, question: str, df_info: str, df: pd.DataFrame):
    """The LLM generates pandas code and we run it. Returns the code and the result."""
    prompt = ChatPromptTemplate.from_template(
        """/no_think
Using the DataFrame info below, write Python pandas code that answers the user's question.

[DataFrame info]
{df_info}

[Question]
{question}

[Rules]
1. The variable `df` is already loaded. Do not import anything or read files.
2. Store the final result in a variable named `result`.
3. If a visualization helps, store a chart DataFrame in `chart_df` (index=category, values=numbers). If no chart is needed, don't create `chart_df`.
4. Numeric columns may contain stray text, so use pd.to_numeric(errors='coerce').
5. Output code only — no explanation, no markdown, no code fences (```), just pure Python.
6. Do not use print()."""
    )

    response = (prompt | llm).invoke({"question": question, "df_info": df_info})
    code = response.content.strip()

    # Strip code-fence markers
    if code.startswith("```"):
        lines = code.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        code = "\n".join(lines)

    # Strip <think> block
    if "<think>" in code:
        code = code.split("</think>")[-1].strip()

    # Execute
    local_vars = {"df": df.copy(), "pd": pd}
    try:
        exec(code, {"__builtins__": {"len": len, "sum": sum, "min": min, "max": max, "round": round, "sorted": sorted, "list": list, "dict": dict, "str": str, "int": int, "float": float, "abs": abs, "enumerate": enumerate, "zip": zip, "range": range, "type": type, "isinstance": isinstance, "True": True, "False": False, "None": None, "print": lambda *a, **kw: None}}, local_vars)
        result = local_vars.get("result", "Could not produce a result.")
        chart_df = local_vars.get("chart_df", None)
        return code, result, chart_df, None
    except Exception as e:
        return code, None, None, str(e)


# --- Main ---
st.title("📂 Chat with your file")
st.caption("Upload a CSV or Excel file and the AI analyzes it and answers your questions.")

if "data_messages" not in st.session_state:
    st.session_state["data_messages"] = [
        ChatMessage(role="assistant", content="Upload a CSV or Excel file and I'll analyze it for you.")
    ]
if "current_file" not in st.session_state:
    st.session_state["current_file"] = None
if "data_pending" not in st.session_state:
    st.session_state["data_pending"] = None

if uploaded_file:
    file_bytes = uploaded_file.getvalue()
    df, retriever = build_vectorstore(file_bytes, uploaded_file.name)

    if st.session_state["current_file"] != uploaded_file.name:
        st.session_state["data_messages"] = [
            ChatMessage(role="assistant", content=f"Analyzed '{uploaded_file.name}'. Ask me anything!")
        ]
        st.session_state["current_file"] = uploaded_file.name

    if retriever:
        st.success(f"✅ '{uploaded_file.name}' ready! ({len(df)} records)")

elif os.path.exists(SAMPLE_PATH):
    with open(SAMPLE_PATH, "rb") as f:
        sample_bytes = f.read()
    df, retriever = build_vectorstore(sample_bytes, SAMPLE_NAME)

    if st.session_state["current_file"] != SAMPLE_NAME:
        st.session_state["data_messages"] = [
            ChatMessage(role="assistant", content=(
                "📊 TEBO paper sample data loaded!\n\n"
                "This is the actual output from Jisang's balance-analysis study "
                "published in the SCIE journal Applied Sciences (2025) — "
                "745 CoP Rambling/Trembling records. Click a sample question on the left or ask your own."
            ))
        ]
        st.session_state["current_file"] = SAMPLE_NAME

    if retriever:
        st.info("📊 Sample data: TEBO balance-analysis study (SCIE paper) · 745 records · 23 variables")
else:
    st.info("👈 Upload a CSV or Excel file from the sidebar.")
    df, retriever = None, None

for msg in st.session_state["data_messages"]:
    st.chat_message(msg.role).write(msg.content)

llm = ChatGroq(model=GROQ_MODEL, groq_api_key=groq_api_key, temperature=0)
user_input = st.chat_input("Ask anything about this data")
if not user_input and st.session_state["data_pending"]:
    user_input = st.session_state["data_pending"]
    st.session_state["data_pending"] = None

if user_input and retriever:
    st.chat_message("user").write(user_input)
    st.session_state["data_messages"].append(ChatMessage(role="user", content=user_input))

    df_info = get_df_info(df)
    route = classify_question(llm, user_input, df_info)

    if route == "PANDAS":
        # --- pandas codegen path ---
        with st.chat_message("assistant"):
            with st.spinner("Generating code..."):
                code, result, chart_df, error = generate_and_run_code(llm, user_input, df_info, df)

            # Show generated code
            st.caption("🔧 Generated pandas code")
            st.code(code, language="python")

            if error:
                # Fall back to RAG if code execution fails
                st.warning(f"⚠️ Code failed, switching to RAG search: {error}")
                retrieved_docs = retriever.invoke(user_input)
                context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
                fallback_prompt = ChatPromptTemplate.from_template(
                    """/no_think
You are an AI data analyst that answers based on the uploaded data.
Answer in English only.
Do not make up anything not in the context — say "I can't find that in the data" instead.

[Data context]:
{context}

Question: {question}
Answer:"""
                )
                full_response = ""
                response_container = st.empty()
                in_think = None
                buffer = ""
                for chunk in (fallback_prompt | llm).stream({"question": user_input, "context": context_text}):
                    delta = chunk.content
                    if in_think is None:
                        buffer += delta
                        if "<think>" in buffer:
                            in_think = True
                        elif len(buffer) >= 50:
                            in_think = False
                            full_response = buffer
                            response_container.markdown(full_response)
                    elif in_think:
                        buffer += delta
                        if "</think>" in buffer:
                            full_response = buffer.split("</think>", 1)[1].lstrip("\n")
                            in_think = False
                            response_container.markdown(full_response)
                    else:
                        full_response += delta
                        response_container.markdown(full_response)
                st.session_state["data_messages"].append(ChatMessage(role="assistant", content=full_response))
            else:
                # Show result
                if isinstance(result, pd.DataFrame):
                    st.dataframe(result, use_container_width=True)
                    result_text = f"```\n{result.to_string()}\n```"
                elif isinstance(result, pd.Series):
                    st.dataframe(result.to_frame(), use_container_width=True)
                    result_text = f"```\n{result.to_string()}\n```"
                else:
                    st.markdown(f"**Result:** {result}")
                    result_text = str(result)

                # Show chart
                if chart_df is not None:
                    try:
                        if isinstance(chart_df, pd.DataFrame):
                            st.bar_chart(chart_df)
                        elif isinstance(chart_df, pd.Series):
                            st.bar_chart(chart_df.to_frame())
                    except Exception:
                        pass

                st.session_state["data_messages"].append(
                    ChatMessage(role="assistant", content=f"🔧 Analyzed with pandas code.\n\n{result_text}")
                )
    else:
        # --- RAG path ---
        retrieved_docs = retriever.invoke(user_input)
        context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])

        history_msgs = [m for m in st.session_state["data_messages"][:-1]
                        if "Analyzed" not in m.content and "loaded" not in m.content and "Upload a CSV" not in m.content]
        history_text = "\n".join(
            f"{'User' if m.role == 'user' else 'AI'}: {m.content}"
            for m in history_msgs[-6:]
        )

        prompt = ChatPromptTemplate.from_template(
            """/no_think
You are an AI data analyst that answers based on the uploaded data.
Answer in English only. Never use Chinese or Japanese characters.

[Prior conversation (use if relevant)]:
{history}

[Data context]:
{context}

Rules:
1. Don't make up anything not in the context — say "I can't find that in the data" instead.
2. Be friendly and professional.
3. When citing numbers or stats, ground them in the actual data.

Question: {question}

Answer:"""
        )

        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response = ""
            buffer = ""
            in_think = None
            with st.spinner("Analyzing..."):
                for chunk in (prompt | llm).stream({
                    "question": user_input,
                    "context": context_text,
                    "history": history_text,
                }):
                    delta = chunk.content
                    if in_think is None:
                        buffer += delta
                        if "<think>" in buffer:
                            in_think = True
                        elif len(buffer) >= 50:
                            in_think = False
                            full_response = buffer
                            response_container.markdown(full_response)
                    elif in_think:
                        buffer += delta
                        if "</think>" in buffer:
                            after = buffer.split("</think>", 1)[1].lstrip("\n")
                            full_response = after
                            in_think = False
                            response_container.markdown(full_response)
                    else:
                        full_response += delta
                        response_container.markdown(full_response)
            st.session_state["data_messages"].append(ChatMessage(role="assistant", content=full_response))

elif user_input and not retriever:
    st.warning("Please upload a file first.")
