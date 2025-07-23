import fitz
import streamlit as st
import google.generativeai as genai
import time
import requests

DEFAULT_LANGUAGE = "한국어"

# API 키 및 모델 설정


genai.configure(api_key="AIzaSyDimeo7tcuyKYq_sAWefpiSXnoi9mOJPPE")
model = genai.GenerativeModel("gemini-1.5-flash")

# 넥슨 API 키 및 캐릭터 기본 정보 가져오기
NEXON_API_KEY = "test_8c70fb58a8535fd3b4b735379682bf774adccedbdb67b3ab610cc10c6347d246efe8d04e6d233bd35cf2fabdeb93fb0d"


def get_character_basic_info(character_name):
    headers = {"x-nxopen-api-key": NEXON_API_KEY}
    ocid_url = "https://open.api.nexon.com/maplestory/v1/id"
    basic_url = "https://open.api.nexon.com/maplestory/v1/character/basic"

    # 1단계: ocid 조회
    ocid_res = requests.get(ocid_url, headers=headers, params={"character_name": character_name})
    if ocid_res.status_code != 200:
        return {"error": "OCID 조회 실패"}
    ocid = ocid_res.json().get("ocid")

    # 2단계: 캐릭터 기본 정보 조회
    basic_res = requests.get(basic_url, headers=headers, params={"ocid": ocid})
    if basic_res.status_code != 200:
        return {"error": "캐릭터 정보 조회 실패"}
    return basic_res.json()

char_name = "박몽뇽"
char_info = get_character_basic_info(char_name)

st.set_page_config(page_title="메지상", page_icon="🤖")

# 언어별 텍스트 정의
LANG_TEXTS = {
    "한국어": {
        "app_title": "메지상",
        "greeting": "안녕하세요! 무엇이든 물어보세요.",
        "chat_input": "무엇이든 물어보세요!",
        "user_label": "사용자",
        "assistant_label": "어시스턴트",
        "language_subtitle": "제 AI 챗봇에 오신 걸 환영해요! 편한 언어를 골라주세요.",
        "elapsed_time_label": "⏳ 응답 시간"
    }
}

def get_text(key):
    # Always return Korean text
    return LANG_TEXTS["한국어"].get(key, "")

# 세션 상태 초기화
if "language" not in st.session_state:
    st.session_state.language = "한국어"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def get_greeting():
    char_name = char_info.get("character_name", "???")
    world_name = char_info.get("world_name", "???")
    return f"안녕하세요! 저는 {world_name} 서버의 {char_name}이에요. 저를 키우고 있는 박지상이 이 AI 챗봇을 직접 만들었답니다. 궁금한 건 무엇이든 물어보세요!"

