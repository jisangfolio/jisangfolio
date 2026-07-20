import streamlit as st
from groq import Groq
from datetime import datetime
from prompts import build_system_prompt, clean_response

st.set_page_config(page_title="JisangFolio · 대화하기", page_icon="💬")

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
    lang = st.radio("Language / 언어", ["한국어", "English"], horizontal=True, key="chat_lang")
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
    caption_text = "이 챗봇은 제(박지상) 이력서로 답하는 AI라 가끔 헷갈릴 수 있어요. 정확한 건 이력서 PDF나 메일로 물어봐 주세요 :)" if lang == "한국어" else "This chatbot answers from my (Jisang's) resume, so it can occasionally get things wrong. For anything important, check the resume PDF or just email me :)"
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
page_caption = "이력서를 통째로 물고 있는 챗봇이에요. 면접에서 물어볼 법한 걸 편하게 던져보세요." if lang == "한국어" else "This chatbot has my whole resume loaded. Ask it the kind of thing you'd ask in an interview."
st.title(title)
st.caption(page_caption)

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
    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user", avatar="🧐"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🧑‍💻"):
        message_placeholder = st.empty()
        message_placeholder.markdown("💭")
        full_response = ""

        messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
        for role, msg in st.session_state.chat_history[:-1]:
            groq_role = "user" if role == "user" else "assistant"
            messages.append({"role": groq_role, "content": msg})
        messages.append({"role": "user", "content": user_input})

        try:
            stream = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=messages,
                stream=True,
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
            full_response = clean_response(full_response)
            message_placeholder.markdown(full_response)
            st.session_state.chat_history.append(("assistant", full_response))
        except Exception as e:
            err = "답변 생성 중 오류가 발생했습니다" if lang == "한국어" else "Error generating response"
            st.error(f"{err}: {e}")
