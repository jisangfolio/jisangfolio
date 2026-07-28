"""공유 스타일 주입 (Pretendard 폰트 + 카드/버튼 라운딩) + 페이지 공통 응답 처리.

config.toml 이 색/테마를 담당하고, 이 모듈은 폰트와 미세 라운딩만 얹는다.
멀티페이지라 각 페이지 set_page_config 직후 apply_style() 을 호출한다.

스트림 마감(finalize_stream)과 LLM 오류 문구(friendly_llm_error)도 여기 둔다.
둘 다 원래 페이지마다 인라인으로 복사돼 있었고, 그래서 1_Chat.py 에서 고친
버그가 2_Data_Analysis.py 에는 안 넘어간 채로 남아 있었다.
"""
import streamlit as st

from prompts import clean_response

_STYLE = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

html, body, [class*="css"], .stMarkdown, button, input, textarea, .stTextInput, .stChatInput {
  font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif !important;
}

/* 버튼: 살짝 둥글게 + 미세 hover */
.stButton > button {
  border-radius: 10px;
  transition: transform .06s ease, border-color .15s ease;
}
.stButton > button:hover { transform: translateY(-1px); }

/* 카드(bordered container): 부드러운 라운딩 */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }

/* 링크: 밑줄은 hover에서만 */
a, a:visited { text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
"""


def apply_style():
    """폰트·라운딩 CSS를 주입한다. set_page_config 이후에 호출."""
    st.markdown(_STYLE, unsafe_allow_html=True)


def finalize_stream(full_response, buffer, in_think, lang="English"):
    """스트리밍 종료 후 최종 응답을 확정한다.

    스트림 루프는 <think> 블록 판정을 위해 앞 50자를 buffer 에 모아두고, 50자를
    넘어야 buffer 를 full_response 로 승격한다. 그래서 **50자 미만 응답은 buffer 에만
    남은 채 끝난다** — 프롬프트가 지시하는 거절 문구 "I can't find that in the data."
    (30자)가 정확히 여기 걸려서 빈 말풍선으로 렌더링되고 히스토리에 content=""
    으로 영구 저장됐다. 짧은 답변일수록 중요한 답변인 경우가 많다.
    """
    if in_think is None:          # 50자에 도달하지 못하고 스트림이 끝난 경우
        full_response = buffer
    out = clean_response(full_response)
    if not out.strip():           # 후처리가 전부 깎아낸 경우 원본으로 되돌린다
        out = clean_response(buffer)
    if not out.strip():
        out = ("(응답이 비어 있어요. 다시 한 번 물어봐 주세요.)" if lang == "한국어"
               else "(Empty response — please try again.)")
    return out


def friendly_llm_error(err, lang="English"):
    """모델 호출 실패를 사용자용 문구로 바꾼다. 원문 예외는 절대 렌더링하지 않는다.

    Groq 의 429 본문에는 조직 ID 와 쿼터가 실려 나온다. 그대로 화면에 뿌리면
    방문자에게 계정 정보를 보여주는 셈이라 예외 '종류'만 노출한다.
    """
    name = type(err).__name__
    ko = (lang == "한국어")
    if "RateLimit" in name or "429" in str(err):
        return ("⚠️ 지금은 모델 사용 한도에 걸려 답할 수 없습니다. 이 데모는 무료 티어를 "
                "쓰기 때문에 한도에 닿을 수 있어요. 잠시 후 다시 시도해 주세요." if ko else
                "⚠️ The model is rate-limited right now — this demo runs on a free tier. "
                "Please try again in a moment.")
    return (f"⚠️ 답변 생성 중 오류가 발생했습니다 ({name}). 잠시 후 다시 시도해 주세요." if ko
            else f"⚠️ Something went wrong while generating the answer ({name}). Please try again.")
