import time
import os
import streamlit as st
import pandas as pd
from langchain_core.messages import ChatMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_groq import ChatGroq
from prompts import ROUTER_PROMPT_TEMPLATE, strip_think
from guardrails import check_input, blocked_message
from ui import apply_style, finalize_stream, friendly_llm_error
from observability import log_trace
from codeguard import run_generated_code
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
SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "tebo_sample.xlsx")
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

import re


def _tok(s):
    return re.findall(r"[a-z0-9가-힣]+", (s or "").lower())


def _rrf(ranklists, k=5, c=60):
    """Reciprocal Rank Fusion — fuse multiple ranked doc lists into one."""
    scores, docmap = {}, {}
    for docs in ranklists:
        for rank, d in enumerate(docs):
            key = d.page_content
            scores[key] = scores.get(key, 0.0) + 1.0 / (c + rank + 1)
            docmap[key] = d
    top = sorted(scores, key=scores.get, reverse=True)[:k]
    return [docmap[key] for key in top]


class HybridRetriever:
    """Hybrid retrieval: dense (FAISS) + sparse (BM25), fused with RRF.
    Same .invoke(query) interface as a LangChain retriever."""

    def __init__(self, vectorstore, splits, bm25, k=5):
        self.vs, self.splits, self.bm25, self.k = vectorstore, splits, bm25, k

    def invoke(self, query, k=None):
        k = k or self.k
        dense = self.vs.similarity_search(query, k=k * 3)
        scores = self.bm25.get_scores(_tok(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k * 3]
        sparse = [self.splits[i] for i in order]
        return _rrf([dense, sparse], k=k)


# --- File processing ---
# max_entries/ttl 이 없으면 업로드된 파일마다 FAISS 인덱스가 컨테이너 수명 내내 상주한다
# (방문자가 각자 파일을 올릴수록 단조 증가 → 무료 티어 메모리에서 결국 죽는다).
# 캐시 미스는 재임베딩 비용일 뿐 정확성 문제가 아니므로 짧게 잡는다.
@st.cache_resource(show_spinner="Analyzing the uploaded file...", max_entries=3, ttl=1800)
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

    from rank_bm25 import BM25Okapi
    bm25 = BM25Okapi([_tok(d.page_content) for d in splits])
    k = max(1, min(10, vectorstore.index.ntotal // 5))
    # Hybrid: dense (FAISS) + sparse (BM25) fused with RRF
    return df, HybridRetriever(vectorstore, splits, bm25, k=k)


def get_df_info(df: pd.DataFrame) -> str:
    """Build a DataFrame summary to pass to the LLM."""
    info_parts = [f"Columns: {list(df.columns)}"]
    info_parts.append(f"Rows: {len(df)}")
    info_parts.append(f"Dtypes:\n{df.dtypes.to_string()}")
    info_parts.append(f"First 3 rows:\n{df.head(3).to_string()}")
    return "\n".join(info_parts)


def classify_question(llm, question: str, df_info: str) -> str:
    """The LLM decides whether to handle the question with pandas (codegen) or RAG search.

    Routing runs on a dedicated LLM handle with reasoning disabled: the router only has
    to emit one word, and with reasoning on the chain-of-thought was being parsed as if
    it were the answer — any stray mention of "PANDAS" inside the thinking flipped the
    route. Stripping <think> as well makes the parse defensive either way. The eval
    harness (evals/run_evals.py classify) uses the same prompt AND the same setting, so
    the measured routing accuracy represents what the app actually does.
    """
    prompt = ChatPromptTemplate.from_template(ROUTER_PROMPT_TEMPLATE)
    result = (prompt | llm).invoke({"question": question, "df_info": df_info})
    answer = strip_think(result.content).strip().upper()
    if "PANDAS" in answer:
        return "PANDAS"
    return "RAG"


# 축소 권한 실행 네임스페이스는 codeguard.py 로 분리했다 —
# Streamlit 페이지는 import 시 set_page_config()가 돌아 테스트가 못 불러오므로,
# 리포에서 가장 위험한 코드가 CI 밖에 있었다. 이제 tests/test_codeguard.py가 검증한다.


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

    # 정적 검사 + 축소 네임스페이스 실행 (codeguard.py)
    result, chart_df, error = run_generated_code(code, df)
    return code, result, chart_df, error


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
# 라우팅 전용 핸들 — 한 단어만 내면 되므로 추론을 끈다(사고 텍스트가 파싱을 오염시키던
# 문제 제거 + 지연 감소). 평가 하니스 classify()와 동일 설정이라 측정값이 앱을 대변한다.
router_llm = ChatGroq(model=GROQ_MODEL, groq_api_key=groq_api_key, temperature=0,
                      reasoning_effort="none", max_tokens=200)
user_input = st.chat_input("Ask anything about this data")
if not user_input and st.session_state["data_pending"]:
    user_input = st.session_state["data_pending"]
    st.session_state["data_pending"] = None

if user_input and retriever:
    st.chat_message("user").write(user_input)
    st.session_state["data_messages"].append(ChatMessage(role="user", content=user_input))

    # 🛡 Guardrail — this page feeds free text straight into a codegen prompt,
    # so the input guard has to run here too, not just on the chat pages.
    verdict = check_input(user_input)
    if not verdict["allowed"]:
        guard_msg = blocked_message(verdict, "English")
        with st.chat_message("assistant"):
            st.markdown(guard_msg)
            st.caption(f"🛡 Guardrail blocked · {verdict['category']}")
        st.session_state["data_messages"].append(ChatMessage(role="assistant", content=guard_msg))
        log_trace(page="data", model=GROQ_MODEL, route="blocked",
                  latency_ms=0, guard=verdict["category"], ok=False)
        st.stop()

    df_info = get_df_info(df)
    _t0 = time.time()

    # 이 페이지의 모델 호출은 전부 bare 였다. 무료 티어에서 429가 나면 빨간
    # 트레이스백이 그대로 화면에 떴다(다른 페이지들은 처리하고 있었다).
    # 라우팅·코드생성·스트리밍이 모두 Groq 를 부르므로 턴 전체를 감싼다.
    try:
        route = classify_question(router_llm, user_input, df_info)
    except Exception as e:                                  # noqa: BLE001
        msg = friendly_llm_error(e)
        with st.chat_message("assistant"):
            st.warning(msg)
        st.session_state["data_messages"].append(ChatMessage(role="assistant", content=msg))
        log_trace(page="data", route="error", model=GROQ_MODEL,
                  latency_ms=int((time.time() - _t0) * 1000), guard="ok",
                  nodes=["llm_error"], ok=False)
        st.stop()

    if route == "PANDAS":
        # --- pandas codegen path ---
        with st.chat_message("assistant"):
            with st.spinner("Generating code..."):
                try:
                    code, result, chart_df, error = generate_and_run_code(llm, user_input, df_info, df)
                except Exception as e:                      # noqa: BLE001
                    msg = friendly_llm_error(e)
                    st.warning(msg)
                    st.session_state["data_messages"].append(ChatMessage(role="assistant", content=msg))
                    log_trace(page="data", route="pandas", model=GROQ_MODEL,
                              latency_ms=int((time.time() - _t0) * 1000), guard="ok",
                              nodes=["llm_error"], ok=False)
                    st.stop()

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
                try:
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
                except Exception as e:                      # noqa: BLE001
                    full_response = friendly_llm_error(e)
                else:
                    # 50자 미만 응답이 buffer 에만 남아 사라지던 버그(1_Chat.py 와 동일)
                    full_response = finalize_stream(full_response, buffer, in_think)
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
                try:
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
                except Exception as e:                      # noqa: BLE001
                    full_response = friendly_llm_error(e)
                else:
                    # 50자 미만 응답이 buffer 에만 남아 사라지던 버그(1_Chat.py 와 동일)
                    full_response = finalize_stream(full_response, buffer, in_think)
            response_container.markdown(full_response)
            st.session_state["data_messages"].append(ChatMessage(role="assistant", content=full_response))

    # 📈 Observability — 데이터 분석 턴도 트레이스로 기록
    # guard는 실제 판정값을 넘긴다(기본값 "ok"에 기대면 가드를 안 돈 페이지도 통과처럼 보임).
    log_trace(page="data", route=route, model=GROQ_MODEL,
              latency_ms=int((time.time() - _t0) * 1000),
              guard=verdict["category"])

elif user_input and not retriever:
    st.warning("Please upload a file first.")
