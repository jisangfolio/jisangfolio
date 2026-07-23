import streamlit as st
from groq import Groq
from datetime import datetime
from prompts import build_system_prompt, clean_response
from ui import apply_style
import time
from guardrails import check_input, blocked_message
from observability import log_trace
from profile_graph import graph_retrieve
from sheetlog import log_conversation
import uuid

st.set_page_config(page_title="JisangFolio · Chat", page_icon="💬")
apply_style()

try:
    groq_api_key = st.secrets["groq_api_key"]
    resume_text = st.secrets["resume_text"]
except KeyError:
    st.error("⚠️ Secrets(API 키 또는 이력서 텍스트)가 설정되지 않았습니다.")
    st.stop()

client = Groq(api_key=groq_api_key)

# 시스템 프롬프트는 prompts.py(SSOT)에서 조립 — 평가 하니스(evals/)와 동일 소스 공유
SYSTEM_KO = build_system_prompt("한국어", resume_text)
SYSTEM_EN = build_system_prompt("English", resume_text)

SUGGESTED_KO = [
    "삼성SDI에서 어떤 프로젝트를 했나요?",
    "KETI에서 어떤 연구를 하고 있나요?",
    "논문 주제가 뭔가요?",
    "가장 어려웠던 기술적 도전은?",
    "5년 후 목표는 무엇인가요?",
]
SUGGESTED_EN = [
    "What did you work on at Samsung SDI?",
    "What research are you doing at KETI?",
    "Tell me about your published paper.",
    "What was your toughest technical challenge?",
    "Where do you see yourself in 5 years?",
]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "_sid" not in st.session_state:
    st.session_state["_sid"] = uuid.uuid4().hex[:8]  # 익명 방문 세션 식별자


def format_chat_for_export(history, lang):
    label_user = "면접관" if lang == "한국어" else "Interviewer"
    label_ai = "박지상" if lang == "한국어" else "Jisang"
    header = "JisangFolio 대화 기록" if lang == "한국어" else "JisangFolio Chat Log"
    lines = [f"{header} ({datetime.now().strftime('%Y-%m-%d %H:%M')})", "=" * 40, ""]
    for role, msg in history:
        label = label_user if role == "user" else label_ai
        lines.append(f"[{label}]")
        lines.append(msg)
        lines.append("")
    return "\n".join(lines)


