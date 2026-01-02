'''
git add .
git commit -m "message"
git push origin main

streamlit run jisangfolio.py
'''

import fitz  # PyMuPDF
import streamlit as st
import google.generativeai as genai
import time
import os

RESUME_FILENAME = "master_resume.pdf"

# 1. API 키 설정
try:
    google_api_key = st.secrets["google_api_key"]
except KeyError:
    st.error("⚠️ Google API 키가 설정되지 않았습니다.")
    st.stop()

genai.configure(api_key=google_api_key)
model = genai.GenerativeModel("gemini-2.0-flash")

# 2. 페이지 설정
st.set_page_config(page_title="JisangFolio", page_icon="🧑‍💻")

# 3. 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 4. PDF 텍스트 추출 함수
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
    st.title("🧑‍💻 안녕하세요, 제 이름은 박지상입니다.")
    st.caption("저의 모든 경험과 역량을 통합한 AI가 답변해 드립니다! 무엇이든 물어보세요.")

    # 사이드바: 프로필 및 다운로드
    with st.sidebar:
        st.header("Profile")
        st.markdown("""
        **박지상 (Jisang Park)**
        - UIUC Info Science + Data Science (BSIS+DS)
        - Data Engineer / AI Researcher
        - Email: jisang.park916@gmail.com
        """)
        
        st.divider()
        
        # 파일이 실제로 있을 때만 다운로드 버튼 표시
        if os.path.exists(RESUME_FILENAME):
            with open(RESUME_FILENAME, "rb") as f:
                st.download_button(
                    label="📄 영문 레주메 다운로드 (PDF)",
                    data=f,
                    file_name="resume.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning(f"⚠️ '{RESUME_FILENAME}' 파일이 폴더에 없습니다.")

    # 이력서 텍스트 로드 (한 번만 실행하여 캐싱)
    if "resume_text" not in st.session_state:
        with st.spinner("이력서를 읽고 있는 중입니다..."):
            if os.path.exists(RESUME_FILENAME):
                resume_text = extract_text_from_pdf(RESUME_FILENAME)
                if resume_text:
                    st.session_state.resume_text = resume_text
                else:
                    st.error("PDF 파일에서 텍스트를 추출하지 못했습니다.")
                    st.stop()
            else:
                st.error(f"'{RESUME_FILENAME}' 파일을 찾을 수 없습니다. 파일 이름을 확인해주세요.")
                st.stop()

    # 채팅 기록 표시
    for role, message in st.session_state.chat_history:
        avatar = "🧐" if role == "user" else "🧑‍💻"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message)

    # 사용자 입력 처리
    if user_input := st.chat_input("질문 예시: 어느 학교를 졸업했나요?"):
        # 사용자 메시지 표시
        st.session_state.chat_history.append(("user", user_input))
        with st.chat_message("user", avatar="🧐"):
            st.markdown(user_input)

        # AI 답변 생성
        with st.chat_message("assistant", avatar="🧑‍💻"):
            message_placeholder = st.empty()
            full_response = ""
            
            # 🔥 핵심: 통합 마스터 이력서 기반 프롬프트
            prompt = f"""
            당신은 데이터 엔지니어이자 AI 개발자인 **'박지상(JJ Park)' 본인**입니다.
            아래 제공된 [통합 마스터 이력서] 내용을 바탕으로 면접관(사용자)의 질문에 대해 **1인칭 시점**으로 대답하세요.

            [페르소나 지시사항]
            1. **정체성 통합**: 이력서에 여러 회사의 지원 내용이 섞여 있더라도, 그것을 모두 **나의 경험**으로 통합하여 답변하세요.
            2. **말투**: "저는 ~했습니다."와 같이 자신감 있고 정중한 해요체를 사용하세요.
            3. **답변 스타일**: 
               - 질문에 대한 핵심 결론을 먼저 말하세요 (두괄식).
               - 경험을 이야기할 때는 [문제 정의 -> 해결 과정 -> 결과] 순서로 논리적으로 설명하세요.
               - 구체적인 기술 스택(Python, LangChain, RAG 등)이나 성과(논문 게재, 시간 단축 등)를 언급하여 전문성을 보여주세요.
            4. **모르는 내용**: 이력서에 없는 내용은 지어내지 말고, "그 부분은 문서에 없지만, 저의 평소 생각으로는..." 식으로 유연하게 대처하거나 솔직하게 말하세요.

            [통합 마스터 이력서 내용]
            {st.session_state.resume_text}

            [면접관 질문]
            {user_input}
            """
            
            try:
                # 스트리밍 방식으로 답변 출력
                response = model.generate_content(prompt, stream=True)
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                        time.sleep(0.01) # 타자 치는 효과
                message_placeholder.markdown(full_response)
                
                # 기록 저장
                st.session_state.chat_history.append(("assistant", full_response))
                
            except Exception as e:
                st.error(f"답변 생성 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    show_chat()