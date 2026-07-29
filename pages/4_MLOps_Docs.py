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
from agent_rag import ANSWER_MAX_TOKENS, APP_TURN_BUDGET_S, agentic_answer
from ui import apply_style, friendly_llm_error

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
    st.chat_message("user" if msg.role.startswith("user") else "assistant").write(msg.content)

# reasoning_effort="none": qwen3의 사고(<think>)를 끈다.
# 문서 RAG는 검색된 근거로 바로 답하면 되므로 사고가 불필요하고, 켜두면 토큰을
# 사고에 다 써(2048 cap) 답이 잘리는 문제가 있었다 → 끄니 빠르고·안 잘리고·인용 정확.
llm = ChatGroq(model=GROQ_MODEL, groq_api_key=groq_api_key, temperature=0,
               reasoning_effort="none", max_tokens=ANSWER_MAX_TOKENS)

user_input = st.chat_input("Ask about MLOps pipelines...")
if not user_input and st.session_state["rag_pending"]:
    user_input = st.session_state["rag_pending"]
    st.session_state["rag_pending"] = None

if user_input:
    # 1) 입력 가드레일 (인젝션·과길이 차단)
    verdict = check_input(user_input)
    st.chat_message("user").write(user_input)

    if not verdict["allowed"]:
        msg = blocked_message(verdict, lang="English")
        st.chat_message("assistant").write(msg)
        # 이 페이지는 히스토리를 모델에 재전송하지 않아 지금은 새지 않는다. 그래도
        # 세 페이지가 같은 규칙을 쓰게 둔다 — 나중에 여기에 히스토리를 붙이는 사람이
        # 다른 두 페이지의 교훈을 다시 배우지 않아도 되도록. (ui.REPLAYABLE_ROLES)
        st.session_state["rag_messages"].append(ChatMessage(role="user_blocked", content=user_input))
        st.session_state["rag_messages"].append(ChatMessage(role="assistant_guard", content=msg))
        log_trace(page="rag_docs", route="blocked", model=GROQ_MODEL,
                  latency_ms=0, guard=verdict["category"], ok=False)
    else:
        st.session_state["rag_messages"].append(ChatMessage(role="user", content=user_input))
        with st.chat_message("assistant"):
            # Agentic RAG: 검색 → 관련성 평가 → (부실하면) 재작성+재검색 → 생성 → 근거점검
            # 이 루프는 한 턴에 LLM을 3~4회 부른다(판정 1 + 생성 1 + 자기점검 1, 재작성 시 +1).
            # 즉 단방향 RAG보다 호출·토큰을 몇 배 쓰므로, 무료 티어의 분당·일일 한도에
            # 단방향 경로보다 훨씬 빨리 닿는다. 실패를 사용자에게 그대로 노출하지 않는다.
            #
            # turn_budget_s 를 넘기는 이유: 재시도 백오프는 호출당 최대 90초까지 자고
            # 한 턴에 3~4콜이 있어, 상한이 없으면 방문자가 몇 분간 멈춘 화면을 본다.
            # 무인 실행(평가 하니스)은 이 인자를 안 넘겨 끈기 있는 백오프를 유지한다.
            result = None
            with timer() as t:
                with st.spinner("🔁 Agent: retrieve → grade → (rewrite) → answer → self-check..."):
                    try:
                        result = agentic_answer(llm, retriever, user_input, max_retries=1,
                                                turn_budget_s=APP_TURN_BUDGET_S)
                    except Exception as e:                     # noqa: BLE001
                        result = None
                        err = e

            if result is None:
                # 이 페이지만 자체 오류 문구를 갖고 있었고, 그것도 UI 가 영어인데 한국어였다.
                # 영어권 방문자가 429 를 만나면 한국어 안내를 봤다 → 공용 헬퍼로 통일.
                msg = friendly_llm_error(err)
                st.warning(msg)
                st.caption("Retrieval succeeded — the failure was in the model call.")
                st.session_state["rag_messages"].append(ChatMessage(role="assistant", content=msg))
                log_trace(page="rag_docs", route="agentic_rag", model=GROQ_MODEL,
                          latency_ms=t.ms, guard="ok", nodes=["llm_error"], ok=False)
                st.stop()

            answer = result["answer"]
            chunks = result["chunks"]

            st.markdown(answer)

            # 근거 자기점검 배지 (faithfulness)
            if result["grounded"] == "YES":
                st.caption("✅ Self-check: answer grounded in retrieved sources")
            else:
                st.caption("⚠️ Self-check: answer may contain unsupported claims")

            # 🔁 단계 트레이스 — 자기교정 루프(판단·재시도)를 눈에 보이게
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
