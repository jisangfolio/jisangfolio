'''
git add .
git commit -m "message"
git push origin main

streamlit run jisangfolio.py
'''

import fitz
import streamlit as st
import google.generativeai as genai
import time

# 1. API 키 설정
try:
    google_api_key = st.secrets["google_api_key"]
except KeyError:
    st.error("⚠️ Google API 키가 설정되지 않았습니다. secrets.toml을 확인해주세요.")
    st.stop()

genai.configure(api_key=google_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# 2. 페이지 설정
st.set_page_config(page_title="Chat with JJ Park", page_icon="🧑‍💻")

# 3. 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 4. PDF 텍스트 추출
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        return None

# 5. 메인 로직
def show_chat():
    st.title("🧑‍💻 안녕하세요, JJ Park입니다.")
    st.caption("제 이력서와 경험에 대해 궁금한 점을 직접 물어봐 주세요! (AI가 저를 대신해 답변합니다)")

    # 사이드바: 이력서 다운로드
    with st.sidebar:
        st.header("Profile")
        st.info("UIUC Data Science Major\nData Engineer / Scientist 지망")
        
        try:
            with open("resume.pdf", "rb") as f:
                st.download_button(
                    label="📄 제 이력서 다운로드 (PDF)",
                    data=f,
                    file_name="JJ_Park_Resume.pdf",
                    mime="application/pdf"
                )
        except FileNotFoundError:
            st.warning("⚠️ resume.pdf 파일이 없습니다.")

    # 이력서 로드
    if "resume_text" not in st.session_state:
        resume_text = extract_text_from_pdf("resume.pdf")
        if resume_text:
            st.session_state.resume_text = resume_text
        else:
            st.error("이력서 파일을 찾을 수 없습니다.")
            st.stop()

    # 채팅 기록 표시
    for role, message in st.session_state.chat_history:
        # 아바타 설정: user는 면접관 느낌, assistant는 내 사진(또는 이모지)
        avatar = "🧐" if role == "user" else "🧑‍💻"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message)

    # 입력창
    if user_input := st.chat_input("질문 예시: 사용해본 기술 스택이 무엇인가요?"):
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user", avatar="🧐"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🧑‍💻"):
            message_placeholder = st.empty()
            full_response = ""
            
            # 🔥 핵심: 1인칭 시점 프롬프트 엔지니어링
            prompt = f"""
            당신은 현재 구직 중인 데이터 사이언티스트/데이터 엔지니어 **'JJ Park' 본인**입니다.
            아래 제공된 [내 이력서] 내용을 바탕으로 면접관(사용자)의 질문에 대해 **1인칭 시점("저", "제가")**으로 대답하세요.

            [대화 규칙]
            1. **1인칭 사용:** "지원자는"이라고 하지 말고 "저는"이라고 하세요.
            2. **태도:** 자신감 있지만 겸손하고 예의 바르게(해요체) 대답하세요. 
            3. **근거 중심:** 제 경험과 프로젝트 내용을 구체적인 근거로 들어 설명하세요.
            4. **솔직함:** 이력서에 없는 내용을 물어보면 지어내지 말고 "그 부분은 아직 경험해보지 못했지만, 배우고 싶습니다" 혹은 "이력서에는 없지만 면접에서 자세히 말씀드리고 싶습니다"라고 대응하세요.
            5. **상황:** UIUC에서 데이터 사이언스를 전공했다는 배경을 인지하세요.

            [내 이력서 내용]
            {st.session_state.resume_text}

            [면접관 질문]
            {user_input}
            """
            
            try:
                response = model.generate_content(prompt, stream=True)
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                        time.sleep(0.01)
                message_placeholder.markdown(full_response)
                
                st.session_state.chat_history.append(("assistant", full_response))
                
            except Exception as e:
                st.error(f"답변을 생각하는 중 오류가 났어요: {e}")

if __name__ == "__main__":
    show_chat()