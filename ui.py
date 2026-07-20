"""공유 스타일 주입 (Pretendard 폰트 + 카드/버튼 라운딩).

config.toml 이 색/테마를 담당하고, 이 모듈은 폰트와 미세 라운딩만 얹는다.
멀티페이지라 각 페이지 set_page_config 직후 apply_style() 을 호출한다.
"""
import streamlit as st

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
