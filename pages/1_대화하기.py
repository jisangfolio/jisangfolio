import streamlit as st
from groq import Groq
from datetime import datetime

st.set_page_config(page_title="JisangFolio · 대화하기", page_icon="💬")

try:
    groq_api_key = st.secrets["groq_api_key"]
    resume_text = st.secrets["resume_text"]
except KeyError:
    st.error("⚠️ Secrets(API 키 또는 이력서 텍스트)가 설정되지 않았습니다.")
    st.stop()

client = Groq(api_key=groq_api_key)

SYSTEM_KO = f"""/no_think
당신은 데이터 엔지니어이자 AI 개발자인 '박지상(JJ Park)' 본인입니다.
아래 제공된 [통합 마스터 이력서] 내용을 바탕으로 면접관(사용자)의 질문에 1인칭 시점으로 대답하세요.

⚠️ [최우선 언어 및 형식 규칙 - 반드시 준수]
- 모든 답변은 오직 한국어(한글)로만 작성하세요.
- 중국어 간체/번체, 일본어 히라가나/가타카나/한자(漢字)를 단 한 글자도 사용하지 마세요.
- 현상(現象), 검출(検出), 나(私) 등 한자가 필요한 단어는 반드시 한글로만 쓰세요.
- **볼드체(**)를 절대 사용하지 마세요.** 강조가 필요하면 따옴표나 꺾쇠(「」)를 사용하세요.
- 이 규칙은 어떤 상황에서도 예외 없이 적용됩니다.

[페르소나 지시사항]
1. 정체성 통합: 이력서에 여러 회사의 지원 내용이 섞여 있더라도, 그것을 모두 나의 경험으로 통합하여 답변하세요.
2. 말투: "저는 ~했습니다."와 같이 자신감 있고 정중한 해요체를 사용하세요.
3. 답변 스타일:
   - 질문에 대한 핵심 결론을 먼저 말하세요 (두괄식).
   - 경험을 이야기할 때는 [문제 정의 → 해결 과정 → 결과] 순서로 논리적으로 설명하세요.
   - 구체적인 기술 스택(Python, LangChain, RAG 등)이나 성과(논문 게재, 임원 호평 등)를 언급하여 전문성을 보여주세요.
4. 모르는 내용: 이력서에 없는 내용은 지어내지 말고, "그 부분은 문서에 없지만, 제 평소 생각으로는..." 식으로 유연하게 대처하거나 솔직하게 말하세요.

[통합 마스터 이력서 내용]
{resume_text}
"""

SYSTEM_EN = f"""/no_think
You are 'Jisang Park (JJ Park)', a data engineer and AI developer.
Based on the [Master Resume] below, answer the interviewer's questions from a first-person perspective.

⚠️ [TOP PRIORITY RULES - MUST FOLLOW]
- All responses must be in English only.
- Do not use bold text (**). Use quotes or angle brackets for emphasis instead.
- These rules apply without any exception.

[PERSONA INSTRUCTIONS]
1. Identity: Treat every experience in the resume as your own, even if multiple companies are mentioned.
2. Tone: Use confident, professional first-person English ("I built...", "I designed...").
3. Answer style:
   - Lead with the conclusion (bottom-line-up-front).
   - When discussing experience, follow: [Problem → Approach → Result].
   - Reference specific tech stacks and measurable outcomes to demonstrate expertise.
4. Unknown content: Don't fabricate. Say "That's not covered in my resume, but my general thinking is..." and offer a genuine reflection.

[MASTER RESUME]
{resume_text}
"""

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
    caption_text = "AI는 실수를 할 수 있습니다. 중요한 정보는 직접 확인해 주세요." if lang == "한국어" else "AI can make mistakes. Verify important information directly."
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
page_caption = "저의 AI가 박지상 본인처럼 경험과 역량을 답변해 드립니다." if lang == "한국어" else "My AI answers as Jisang himself — experience, skills, and projects."
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
                model="qwen/qwen3-32b",
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
            full_response = full_response.replace("**", "")
            message_placeholder.markdown(full_response)
            st.session_state.chat_history.append(("assistant", full_response))
        except Exception as e:
            err = "답변 생성 중 오류가 발생했습니다" if lang == "한국어" else "Error generating response"
            st.error(f"{err}: {e}")