# PDF 텍스트 추출 함수
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def show_chat():

    user_input = None

    def get_avatar_url(role):
        if role == "user":
            return "https://i.namu.wiki/i/QjHC1Y9DjVcXUmTeNFh9prP4ppC3YbFEA5M6jP4jyJgoGijaOmrxegU1Fkx9x_naCeiS6cLHpj1bcHAB4xhNsA.webp"
        else:
            url = char_info.get("character_image")
            if url and isinstance(url, str) and url.startswith("http"):
                return url
            else:
                return "https://i.pravatar.cc/40?u=assistant"

    st.title(get_text("app_title"))
    # Greeting and static example questions shown below
    with st.chat_message("assistant", avatar=get_avatar_url("assistant")):
        greeting = get_greeting()
        st.write(f"{char_info.get('character_name', '어시스턴트')}: {greeting}")
        st.write("예시 질문을 참고해보세요 👇")
        st.markdown("- 너의 직업은 뭐야?\n- 지상이는 어떤 사람이야?\n- 포트폴리오 요약해줘")

    # Remove buttons and separate markdown for example questions
    if user_input is None:
        user_input = st.chat_input(get_text("chat_input"))

    portfolio_text = extract_text_from_pdf("resume.pdf")

    # 캐릭터 정보 테스트 출력 (초기에는 비활성화)
    # if "error" in char_info:
    #     st.error(f"❌ {char_info['error']}")
    # else:
    #     st.subheader("🧝‍♂️ 캐릭터 정보 (Character Info)")
    #     st.image(char_info["character_image"])
    #     st.markdown(f"**닉네임:** {char_info['character_name']}")
    #     st.markdown(f"**직업:** {char_info['character_class']}")
    #     st.markdown(f"**서버:** {char_info['world_name']}")


    for role, message in st.session_state.chat_history:
        label = char_info.get("character_name", "Assistant") if role != "user" else get_text("user_label")
        avatar_url = get_avatar_url(role)
        with st.chat_message(role, avatar=avatar_url):
            st.markdown(f"**{label}**: {message}")

    if user_input:
        # AI로 다운로드 요청 판단
        classification_prompt = f'''
        다음 문장이 '이력서 또는 레주메 PDF 파일 다운로드 요청'인지 판단해주세요.
        문장: "{user_input}"
        "예" 또는 "아니오"로만 대답해주세요.
        '''
        classification_response = model.generate_content(classification_prompt)
        classification = classification_response.text.strip()

        if classification == "예":
            with st.chat_message("assistant", avatar=get_avatar_url("assistant")):
                st.markdown("📄 박지상 님의 레주메를 다운로드하시려면 아래 버튼을 클릭하세요:")
                st.download_button(
                    label="📄 박지상 레주메 다운로드",
                    data=open("resume.pdf", "rb"),
                    file_name="박지상_레주메.pdf",
                    mime="application/pdf"
                )
            st.session_state.chat_history.append(("assistant", "레주메 다운로드 버튼을 제공했습니다."))
            return

        # 이하 기존 처리 유지
        with st.chat_message("user", avatar=get_avatar_url("user")):
            st.markdown(f"**{get_text('user_label')}**: {user_input}")

        st.session_state.chat_history.append(("user", user_input))
        
        with st.chat_message("assistant", avatar=get_avatar_url("assistant")):
            if any(k in user_input for k in ["캐릭터", "캐릭터 정보", "나에 대해 알려줘", "소개해줘"]):
                answer = (
                    f"닉네임: {char_info['character_name']}\n"
                    f"직업: {char_info['character_class']}\n"
                    f"서버: {char_info['world_name']}"
                )
                elapsed = 0
            else:
                if any(k in user_input for k in ["지상", "포트폴리오", "이력서", "경력", "학력", "전공", "AI", "프로젝트"]):
                    prompt = f"""당신은 박지상 님의 메이플스토리 캐릭터 '박몽뇽'입니다.
박지상 님의 이력은 다음과 같습니다:
{portfolio_text}
유저의 질문에 따라 박지상 님의 정보를 친절하고 친근하게 전달해주세요.

질문: {user_input}
"""
                else:
                    prompt = f"""당신은 메이플스토리의 '엘리시움' 서버에 있는 '박몽뇽'이라는 캐릭터이고, 캐릭터의 직업은 "신궁"입니다.
                    신궁은 석궁을 사용하는 궁수 직업군입니다.
현실 정보는 묻지 않으면 말하지 마세요.
유저의 질문에 따라 캐릭터로서 대답해주세요.
친근하게 존대말로 대답해주세요.

질문: {user_input}
"""
                start_time = time.time()
                response = model.generate_content(prompt)
                answer = response.text
                elapsed = time.time() - start_time

            placeholder = st.empty()
            output = ""
            for char in answer:
                output += char
                placeholder.write(f"{char_info.get('character_name', 'Assistant')}: {output}")
                time.sleep(0.05)

            if elapsed > 0:
                st.markdown(f"*{get_text('elapsed_time_label')}: {elapsed:.2f}초*")
            st.session_state.chat_history.append(("assistant", answer))

show_chat()