# --- 사이드바 ---
with st.sidebar:
    lang = st.radio("Language / 언어", ["English", "한국어"], horizontal=True, key="chat_lang")
    st.divider()
    st.markdown("""
    **박지상 (Jisang Park)**
    - UIUC Info Science + Data Science
    - Data Engineer / AI Researcher
    - ✉️ jjpark324434@gmail.com
    """)
    st.divider()

    SUGGESTED = SUGGESTED_KO if lang == "한국어" else SUGGESTED_EN
    hint = "**💡 질문 예시 (클릭하면 바로 전송)**" if lang == "한국어" else "**💡 Sample Questions (click to send)**"
    st.markdown(hint)
    for q in SUGGESTED:
        if st.button(q, use_container_width=True, key=f"suggest_{q}"):
            st.session_state.pending_question = q
            st.rerun()

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        btn_home = "← 소개 페이지" if lang == "한국어" else "← Home"
        if st.button(btn_home, use_container_width=True):
            st.switch_page("jisangfolio.py")
    with col2:
        btn_reset = "대화 초기화" if lang == "한국어" else "Clear Chat"
        if st.button(btn_reset, use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()

    st.divider()
    caption_text = "이 챗봇은 제(박지상) 이력서로 답하는 AI라 가끔 헷갈릴 수 있습니다. 정확한 건 이력서 PDF나 메일로 확인 바랍니다 :)" if lang == "한국어" else "This chatbot answers from my (Jisang's) resume, so it can occasionally get things wrong. For anything important, check the resume PDF or just email me :)"
    st.caption(caption_text)

    if st.session_state.chat_history:
        st.divider()
        export_label = "💾 대화 내보내기" if lang == "한국어" else "💾 Export Chat"
        st.download_button(
            label=export_label,
            data=format_chat_for_export(st.session_state.chat_history, lang),
            file_name=f"jisangfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

# --- 메인 ---
title = "💬 박지상과 대화하기" if lang == "한국어" else "💬 Chat with Jisang"
st.title(title)

for role, message in st.session_state.chat_history:
    avatar = "🧐" if role == "user" else "🧑‍💻"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message)

placeholder_text = "질문을 입력하거나 왼쪽 예시를 클릭하세요." if lang == "한국어" else "Type a question or click a sample on the left."
user_input = st.chat_input(placeholder_text)
if not user_input and st.session_state.pending_question:
    user_input = st.session_state.pending_question
    st.session_state.pending_question = None

SYSTEM_INSTRUCTION = SYSTEM_KO if lang == "한국어" else SYSTEM_EN

if user_input:
    # 🛡 Guardrail — 인젝션/과길이/빈입력을 모델 도달 전에 차단
    verdict = check_input(user_input)

    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user", avatar="🧐"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🧑‍💻"):
        if not verdict["allowed"]:
            guard_msg = blocked_message(verdict, lang)
            st.markdown(guard_msg)
            st.caption(f"🛡 Guardrail blocked · {verdict['category']}")
            st.session_state.chat_history.append(("assistant", guard_msg))
            log_trace(page="chat", model="qwen/qwen3.6-27b", route="blocked",
                      latency_ms=0, guard=verdict["category"], ok=False)
            log_conversation(st.session_state["_sid"], "chat", user_input, guard_msg,
                             guard=verdict["category"], model="qwen/qwen3.6-27b")
        else:
            # 🕸 GraphRAG — 질문 관련 서브그래프를 탐색해 '집중 근거'로 주입
            gr = graph_retrieve(user_input, lang=lang)
            system_content = SYSTEM_INSTRUCTION
            if gr["context"]:
                _lab = "이 질문에 관련된 프로필 서브그래프" if lang == "한국어" else "Profile subgraph relevant to this question"
                system_content = system_content + f"\n\n[GraphRAG — {_lab}]\n" + gr["context"] + "\n"

            message_placeholder = st.empty()
            message_placeholder.markdown("💭")
            full_response = ""

            messages = [{"role": "system", "content": system_content}]
            for role, msg in st.session_state.chat_history[:-1]:
                groq_role = "user" if role == "user" else "assistant"
                messages.append({"role": groq_role, "content": msg})
            messages.append({"role": "user", "content": user_input})

            try:
                t0 = time.time()
                stream = client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=messages,
                    stream=True,
                    reasoning_effort="none",  # thinking 끔 → 응답 속도 개선
                )
                full_response = ""
                buffer = ""
                in_think = None  # None=미결정, True=thinking 블록 내, False=일반 응답
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if in_think is None:
                        buffer += delta
                        if "<think>" in buffer:
                            in_think = True
                        elif len(buffer) >= 50:
                            in_think = False
                            full_response = buffer
                            message_placeholder.markdown(full_response + "▌")
                    elif in_think:
                        buffer += delta
                        if "</think>" in buffer:
                            after = buffer.split("</think>", 1)[1].lstrip("\n")
                            full_response = after
                            in_think = False
                            message_placeholder.markdown(full_response + "▌")
                    else:
                        full_response += delta
                        message_placeholder.markdown(full_response + "▌")
                # 스트림 종료 후 확정: 50자 미만 짧은 응답이 버퍼에만 남아 빈 화면이 되던 버그 수정
                if in_think is None:
                    full_response = buffer
                full_response = clean_response(full_response)
                if not full_response.strip():
                    full_response = clean_response(buffer)
                if not full_response.strip():
                    full_response = "(응답이 비어 있어요. 다시 한 번 물어봐 주세요.)" if lang == "한국어" else "(Empty response — please try again.)"
                message_placeholder.markdown(full_response)
                st.session_state.chat_history.append(("assistant", full_response))
                # 📈 Observability — 이 턴을 트레이스로 기록
                log_trace(page="chat", model="qwen/qwen3.6-27b", route="chat",
                          latency_ms=int((time.time() - t0) * 1000),
                          guard="ok", nodes=gr["seeds"], ok=True)
                log_conversation(st.session_state["_sid"], "chat", user_input, full_response,
                                 latency_ms=int((time.time() - t0) * 1000), guard="ok",
                                 model="qwen/qwen3.6-27b")
                if gr["seeds"]:
                    st.caption(f"🕸 GraphRAG · traversed {len(gr['nodes'])} nodes: " + " · ".join(gr["nodes"][:8]))
            except Exception as e:
                err = "답변 생성 중 오류가 발생했습니다" if lang == "한국어" else "Error generating response"
                st.error(f"{err}: {e}")
