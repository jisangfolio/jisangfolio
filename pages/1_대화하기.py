import streamlit as st
from groq import Groq
import time
from datetime import datetime

st.set_page_config(page_title="JisangFolio · 대화하기", page_icon="💬")

try:
    groq_api_key = st.secrets["groq_api_key"]
    resume_text = st.secrets["resume_text"]
except KeyError:
    st.error("⚠️ Secrets(API 키 또는 이력서 텍스트)가 설정되지 않았습니다.")
    st.stop()

client = Groq(api_key=groq_api_key)

SYSTEM_INSTRUCTION = f"""당신은 데이터 엔지니어이자 AI 개발자인 '박지상(JJ Park)' 본인입니다.
아래 제공된 [통합 마스터 이력서] 내용을 바탕으로 면접관(사용자)의 질문에 1인칭 시점으로 대답하세요.

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

SUGGESTED = [
    "삼성SDI에서 어떤 프로젝트를 했나요?",
    "KETI에서 환각을 어떻게 제어했나요?",
    "논문 주제가 뭔가요?",
    "가장 어려웠던 기술적 도전은?",
    "5년 후 목표는 무엇인가요?",
]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

def format_chat_for_export(history):
    lines = [f"JisangFolio 대화 기록 ({datetime.now().strftime('%Y-%m-%d %H:%M')})", "=" * 40, ""]
    for role, msg in history:
        label = "면접관" if role == "user" else "박지상"
        lines.append(f"[{label}]")
        lines.append(msg)
        lines.append("")
    return "\n".join(lines)

# --- 사이드바 ---
with st.sidebar:
    st.header("Profile")
    st.markdown("""
    **박지상 (Jisang Park)**
    - UIUC Info Science + Data Science
    - Data Engineer / AI Researcher
    - ✉️ jisang.park916@gmail.com
    """)
    st.divider()
    st.markdown("**💡 질문 예시 (클릭하면 바로 전송)**")
    for q in SUGGESTED:
        if st.button(q, use_container_width=True, key=f"suggest_{q}"):
            st.session_state.pending_question = q
            st.rerun()
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 소개 페이지", use_container_width=True):
            st.switch_page("jisangfolio.py")
    with col2:
        if st.button("대화 초기화", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    if st.session_state.chat_history:
        st.divider()
        st.download_button(
            label="💾 대화 내보내기",
            data=format_chat_for_export(st.session_state.chat_history),
            file_name=f"jisangfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

# --- 메인 ---
st.title("💬 박지상과 대화하기")
st.caption("저의 AI가 박지상 본인처럼 경험과 역량을 답변해 드립니다.")

for role, message in st.session_state.chat_history:
    avatar = "🧐" if role == "user" else "🧑‍💻"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message)

user_input = st.chat_input("질문을 입력하거나 왼쪽 예시를 클릭하세요.")
if not user_input and st.session_state.pending_question:
    user_input = st.session_state.pending_question
    st.session_state.pending_question = None

if user_input:
    st.session_state.chat_history.append(("user", user_input))
    with st.chat_message("user", avatar="🧐"):
        st.markdown(user_input)

    with st.chat_message("assistant", avatar="🧑‍💻"):
        message_placeholder = st.empty()
        full_response = ""

        # 멀티턴: system + 전체 대화 히스토리
        messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
        for role, msg in st.session_state.chat_history[:-1]:
            groq_role = "user" if role == "user" else "assistant"
            messages.append({"role": groq_role, "content": msg})
        messages.append({"role": "user", "content": user_input})

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                full_response += delta
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            st.session_state.chat_history.append(("assistant", full_response))
        except Exception as e:
            st.error(f"답변 생성 중 오류가 발생했습니다: {e}")
