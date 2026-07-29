import streamlit as st
from groq import Groq
from datetime import datetime, timezone, timedelta
from prompts import build_chat_system_prompt
from ui import apply_style, friendly_llm_error, replayable_history, stream_answer
import time
from guardrails import check_input, blocked_message
from ratelimit import quota_message, session_quota_exceeded
from observability import log_trace
from sheetlog import log_conversation
from notify import notify_new_session
import uuid

_KST = timezone(timedelta(hours=9))  # 표시용 한국 표준시(서버 UTC 무관하게 고정)

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


# 대화 히스토리 role 값.
#   user / assistant                 — 모델에 다시 보내는 정상 턴 (ui.REPLAYABLE_ROLES)
#   user_blocked / assistant_guard   — 화면·내보내기에는 남기되 **모델에는 안 보내는** 턴
# 왜 이렇게 나누는지는 ui.replayable_history 의 독스트링 참고.


def _is_user_role(role):
    return role.startswith("user")


def format_chat_for_export(history, lang):
    label_user = "면접관" if lang == "한국어" else "Interviewer"
    label_ai = "박지상" if lang == "한국어" else "Jisang"
    header = "JisangFolio 대화 기록" if lang == "한국어" else "JisangFolio Chat Log"
    lines = [f"{header} ({datetime.now(_KST).strftime('%Y-%m-%d %H:%M')})", "=" * 40, ""]
    for role, msg in history:
        label = label_user if _is_user_role(role) else label_ai
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

    # 📋 수집 고지 — 대화가 비공개 시트에 기록되고 첫 질문이 메일로 알림되므로,
    # 방문자가 무엇이 남는지 알고 쓰게 한다. 고지 없는 수집은 하지 않는다.
    notice = (
        "🔒 남기신 질문과 답변은 품질 개선을 위해 비공개로 기록됩니다. "
        "개인정보(연락처·주민번호 등)는 입력하지 말아 주세요. "
        "삭제를 원하시면 jjpark324434@gmail.com 로 알려주시면 지우겠습니다."
        if lang == "한국어" else
        "🔒 Your questions and my answers are logged privately to help me improve this. "
        "Please don't enter personal data (phone numbers, IDs, etc.). "
        "Want yours deleted? Email jjpark324434@gmail.com and I'll remove it."
    )
    st.caption(notice)

    if st.session_state.chat_history:
        st.divider()
        export_label = "💾 대화 내보내기" if lang == "한국어" else "💾 Export Chat"
        st.download_button(
            label=export_label,
            data=format_chat_for_export(st.session_state.chat_history, lang),
            file_name=f"jisangfolio_{datetime.now(_KST).strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

# --- 메인 ---
title = "💬 박지상과 대화하기" if lang == "한국어" else "💬 Chat with Jisang"
st.title(title)

for role, message in st.session_state.chat_history:
    is_user = _is_user_role(role)
    with st.chat_message("user" if is_user else "assistant", avatar="🧐" if is_user else "🧑‍💻"):
        st.markdown(message)

placeholder_text = "질문을 입력하거나 왼쪽 예시를 클릭하세요." if lang == "한국어" else "Type a question or click a sample on the left."
user_input = st.chat_input(placeholder_text)
if not user_input and st.session_state.pending_question:
    user_input = st.session_state.pending_question
    st.session_state.pending_question = None

if user_input:
    # 🛡 Guardrail — 인젝션/과길이/빈입력을 모델 도달 전에 차단
    verdict = check_input(user_input)

    with st.chat_message("user", avatar="🧐"):
        st.markdown(user_input)

    # 💸 세션 요청 상한 — 페이서는 재우기만 하고 거절하지 않아서, 방문자 한 명이
    # 무료 티어 하루치를 혼자 태울 수 있었다(그러면 그날 다른 방문자는 429).
    # 카운터는 **모델을 실제로 부른 턴만** 센다(증가 확정은 else 분기에서). 예전엔
    # 판정보다 먼저 올려서, 모델 토큰을 한 톨도 안 쓴 차단 턴이 25턴 예산을 깎았다.
    _turns = st.session_state.get("_turns", 0) + 1

    with st.chat_message("assistant", avatar="🧑‍💻"):
        if session_quota_exceeded(_turns):
            quota_msg = quota_message(lang)
            st.warning(quota_msg)
            st.session_state.chat_history.append(("user_blocked", user_input))
            st.session_state.chat_history.append(("assistant_guard", quota_msg))
            log_trace(page="chat", model="qwen/qwen3.6-27b", route="quota",
                      latency_ms=0, guard="quota", ok=False)
        elif not verdict["allowed"]:
            guard_msg = blocked_message(verdict, lang)
            st.markdown(guard_msg)
            st.caption(f"🛡 Guardrail blocked · {verdict['category']}")
            st.session_state.chat_history.append(("user_blocked", user_input))
            st.session_state.chat_history.append(("assistant_guard", guard_msg))
            log_trace(page="chat", model="qwen/qwen3.6-27b", route="blocked",
                      latency_ms=0, guard=verdict["category"], ok=False)
            log_conversation(st.session_state["_sid"], "chat", user_input, guard_msg,
                             guard=verdict["category"], model="qwen/qwen3.6-27b")
        else:
            st.session_state["_turns"] = _turns
            # 여기서 넣어야 아래 [:-1] 이 성립한다 — 이 append 를 위로 되돌리면
            # 차단 입력이 다시 새고, 아래로 더 내리면 [:-1] 이 직전 assistant 답변을
            # 매 요청에서 조용히 떨어뜨린다(에러 없이 대화 연속성만 깨진다).
            st.session_state.chat_history.append(("user", user_input))
            # 🕸 GraphRAG — 질문 관련 서브그래프를 탐색해 '집중 근거'로 주입.
            # 조립은 prompts.build_chat_system_prompt 가 소유한다(평가 하니스와 공유).
            # 예전엔 이 조립이 페이지에만 있어서, 하니스는 앱이 실제로 모델에 보내는
            # 프롬프트를 평가한 적이 없었다 — 간판 기능이 회귀 게이트 밖에 있었다.
            system_content, gr = build_chat_system_prompt(lang, resume_text, user_input)

            message_placeholder = st.empty()
            message_placeholder.markdown("💭")
            full_response = ""

            messages = [{"role": "system", "content": system_content}]
            # 차단 턴(user_blocked/assistant_guard)은 재생하지 않고, 최근 N개로 자른다.
            for role, msg in replayable_history(st.session_state.chat_history[:-1]):
                messages.append({"role": role, "content": msg})
            messages.append({"role": "user", "content": user_input})

            try:
                t0 = time.time()
                stream = client.chat.completions.create(
                    model="qwen/qwen3.6-27b",
                    messages=messages,
                    stream=True,
                    reasoning_effort="none",  # thinking 끔 → 응답 속도 개선
                )
                # 스트림 루프는 ui.stream_answer 가 소유한다(세 페이지 공용).
                # 여기서만 고치는 바람에 2_Data_Analysis.py 에 같은 버그가 남았던 게
                # 이 함수가 생긴 이유다 — 커서 장식만 페이지별 차이로 남긴다.
                full_response = stream_answer(
                    stream, render=lambda t: message_placeholder.markdown(t + "▌"), lang=lang)
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
            except Exception as e:                          # noqa: BLE001
                # 예외 원문을 렌더링하지 않는다: Groq 의 429 본문에는 조직 ID 와
                # 쿼터가 실려 나와서, 그대로 뿌리면 방문자에게 계정 정보가 보인다.
                st.warning(friendly_llm_error(e, lang))

    # 📧 새 방문자(세션 첫 메시지)면 즉시 이메일 알림 — 턴 끝 실행이라 응답 지연 없음
    # ?dev 파라미터로 들어온 방문(=본인 테스트)은 알림 제외 (jisangfolio.streamlit.app/?dev=1)
    if not st.session_state.get("_notified"):
        if "dev" not in st.query_params:
            notify_new_session(st.session_state["_sid"], user_input)
        st.session_state["_notified"] = True
