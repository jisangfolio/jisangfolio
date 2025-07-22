import fitz
import streamlit as st
import google.generativeai as genai
import time

DEFAULT_LANGUAGE = "English"

# API 키 및 모델 설정

genai.configure(api_key="AIzaSyDimeo7tcuyKYq_sAWefpiSXnoi9mOJPPE")
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="AI 박지상 지상폴리오", page_icon="🤖")

# 언어별 텍스트 정의
LANG_TEXTS = {
    "한국어": {
        "app_title": "📄 박지상 지상폴리오",
        "greeting": "안녕하세요! 무엇이든 물어보세요.",
        "chat_input": "무엇이든 물어보세요!",
        "user_label": "사용자",
        "assistant_label": "어시스턴트",
        "language_subtitle": "제 AI 챗봇에 오신 걸 환영해요! 편한 언어를 골라주세요.",
        "elapsed_time_label": "⏳ 응답 시간"
    },
    "English": {
        "app_title": "📄 Jisang Park Portfolio",
        "greeting": "Hello! Ask me anything.",
        "chat_input": "Ask me anything!",
        "user_label": "You",
        "assistant_label": "Assistant",
        "language_subtitle": "Welcome to my AI chatbot! Please choose your preferred language.",
        "elapsed_time_label": "⏳ Elapsed time"
    }
}

def get_text(key, fallback_lang=None):
    lang = st.session_state.get("language", fallback_lang or DEFAULT_LANGUAGE)
    return LANG_TEXTS.get(lang, LANG_TEXTS[DEFAULT_LANGUAGE]).get(key, "")

# 세션 상태 초기화
if "language_selected" not in st.session_state:
    st.session_state.language_selected = False
if "language" not in st.session_state:
    st.session_state.language = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def show_language_selection():
    st.title("🌐 언어 선택 / Choose Language")
    st.markdown("제 AI 챗봇에 오신 걸 환영해요! 편한 언어를 골라주세요.  \nWelcome to my AI chatbot! Please choose your preferred language.")
    lang = st.selectbox("", ["한국어", "English"])
    if st.button("확인 / Confirm"):
        st.session_state.language_selected = True
        st.session_state.language = lang

def get_greeting():
    return get_text("greeting")


# PDF 텍스트 추출 함수
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def show_chat():
    st.title(get_text("app_title"))
    st.write(get_greeting())

    portfolio_text = extract_text_from_pdf("resume.pdf")

    user_input = st.chat_input(get_text("chat_input"))

    for role, message in st.session_state.chat_history:
        label = get_text("user_label") if role == "user" else get_text("assistant_label")
        with st.chat_message(role):
            st.markdown(f"**{label}**: {message}")

    if user_input:
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user"):
            st.markdown(f"**{get_text('user_label')}**: {user_input}")

        with st.chat_message("assistant"):
            lang_name = "Korean" if st.session_state.language == "한국어" else "English"
            prompt = f"""You are my AI assistant. Here's my resume:
{portfolio_text}

Please answer ONLY in {lang_name} without any translation, transliteration, or additional language.
User question:
{user_input}
"""
            start_time = time.time()
            response = model.generate_content(prompt)
            answer = response.text
            elapsed = time.time() - start_time

            placeholder = st.empty()
            output = ""
            for char in answer:
                output += char
                placeholder.markdown(f"**{get_text('assistant_label')}**: {output}")
                time.sleep(0.05)

            st.markdown(f"*{get_text('elapsed_time_label')}: {elapsed:.2f}초*")
            st.session_state.chat_history.append(("assistant", answer))

if not st.session_state.language_selected:
    show_language_selection()
else:
    show_chat()