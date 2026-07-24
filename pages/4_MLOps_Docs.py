"""MLOps Docs Assistant — 공식 MLOps 파이프라인 문서에 대한 RAG 챗봇.

코퍼스 = Google/AWS/Azure/Vertex 공식 파이프라인 문서 + 온프레 KETI 파이프라인(정제본).
Phase 1: 하이브리드 검색(FAISS+BM25) → 근거 인용 생성. (Phase 2에서 agentic 루프 추가)

'내 온프레 MLOps 파이프라인 vs 클라우드 3사'를 비교·질의할 수 있는, 방대한 기술문서를
빠르게 검색·학습하려고 만든 도구. KAigen(내부 규정 문서 RAG)과 같은 패턴.
"""
import time
import streamlit as st
from langchain_core.messages import ChatMessage
from langchain_groq import ChatGroq

from guardrails import check_input, blocked_message
from observability import log_trace, timer
from rag_corpus import build_retriever, source_lines
from agent_rag import agentic_answer
from ui import apply_style

st.set_page_config(page_title="JisangFolio · MLOps Docs", page_icon="📚")
apply_style()

try:
    groq_api_key = st.secrets["groq_api_key"]
except KeyError:
    st.error("⚠️ groq_api_key is not set in Secrets.")
    st.stop()

GROQ_MODEL = "qwen/qwen3.6-27b"

SAMPLE_QUESTIONS = [
    "What is MLOps maturity level 1?",
    "What pipeline step types does SageMaker Pipelines support?",
    "온프레 KETI 파이프라인은 Triton으로 모델을 어떻게 서빙했나?",
    "How does Vertex AI Pipelines track artifact lineage?",
]


# 코퍼스 검색기는 컨테이너 수명 동안 한 번만 구축(임베딩)하고 공유
@st.cache_resource(show_spinner="Indexing MLOps docs (embedding)...")
def get_retriever():
    return build_retriever(k=5)


# --- Sidebar ---
with st.sidebar:
    if st.button("← Home"):
        st.switch_page("jisangfolio.py")
    if st.button("💬 Chat"):
        st.switch_page("pages/1_Chat.py")
    st.divider()
    st.header("📚 MLOps Docs Assistant")
    st.caption(
        "Official MLOps pipeline docs (Google · AWS · Azure · Vertex) + an on-prem "
        "KETI pipeline reference, indexed for retrieval-augmented Q&A with citations."
    )
    st.divider()
    st.markdown("**💡 Sample questions**")
    for q in SAMPLE_QUESTIONS:
        if st.button(q, use_container_width=True, key=f"rag_{q}"):
            st.session_state["rag_pending"] = q
            st.rerun()

st.title("📚 MLOps Docs Assistant")
st.caption("Ask about MLOps pipelines across clouds and the on-prem KETI stack. Answers are grounded in the indexed docs, with source citations.")

if "rag_messages" not in st.session_state:
    st.session_state["rag_messages"] = [
        ChatMessage(role="assistant", content=(
            "Ask me anything about MLOps pipelines — Google's maturity model, "
            "SageMaker / Vertex / Azure ML pipelines, or the on-prem KETI stack. "
            "I answer only from the indexed docs and cite my sources."
        ))
    ]
if "rag_pending" not in st.session_state:
    st.session_state["rag_pending"] = None

retriever = get_retriever()

for msg in st.session_state["rag_messages"]:
    st.chat_message(msg.role).write(msg.content)

# reasoning_effort="none": qwen3의 사고(<think>)를 끈다.
# 문서 RAG는 검색된 근거로 바로 답하면 되므로 사고가 불필요하고, 켜두면 토큰을
# 사고에 다 써(2048 cap) 답이 잘리는 문제가 있었다 → 끄니 빠르고·안 잘리고·인용 정확.
llm = ChatGroq(model=GROQ_MODEL, groq_api_key=groq_api_key, temperature=0,
               reasoning_effort="none", max_tokens=1500)

user_input = st.chat_input("Ask about MLOps pipelines...")
if not user_input and st.session_state["rag_pending"]:
    user_input = st.session_state["rag_pending"]
    st.session_state["rag_pending"] = None

if user_input:
    # 1) 입력 가드레일 (인젝션·과길이 차단)
    verdict = check_input(user_input)
    st.chat_message("user").write(user_input)
    st.session_state["rag_messages"].append(ChatMessage(role="user", content=user_input))

    if not verdict["allowed"]:
        msg = blocked_message(verdict, lang="English")
        st.chat_message("assistant").write(msg)
        st.session_state["rag_messages"].append(ChatMessage(role="assistant", content=msg))
        log_trace(page="rag_docs", route="blocked", model=GROQ_MODEL,
                  latency_ms=0, guard=verdict["category"], ok=False)
    else:
        with st.chat_message("assistant"):
            # Agentic RAG: 검색 → 관련성 평가 → (부실하면) 재작성+재검색 → 생성 → 근거점검
            with timer() as t:
                with st.spinner("🔁 Agent: retrieve → grade → (rewrite) → answer → self-check..."):
                    result = agentic_answer(llm, retriever, user_input, max_retries=1)
            answer = result["answer"]
            chunks = result["chunks"]

            st.markdown(answer)

            # 근거 자기점검 배지 (faithfulness)
            if result["grounded"] == "YES":
                st.caption("✅ Self-check: answer grounded in retrieved sources")
            else:
                st.caption("⚠️ Self-check: answer may contain unsupported claims")

            # 🔁 에이전트 단계 — 자기교정 루프를 눈에 보이게 (L3 에이전트의 증거)
            _icon = {"retrieve": "🔎", "grade": "⚖️", "rewrite": "✏️",
                     "generate": "💬", "self_check": "✅"}
            title = "🔁 Agent steps" + (" · rewrote the query & retried" if result["rewrote"] else "")
            with st.expander(title):
                for s in result["trace"]:
                    st.markdown(f"{_icon.get(s['step'], '•')} **{s['step']}** — {s['detail']}")

            # 📎 출처 (검색된 청크 = 인용 번호와 대응)
            with st.expander(f"📎 Sources ({len(chunks)} retrieved)"):
                for s in source_lines(chunks):
                    loc = s["section"] or s["source_file"]
                    line = f"**[{s['n']}]** {s['vendor']} · {loc}"
                    if s["url"] and s["url"].startswith("http"):
                        line += f"  \n{s['url']}"
                    st.markdown(line)

        st.session_state["rag_messages"].append(ChatMessage(role="assistant", content=answer))
        log_trace(page="rag_docs", route="agentic_rag", model=GROQ_MODEL,
                  latency_ms=t.ms, guard="ok",
                  nodes=[s["step"] for s in result["trace"]],
                  ok=(result["grounded"] == "YES"))
